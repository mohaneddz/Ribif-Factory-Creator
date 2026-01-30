import base64
import os
import shutil
from pathlib import Path

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from config import BASE_URL, OUTPUT_DIRS, UPLOAD_DIR, CREATE_IMAGES, SKIP_MODULE_1, write_json
from supabase_utils import get_supabase, insert_module1_extraction
from utils.module_1.core import RIBIFExtractor
from utils.logger import log_skip
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
from utils.image_selector import find_best_image
from vertex_utils import generate_image

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

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No filename"}), 400

    filename = secure_filename(file.filename)
    filepath = UPLOAD_DIR / filename
    file.save(filepath)

    settings = get_pipeline_settings()
    project_id = get_request_project_id(include_form=True)
    owner_id = get_request_user_id()
    client = get_supabase()
    project_id = ensure_project_id(client, project_id, owner_id, Path(filename).stem or "Project")
    if client and project_id and settings:
        try:
            store_project_settings(client, project_id, settings, owner_id)
        except Exception:
            pass

    source_file_id = None
    source_file_url = None
    source_object_path = None
    if client and project_id:
        try:
            source_file_id, source_file_url, source_object_path = upload_with_name_timestamp(
                client=client,
                project_id=project_id,
                owner_id=owner_id,
                local_path=str(filepath),
                category="uploads",
                label="module1_source",
            )
        except Exception:
            pass

    extraction_result = extractor.process_document(str(filepath), str(OUTPUT_DIRS["module1"]))

    machines = extraction_result.get("stage_4_machines_equipements", {}).get("machines_production", []) or []

    enriched_machines = []
    for machine_data in machines:
        nom_machine = machine_data.get("nom_machine", "Unknown")
        machine_type = machine_data.get("type", "industrial machine")
        manufacturer = machine_data.get("fabricant_recommande", "")

        image_result = {"image_url": None, "status": "skipped"}
        image_local_path = None
        image_download_url = None

        if CREATE_IMAGES and settings.get("enableMachineImages", True):
            image_result = generate_machine_image(nom_machine, machine_type, manufacturer)
            image_local_path = image_result.get("image_path")
        else:
            cached = find_best_image(nom_machine)
            if cached:
                target_path = OUTPUT_DIRS["module1"] / cached.name
                if not target_path.exists():
                    shutil.copyfile(cached, target_path)
                image_local_path = str(target_path)

        if image_local_path:
            image_download_url = f"{BASE_URL}/download/{Path(image_local_path).name}"

        enriched_machine = {
            "nom_machine": nom_machine,
            "type": machine_type,
            "fabricant_recommande": manufacturer,
            "quantite_necessaire": machine_data.get("quantite_necessaire", 1),
            "use": machine_data.get("use", ""),
            "specifications": machine_data.get("specifications", {}),
            "performance": machine_data.get("performance", {}),
            "image_url": image_result.get("image_url"),
            "image_status": image_result.get("status"),
            "image_local_path": image_local_path,
            "image_download_url": image_download_url,
            "source": "vertex_extraction",
        }
        enriched_machines.append(enriched_machine)

    final_result = extraction_result.copy()
    final_result["enriched_machines"] = enriched_machines
    final_result["scraping_summary"] = {
        "total_machines": len(machines),
        "successful_scrapes": sum(1 for m in enriched_machines if m.get("image_status") == "success"),
        "failed_scrapes": sum(1 for m in enriched_machines if m.get("image_status") != "success"),
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
            module1_id = insert_module1_extraction(client, project_id, source_file_id, final_result)
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

        except Exception:
            pass

    final_result.setdefault("ribif_metadata", {})
    final_result["ribif_metadata"]["module1_id"] = module1_id

    return jsonify({"message": "Success", "data": final_result})
