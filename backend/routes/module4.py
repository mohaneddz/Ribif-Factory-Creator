import json
from flask import Blueprint, jsonify, request
from pathlib import Path
import time
import uuid
from datetime import datetime, timezone

from config import OUTPUT_DIRS, SKIP_MODULE_4, BASE_URL
from supabase_utils import get_supabase, insert_module4_sourcing
from utils.module_4.core import build_machines_enriched
from utils.logger import log_skip, get_logger
from utils.app_helpers import (
    get_request_project_id,
    get_request_user_id,
    get_project_machines,
    insert_machine_supplier,
    load_template_payload,
    upsert_supplier,
    upload_and_register_file,
    upload_with_name_timestamp,
    sanitize_for_json,
)

logger = get_logger("module4")

def extract_normalized_input(data: dict) -> dict:
    """Normalize input to standard structure."""
    if not isinstance(data, dict):
        return {}
    
    # Try direct structure
    machines = data.get("stage_4_machines_equipements", {}).get("machines_production", [])
    if machines:
        return data

    # Try nested 'data' (common from frontend wrappers)
    if "data" in data and isinstance(data["data"], dict):
        sub = data["data"]
        machines_sub = sub.get("stage_4_machines_equipements", {}).get("machines_production", [])
        if machines_sub:
            return sub
            
    return data

bp_module4 = Blueprint("module4", __name__)


@bp_module4.route("/api/module4/enrich", methods=["POST"])
def enrich_machines_module4():
    try:
        if SKIP_MODULE_4:
            log_skip("module4.enrich_machines_module4", reason="SKIP_MODULE_4")
            payload = load_template_payload("module4") or {}
            project_id = get_request_project_id(include_json=True)
            if isinstance(payload, dict) and project_id:
                payload["project_id"] = payload.get("project_id") or project_id
                meta = payload.get("ribif_metadata")
                if isinstance(meta, dict):
                    meta["project_id"] = meta.get("project_id") or project_id
            return jsonify(payload)

        start_time = time.time()
        project_id = get_request_project_id(include_json=True)
        
        if not request.is_json:
            return jsonify({"error": "Expected JSON input (module_1 output)"}), 400

        raw_input = request.get_json()
        input_data = extract_normalized_input(raw_input)
        
        module1_id = input_data.get("module1_id") or input_data.get("ribif_metadata", {}).get("module1_id")
        machines = input_data.get("stage_4_machines_equipements", {}).get("machines_production", [])

        if not machines:
            return jsonify({"error": "No machines found in input."}), 400

        input_path = OUTPUT_DIRS["module4"] / "module_4_input.json"
        input_path.parent.mkdir(parents=True, exist_ok=True)
        input_path.write_text(json.dumps(input_data, ensure_ascii=False, indent=2), encoding="utf-8")

        output_path = OUTPUT_DIRS["module4"] / "module_4.json"
        
        # Budget is consistent at 60s
        result = build_machines_enriched(
            input_path=str(input_path),
            output_path=str(output_path),
            max_workers=4,
            per_machine_timeout_s=75,
            domain_gap_s=1.5,
            llm_call_timeout_s=30,
            total_machine_budget_s=60,
            generated_images_dir=str(OUTPUT_DIRS["module4"] / "module_4_images"),
        )

        if project_id:
            result["project_id"] = project_id
        if module1_id:
            result.setdefault("ribif_metadata", {})
            result["ribif_metadata"]["module1_id"] = module1_id

        client = get_supabase()
        owner_id = get_request_user_id()
        
        # Post-process: Handle generated images and DB sync
        warnings = []
        if client and project_id:
            try:
                # 1. Upload generated images & update URLs
                machines_enriched = result.get("machines_enriched", []) or []
                for entry in machines_enriched:
                    try:
                        m_input = entry.get("machine_input", {})
                        assets = m_input.get("assets", {})
                        gen = assets.get("generated_image")
                        
                        if gen and isinstance(gen, dict) and gen.get("local_path"):
                            local_p = gen.get("local_path")
                            fname = gen.get("filename")
                            
                            # Upload to storage
                            fid, url, ob_path = upload_with_name_timestamp(
                                client=client,
                                project_id=project_id,
                                owner_id=owner_id,
                                local_path=local_p,
                                category="module4-generated",
                                label=fname,
                            )
                            
                            # Update JSON with public URL
                            gen["public_url"] = url
                            gen["file_id"] = fid
                            
                            # Fallback best_image_url if N/A
                            if m_input.get("best_image_url") in [None, "N/A", ""]:
                                m_input["best_image_url"] = url
                                
                    except Exception as img_err:
                        warnings.append(f"Image upload fail for item: {img_err}")
                        logger.error("Image upload post-process failed: %s", img_err)

                # 2. Insert Module 4 Record
                # Stats
                processing_time = int(time.time() - start_time)
                run_id = str(uuid.uuid4())
                enrichment_date = datetime.now(timezone.utc).isoformat()
                
                proj_meta = {
                    "last_run_id": run_id,
                    "last_enrichment_date": enrichment_date,
                    "model_used": "vertex-gemini-pro",
                    "last_processing_time_seconds": processing_time
                }

                module4_id = insert_module4_sourcing(client, project_id, module1_id, result, project_metadata=proj_meta)
                result.setdefault("ribif_metadata", {})
                result["ribif_metadata"]["module4_id"] = module4_id
                
                # 3. Upload Output JSON
                if output_path.exists():
                    output_file_id, output_file_url = upload_and_register_file(
                        client=client,
                        project_id=project_id,
                        owner_id=owner_id,
                        local_path=str(output_path),
                        category="module4-output",
                        label=output_path.name,
                    )
                    result["ribif_metadata"]["module4_output_file_id"] = output_file_id
                    result["ribif_metadata"]["module4_output_file_url"] = output_file_url

                # 4. Sync Suppliers & Machines
                machines_map = get_project_machines(client, project_id)
                for entry in machines_enriched:
                    try:
                        machine_input = entry.get("machine_input", {})
                        machine_name = machine_input.get("nom_machine") or machine_input.get("name")
                        machine_id = machines_map.get(machine_name)
                        
                        if not machine_id:
                            continue
                            
                        # Insert suppliers
                        for supplier in entry.get("suppliers", []) or []:
                            supplier_id = upsert_supplier(
                                client,
                                supplier.get("supplier_name") or supplier.get("name") or "Unknown",
                                supplier.get("website"),
                                supplier.get("region"),
                                metadata={"source": "module4"},
                            )
                            if supplier_id:
                                insert_machine_supplier(
                                    client,
                                    machine_id,
                                    supplier_id,
                                    supplier,
                                    metadata={"source": "module4"},
                                )
                                
                    except Exception as inner_e:
                        warnings.append(f"DB sync fail for {machine_name}: {inner_e}")
                        logger.error("DB sync failed: %s", inner_e)
                        
            except Exception as e:
                msg = f"Critical DB operation failed: {e}"
                warnings.append(msg)
                logger.error(msg)
        
        if warnings:
            result.setdefault("ribif_metadata", {})
            existing = result["ribif_metadata"].get("warnings", [])
            if isinstance(existing, list):
                result["ribif_metadata"]["warnings"] = existing + warnings
            else:
                result["ribif_metadata"]["warning_note"] = (existing if isinstance(existing, str) else "") + " | " + "; ".join(warnings)
 
        return jsonify(sanitize_for_json(result))
    except Exception as e:
        logger.error("Module 4 global failure: %s", e)
        return jsonify({"error": str(e), "status": "error"}), 500
