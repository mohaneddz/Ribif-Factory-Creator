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
from utils.module_1.no_nulls import fill_all_nulls, verify_no_nulls
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
    sanitize_for_json,
)
from utils.image_selector import find_best_image, get_random_image
from utils.job_manager import job_manager
from vertex_utils import generate_image

import time
import uuid
from datetime import datetime

bp_module1 = Blueprint("module1", __name__)
extractor = RIBIFExtractor()

# Module 1 timeout configuration
MODULE1_TOTAL_TIMEOUT = int(os.getenv("MODULE1_TOTAL_TIMEOUT", "300"))  # 5 minutes default
MODULE1_ENRICHMENT_TIMEOUT = int(os.getenv("MODULE1_ENRICHMENT_TIMEOUT", "120"))  # 2 minutes for enrichment


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


# =========================================================
# ASYNC JOB ENDPOINTS
# =========================================================

@bp_module1.route("/api/module1/status", methods=["GET"])
def module1_job_status():
    """Poll job status."""
    job_id = request.args.get("job_id")
    if not job_id:
        return jsonify({"error": "Missing job_id parameter"}), 400
    
    status = job_manager.get_status(job_id)
    if not status:
        return jsonify({"error": "Job not found", "job_id": job_id}), 404
    
    return jsonify(status)


@bp_module1.route("/api/module1/result", methods=["GET"])
def module1_job_result():
    """Get job result (only when completed)."""
    job_id = request.args.get("job_id")
    if not job_id:
        return jsonify({"error": "Missing job_id parameter"}), 400
    
    result = job_manager.get_result(job_id)
    if not result:
        return jsonify({"error": "Job not found", "job_id": job_id}), 404
    
    # Sanitize result for JSON
    return jsonify(sanitize_for_json(result))


