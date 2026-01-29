import json
from flask import Blueprint, jsonify, request

from config import OUTPUT_DIRS, SKIP_MODULE_4
from supabase_utils import get_supabase, insert_module4_sourcing
from utils.module_4.core import build_machines_enriched
from utils.app_helpers import (
    get_request_project_id,
    get_request_user_id,
    load_template_payload,
    upload_and_register_file,
)

bp_module4 = Blueprint("module4", __name__)


@bp_module4.route("/api/module4/enrich", methods=["POST"])
def enrich_machines_module4():
    try:
        if SKIP_MODULE_4:
            payload = load_template_payload("module4") or {}
            project_id = get_request_project_id(include_json=True)
            if isinstance(payload, dict) and project_id:
                payload["project_id"] = payload.get("project_id") or project_id
                meta = payload.get("ribif_metadata")
                if isinstance(meta, dict):
                    meta["project_id"] = meta.get("project_id") or project_id
            return jsonify(payload)

        project_id = get_request_project_id(include_json=True)
        module1_id = None

        if not request.is_json:
            return jsonify({"error": "Expected JSON input (module_1 output)"}), 400

        input_data = request.get_json()
        module1_id = input_data.get("module1_id") or input_data.get("ribif_metadata", {}).get("module1_id")

        machines = input_data.get("stage_4_machines_equipements", {}).get("machines_production", [])
        if not machines and "data" in input_data:
            machines = input_data["data"].get("stage_4_machines_equipements", {}).get("machines_production", [])
            input_data = input_data["data"]

        if not machines:
            return jsonify({"error": "No machines found in input."}), 400

        input_path = OUTPUT_DIRS["module4"] / "module_4_input.json"
        input_path.parent.mkdir(parents=True, exist_ok=True)
        input_path.write_text(json.dumps(input_data, ensure_ascii=False, indent=2), encoding="utf-8")

        output_path = OUTPUT_DIRS["module4"] / "module_4.json"
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
        if client and project_id:
            try:
                module4_id = insert_module4_sourcing(client, project_id, module1_id, result)
                result.setdefault("ribif_metadata", {})
                result["ribif_metadata"]["module4_id"] = module4_id
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
            except Exception:
                pass

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500
