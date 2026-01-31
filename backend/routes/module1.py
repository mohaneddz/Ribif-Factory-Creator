import base64
import os
import shutil
from pathlib import Path

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from config import BASE_URL, OUTPUT_DIRS, UPLOAD_DIR, CREATE_MACHINE_IMAGES, SKIP_MODULE_1, write_json
from supabase_utils import get_supabase, insert_module1_extraction
from utils.module_1.core import RIBIFExtractor
from utils.module_1.enricher import enricher
from utils.logger import log_skip, get_logger
from utils.app_helpers import (
    get_pipeline_settings,
    get_request_project_id,
    get_request_user_id,
    ensure_project_id,
    insert_machines_from_stage,
    insert_machine_assets,
    load_template_payload,
    store_project_settings,
    upload_and_register_file,
    upload_with_name_timestamp,
)
from utils.image_selector import find_best_image, get_random_image
from vertex_utils import generate_image

import time
import uuid
from datetime import datetime

bp_module1 = Blueprint("module1", __name__)
extractor = RIBIFExtractor()


def generate_machine_image(machine_name: str, machine_type: str, manufacturer: str = None) -> dict:
    try:
        manufacturer_text = f" by {manufacturer}" if manufacturer else ""
        prompt = f"""Professional product photography of an industrial {machine_type} machine called \"{machine_name}\"{manufacturer_text}.

The image should be:
- Clean white/gray studio background
- Professional industrial equipment photography style
- High-quality, sharp details
- Showing the full machine from a 3/4 angle
- Realistic, photographic quality
- No text overlays or labels
- Industrial manufacturing equipment aesthetic"""

        image_bytes_list = generate_image(prompt, candidate_count=1)
        if image_bytes_list and len(image_bytes_list) > 0:
            image_filename = f"{machine_name.replace(' ', '_').replace('/', '_')[:50]}.png"
            image_path = OUTPUT_DIRS["module1"] / image_filename
            with open(image_path, "wb") as f:
                f.write(image_bytes_list[0])
            base64_image = base64.b64encode(image_bytes_list[0]).decode("utf-8")
            data_uri = f"data:image/png;base64,{base64_image}"
            return {
                "image_url": data_uri,
                "image_path": str(image_path),
                "status": "success",
            }
        return {"image_url": None, "status": "no_image"}
    except Exception as e:
        return {"image_url": None, "status": "error", "error": str(e)}