@bp_module1.route("/api/module1/process", methods=["POST"])
def process_module_1():
    """
    Process Module 1 - supports both sync and async modes.
    
    Query params:
        async=true: Return job_id immediately, poll /status and /result
        async=false (default): Wait for completion (legacy behavior)
    """
    module1_logger = get_logger("module1")
    
    # Check for async mode
    async_mode = request.args.get("async", "false").lower() == "true"
    
    try:
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

        # Extract request data before async (request context won't be available in thread)
        start_time = time.time()  # Track processing time
        project_id = get_request_project_id(include_form=True, include_json=True)
        settings = get_pipeline_settings()
        owner_id = get_request_user_id()
        
        # Handle file upload synchronously (must happen in request context)
        filepath = None
        filename = "source.pdf"
        download_error = None

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
            # If not in payload, try from DB - DISABLED per user request to prevent cross-project file reuse
            # if not object_path and project_id and client:
            #    try:
            #        res = client.table("projects").select("source_file_path").eq("id", project_id).single().execute()
            #        if res.data and res.data.get("source_file_path"):
            #            object_path = res.data.get("source_file_path")
            #    except Exception as e:
            #        module1_logger = get_logger("module1")
            #        module1_logger.warning(f"Failed to fetch source_file_path from DB: {e}")

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
        final_result = extraction_result.copy()
        try:
            # Set a reasonable timeout for the entire enrichment process
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("Enrichment process exceeded maximum time limit")
            
            # Only set signal alarm on Unix systems
            if hasattr(signal, 'SIGALRM'):
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(120)  # 2 minute timeout for entire enrichment (reduced from 5 min)
            
            try:
                enriched_result = enricher.process(extraction_result)
                final_result = enriched_result
            finally:
                # Cancel the alarm
                if hasattr(signal, 'SIGALRM'):
                    signal.alarm(0)

            # --- FIX: Process Stage 5 (Production Process) with hierarchy preservation ---
            from utils.module_1.stage5_utils import create_hierarchical_stage5_structure
            
            stage5 = final_result.get("stage_5_processus_production", {})
            procs = stage5.get("processus_production", [])
            
            if procs and isinstance(procs, list):
                module1_logger.info("Processing Stage 5 routings with hierarchy preservation...")
                
                # Create hierarchical structure with deduplication and normalization
                structured_data = create_hierarchical_stage5_structure(procs)
                
                # Update Stage 5 with new structure
                final_result["stage_5_processus_production"]["processes"] = structured_data["processes"]
                final_result["stage_5_processus_production"]["ui_steps"] = structured_data["ui_steps"]
                final_result["stage_5_processus_production"]["total_steps"] = structured_data["total_steps"]
                final_result["stage_5_processus_production"]["total_ui_steps"] = structured_data["total_ui_steps"]
                final_result["stage_5_processus_production"]["total_groups"] = structured_data["total_groups"]
                
                # Keep processus_production as alias to ui_steps for backward compatibility
                final_result["stage_5_processus_production"]["processus_production"] = structured_data["ui_steps"]
                final_result["stage_5_processus_production"]["steps_view"] = "ui_flattened"
                
                # Log summary
                module1_logger.info(
                    f"Stage 5 processed: {structured_data['total_groups']} product groups, "
                    f"{structured_data['total_steps']} total steps, "
                    f"{structured_data['total_ui_steps']} UI steps"
                )
                
                if structured_data["duplicate_count"] > 0:
                    module1_logger.info(
                        f"Removed {structured_data['duplicate_count']} duplicate steps during deduplication"
                    )

        except Exception as e:
            module1_logger.error(f"Enrichment pipeline failed: {e}", exc_info=True)
            # final_result already set to extraction_result.copy() above

        # --- FILTER MANDATORY MACHINES ONLY ---
        # Extract only mandatory machines (those with quantite_necessaire > 0 or explicitly required)
        all_machines = final_result.get("stage_4_machines_equipements", {}).get("machines_production", []) or []
        
        # Filter out non-mandatory machines
        mandatory_machines = []
        excluded_count = 0
        for machine in all_machines:
            raw_quantite = machine.get("quantite_necessaire", 0)
            # Safely extract integer from quantite - handle cases where it might be a dict
            if isinstance(raw_quantite, dict):
                raw_quantite = raw_quantite.get("value", raw_quantite.get("quantity", 0))
            try:
                quantite = int(raw_quantite) if raw_quantite else 0
            except (TypeError, ValueError):
                quantite = 0
            nom = machine.get("nom_machine", "")
            
            # Keep machines that have a specified quantity OR are explicitly marked as core production equipment
            # Exclude auxiliary/support equipment with 0 quantity
            if quantite > 0:
                mandatory_machines.append(machine)
            else:
                # If quantity is 0, only keep if it's a core production machine (not AGV, ASRS, etc.)
                machine_type = machine.get("type", "").lower()
                use_desc = machine.get("use", "").lower()
                
                # Exclude generic logistics/support equipment with 0 quantity
                is_auxiliary = any(keyword in nom.lower() for keyword in ["agv", "asrs", "véhicule guidé", "stockage automatisé"])
                
                if not is_auxiliary:
                    # Keep core production machines even with 0 quantity if they're essential
                    if any(keyword in machine_type or keyword in use_desc for keyword in 
                           ["injection", "extrusion", "thermoformage", "presse", "robot", "ligne"]):
                        mandatory_machines.append(machine)
                    else:
                        excluded_count += 1
                else:
                    excluded_count += 1
        
        if excluded_count > 0:
            module1_logger.info(f"Filtered out {excluded_count} non-mandatory/auxiliary machines. Keeping {len(mandatory_machines)} mandatory machines.")
        
        # --- IMAGE GENERATION & FINAL ASSETS ---
        # We still want to ensure every machine has an image, generating them if web search didn't find one.
        machines = mandatory_machines
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

        # === FINAL SAFETY NET: Fill ALL remaining nulls ===
        module1_logger.info("Running final no-nulls safety pass...")
        try:
            final_result = fill_all_nulls(final_result, use_llm=False)
            null_check = verify_no_nulls(final_result)
            if null_check["has_nulls"]:
                module1_logger.warning(f"Still have {null_check['null_count']} null values after final fill")
            else:
                module1_logger.info("✓ All fields populated - no nulls remaining")
        except Exception as e:
            module1_logger.warning(f"Final no-nulls pass failed: {e}")

        output_file = OUTPUT_DIRS["module1"] / f"{Path(filename).stem}_complete_pipeline.json"
        write_json(output_file, final_result)

        final_result["module1_output_path"] = str(output_file)
        final_result["module1_download_url"] = f"{BASE_URL}/download/{output_file.name}"

        module1_id = None
        if client and project_id:
            # WRAP ALL DB/STORAGE OPERATIONS IN TRY/EXCEPT - failures shouldn't crash response
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
            except Exception as e:
                module1_logger.warning(f"Failed to insert module1 extraction: {e}")
            
            # Upload output file - non-blocking
            try:
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
            except Exception as e:
                module1_logger.warning(f"Failed to upload module1 output file: {e}")

            # Upload machine images - non-blocking, don't crash on individual failures
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
                    except Exception as img_err:
                        module1_logger.warning(f"Failed to upload image for {name}: {img_err}")
                        continue

            # Insert machines to DB - non-blocking
            try:
                machine_ids = insert_machines_from_stage(client, project_id, machines, image_meta)
                for name, meta in image_meta.items():
                    machine_id = machine_ids.get(name)
                    file_id = meta.get("image_file_id")
                    if machine_id and file_id:
                        try:
                            insert_machine_assets(client, machine_id, file_id, asset_type="image", label=name)
                        except Exception as asset_err:
                            module1_logger.warning(f"Failed to insert machine asset for {name}: {asset_err}")
            except Exception as db_err:
                module1_logger.warning(f"Failed to insert machines to DB: {db_err}")

        final_result.setdefault("ribif_metadata", {})
        final_result["ribif_metadata"]["module1_id"] = module1_id

        return jsonify(sanitize_for_json({"message": "Success", "data": final_result}))
    except Exception as e:
        module1_logger.error(f"Critical module1 failure: {e}", exc_info=True)
        # Ensure we always return a valid response even on catastrophic failure
        return jsonify({
            "error": str(e), 
            "status": "error",
            "message": "Module 1 processing failed. Please check the logs for details."
        }), 500