@bp_module1.route("/api/module1/process", methods=["POST"])
def process_module_1():
    if SKIP_MODULE_1:
        log_skip("module1.process", reason="SKIP_MODULE_1")
        payload = load_template_payload("module1") or {}
        project_id = get_request_project_id(include_form=True, include_json=True)
        if isinstance(payload, dict) and project_id:
            payload["project_id"] = payload.get("project_id") or project_id
            meta = payload.get("ribif_metadata")
            if isinstance(meta, dict):
                meta["project_id"] = meta.get("project_id") or project_id
        response_payload = {"message": "Success", "data": payload, "status": "skipped"}
        return jsonify(response_payload)

    start_time = time.time()
    project_id = get_request_project_id(include_form=True, include_json=True)
    download_error = None
    filepath = None
    filename = "source.pdf"

    if "file" in request.files:
        file = request.files["file"]
        if file.filename != "":
            filename = secure_filename(file.filename)
            filepath = UPLOAD_DIR / filename
            file.save(filepath)

    if not filepath:
        object_path = None
        # Try to get path from payload
        if request.is_json:
            data = request.get_json() or {}
            object_path = data.get("source_file_path")
            if data.get("source_filename"):
                filename = secure_filename(data.get("source_filename"))

        client = get_supabase()
        # If not in payload, try from DB
        if not object_path and project_id and client:
            try:
                res = client.table("projects").select("source_file_path").eq("id", project_id).single().execute()
                if res.data and res.data.get("source_file_path"):
                    object_path = res.data.get("source_file_path")
            except Exception as e:
                module1_logger = get_logger("module1")
                module1_logger.warning(f"Failed to fetch source_file_path from DB: {e}")

        # Download if we found a path
        # Download if we found a path
        download_error = None
        if object_path and client:
            try:
                file_data = client.storage.from_("project-files").download(object_path)
                try:
                    if filename == "source.pdf" or not filename:
                        raw_name = Path(object_path).name
                        # Handle cases where path includes folders
                        if "/" in raw_name:
                            raw_name = raw_name.split("/")[-1]
                        filename = secure_filename(raw_name)
                except Exception as e:
                    module1_logger = get_logger("module1")
                    module1_logger.warning(f"Failed to resolve filename from object path: {e}")
                    filename = "source.pdf"
                
                filepath = UPLOAD_DIR / filename
                with open(filepath, "wb") as f:
                    f.write(file_data)
            except Exception as e:
                download_error = f"Error downloading file from {object_path}: {str(e)}"
                module1_logger = get_logger("module1")
                module1_logger.warning(download_error)
    
    if not filepath:
         error_details = "No file uploaded and could not retrieve from project"
         if download_error:
             error_details += f". Download failure: {download_error}"
         elif object_path:
             error_details += f". object_path found ({object_path}) but download failed silently or client missing."
         else:
             error_details += ". No file in request and no source_file_path found in payload/DB."
             
         return jsonify({"error": error_details}), 400

    settings = get_pipeline_settings()
    # project_id = get_request_project_id(include_form=True) # Already fetched
    owner_id = get_request_user_id()
    client = get_supabase()
    project_id = ensure_project_id(client, project_id, owner_id, Path(filename).stem or "Project")
    if client and project_id and settings:
        try:
            store_project_settings(client, project_id, settings, owner_id)
        except Exception as e:
            module1_logger = get_logger("module1")
            module1_logger.warning(f"Failed to store project settings: {e}")

    source_file_id = None
    source_file_url = None
    source_object_path = None
    if client and project_id and "file" in request.files:
        try:
            source_file_id, source_file_url, source_object_path = upload_with_name_timestamp(
                client=client,
                project_id=project_id,
                owner_id=owner_id,
                local_path=str(filepath),
                category="uploads",
                label="module1_source",
            )
        except Exception as e:
            module1_logger = get_logger("module1")
            module1_logger.warning(f"Failed to upload source file copy: {e}")

    extraction_result = extractor.process_document(str(filepath), str(OUTPUT_DIRS["module1"]))

    # --- COMPREHENSIVE ENRICHMENT (Module 1 Stages 1-6) ---
    module1_logger = get_logger("module1")
    module1_logger.info("Starting enrichment pipeline...")
    try:
        enriched_result = enricher.process(extraction_result)
        final_result = enriched_result

        # --- FIX: Reconcile Stage 5 (Production Process) for UI ---
        stage5 = final_result.get("stage_5_processus_production", {})
        procs = stage5.get("processus_production", [])
        
        if procs and isinstance(procs, list):
            # If the enricher returned a list of products with nested steps, flatten it for the UI
            if "etapes" in procs[0]:
                module1_logger.info("Flattening nested Stage 5 routings for UI compatibility...")
                all_steps = []
                for p in procs:
                    prod_name = p.get("produit", "Production")
                    for i, s in enumerate(p.get("etapes", [])):
                        # Map keys to UI expectations
                        s["nom_etape"] = s.get("name", s.get("nom_etape", "Etape sans nom"))
                        if prod_name != "Production":
                            s["nom_etape"] = f"[{prod_name}] {s['nom_etape']}"
                        
                        s["numero_etape"] = s.get("step", s.get("numero_etape", i + 1))
                        
                        # Ensure parametres_process exists for Temp/Pression/Cycle labels
                        if "parametres_process" not in s:
                            s["parametres_process"] = {
                                "temperature": s.get("temperature", s.get("temp", "N/A")),
                                "pression": s.get("pression", "N/A"),
                                "temps_cycle": s.get("cycle", s.get("duration", "N/A")),
                                "vitesse": s.get("vitesse", s.get("speed", "N/A"))
                            }
                        all_steps.append(s)
                final_result["stage_5_processus_production"]["processus_production"] = all_steps
            else:
                # Flat list already, but ensure keys are correct
                for i, s in enumerate(procs):
                    if "nom_etape" not in s and "name" in s:
                        s["nom_etape"] = s["name"]
                    if "numero_etape" not in s:
                        s["numero_etape"] = s.get("step", i + 1)
                    if "parametres_process" not in s:
                         s["parametres_process"] = {
                            "temperature": s.get("temperature", "N/A"),
                            "pression": s.get("pression", "N/A"),
                            "temps_cycle": s.get("cycle", "N/A")
                        }

    except Exception as e:
        module1_logger.error(f"Enrichment pipeline failed: {e}")
        final_result = extraction_result.copy()

    # --- IMAGE GENERATION & FINAL ASSETS ---
    # We still want to ensure every machine has an image, generating them if web search didn't find one.
    machines = final_result.get("stage_4_machines_equipements", {}).get("machines_production", []) or []
    enriched_machines = []
    
    for machine_data in machines:
        nom_machine = machine_data.get("nom_machine", "Unknown")
        machine_type = machine_data.get("type", "industrial machine")
        manufacturer = machine_data.get("fabricant_recommande", "")
        
        # Check if we already have an image from web enrichment
        web_enrichment = machine_data.get("_web_enrichment", {})
        web_images = web_enrichment.get("images", [])
        
        image_result = {"image_url": None, "status": "skipped"}
        image_local_path = None
        image_download_url = None
        web_image_found = False

        # Try to download the best web image if present
        if web_images and settings.get("useWebImages", True):
            try:
                import requests
                img_url = web_images[0]
                resp = requests.get(img_url, timeout=5)
                if resp.status_code == 200:
                    safe_name = secure_filename(f"{nom_machine[:50]}_web") or "machine_web"
                    image_filename = f"{safe_name}.jpg"
                    image_path = OUTPUT_DIRS["module1"] / image_filename
                    image_path.write_bytes(resp.content)
                    
                    web_image_found = True
                    image_local_path = str(image_path)
                    b64 = base64.b64encode(resp.content).decode("utf-8")
                    image_result = {
                        "image_url": f"data:image/jpeg;base64,{b64}",
                        "image_path": str(image_path),
                        "status": "web_found",
                        "source_url": img_url
                    }
            except Exception as e:
                module1_logger.warning(f"Failed to download agent-found web image for {nom_machine}: {e}")

        # Fallback to generation if no image found/downloaded
        if not web_image_found:
             if CREATE_MACHINE_IMAGES and settings.get("enableMachineImages", True):
                image_result = generate_machine_image(nom_machine, machine_type, manufacturer)
                image_local_path = image_result.get("image_path")
             else:
                cached = find_best_image(nom_machine) or get_random_image()
                if cached:
                    target_path = OUTPUT_DIRS["module1"] / cached.name
                    if not target_path.exists():
                        shutil.copyfile(cached, target_path)
                    image_local_path = str(target_path)

        if image_local_path:
            image_download_url = f"{BASE_URL}/download/{Path(image_local_path).name}"

        # Update machine data
        machine_data["image_url"] = image_result.get("image_url")
        machine_data["image_status"] = image_result.get("status")
        machine_data["image_local_path"] = image_local_path
        machine_data["image_download_url"] = image_download_url
        enriched_machines.append(machine_data)

    final_result["stage_4_machines_equipements"]["machines_production"] = enriched_machines
    final_result["enriched_machines"] = enriched_machines
    successful_scrapes = sum(1 for m in enriched_machines if m.get("image_status") in ("success", "web_found", "cache_found"))
    final_result["scraping_summary"] = {
        "total_machines": len(machines),
        "successful_scrapes": successful_scrapes,
        "failed_scrapes": len(machines) - successful_scrapes,
    }
    final_result.setdefault("ribif_metadata", {})
    final_result["ribif_metadata"].update({
        "project_id": project_id,
        "source_file_path": str(filepath),
        "source_file_id": source_file_id,
        "source_file_object_path": source_object_path,
        "source_file_url": source_file_url,
        "pipeline_settings": settings,
    })
    final_result["project_id"] = project_id

    output_file = OUTPUT_DIRS["module1"] / f"{Path(filename).stem}_complete_pipeline.json"
    write_json(output_file, final_result)

    final_result["module1_output_path"] = str(output_file)
    final_result["module1_download_url"] = f"{BASE_URL}/download/{output_file.name}"

    module1_id = None
    if client and project_id:
        try:
            # Metadata stats
            processing_time = int(time.time() - start_time)
            run_id = str(uuid.uuid4())
            extraction_date = datetime.utcnow().isoformat()
            
            proj_meta = {
                "last_run_id": run_id,
                "last_extraction_date": extraction_date,
                "model_used": "vertex-gemini-pro-vision", # Assumed default from config/extractor
                "last_processing_time_seconds": processing_time
            }
            
            # module1_id is now just project_id
            module1_id = insert_module1_extraction(client, project_id, source_file_id, final_result, project_metadata=proj_meta)
            
            output_file_id, output_file_url = upload_and_register_file(
                client=client,
                project_id=project_id,
                owner_id=owner_id,
                local_path=str(output_file),
                category="module1-output",
                label=output_file.name,
            )
            final_result["module1_output_file_id"] = output_file_id
            final_result["module1_output_file_url"] = output_file_url

            image_meta = {}
            for m in enriched_machines:
                image_path = m.get("image_local_path")
                name = m.get("nom_machine")
                if image_path and name and Path(image_path).exists():
                    try:
                        img_file_id, img_url, img_object_path = upload_with_name_timestamp(
                            client=client,
                            project_id=project_id,
                            owner_id=owner_id,
                            local_path=image_path,
                            category="machine-images",
                            label=name,
                        )
                        image_meta[name] = {
                            "image_file_id": img_file_id,
                            "image_url": img_url,
                            "image_object_path": img_object_path,
                        }
                    except Exception:
                        continue

            machine_ids = insert_machines_from_stage(client, project_id, machines, image_meta)
            for name, meta in image_meta.items():
                machine_id = machine_ids.get(name)
                file_id = meta.get("image_file_id")
                if machine_id and file_id:
                    insert_machine_assets(client, machine_id, file_id, asset_type="image", label=name)

        except Exception as e:
            module1_logger = get_logger("module1")
            module1_logger.warning(f"Failed to upload module1 output or enrich machines: {e}")

    final_result.setdefault("ribif_metadata", {})
    final_result["ribif_metadata"]["module1_id"] = module1_id

    return jsonify({"message": "Success", "data": final_result})
