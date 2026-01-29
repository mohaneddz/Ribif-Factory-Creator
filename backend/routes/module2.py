from pathlib import Path
from flask import Blueprint, jsonify, request

from config import OUTPUT_DIRS, SKIP_MODULE_2
from supabase_utils import get_supabase, insert_layout
from utils.app_helpers import (
    get_request_project_id,
    get_request_user_id,
    load_template_payload,
    upload_and_register_file,
)

bp_module2 = Blueprint("module2", __name__)


@bp_module2.route("/api/module2/layout", methods=["POST"])
def generate_layout():
    try:
        if SKIP_MODULE_2:
            payload = load_template_payload("module2") or {}
            project_id = get_request_project_id(include_json=True)
            if isinstance(payload, dict) and project_id:
                payload["project_id"] = payload.get("project_id") or project_id
            return jsonify(payload)

        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        project_id = get_request_project_id(include_json=True)

        product = data.get("product", {})
        machines = data.get("machines", [])
        if not machines:
            return jsonify({"error": "Missing required field: machines"}), 400

        output_dir = OUTPUT_DIRS["module2"]
        result = {
            "layout_2d": str(output_dir / "layout_square.png"),
            "layout_3d": str(output_dir / "factory_model.glb"),
            "product": product,
        }
        if project_id:
            result["project_id"] = project_id

        layout_2d_file_id = None
        layout_3d_file_id = None
        client = get_supabase()
        owner_id = get_request_user_id()
        if client and project_id:
            try:
                layout_2d = Path(result.get("layout_2d", ""))
                if layout_2d.exists():
                    layout_2d_file_id, _ = upload_and_register_file(
                        client=client,
                        project_id=project_id,
                        owner_id=owner_id,
                        local_path=str(layout_2d),
                        category="layout-2d",
                        label=layout_2d.name,
                    )
                layout_3d = Path(result.get("layout_3d", ""))
                if layout_3d.exists():
                    layout_3d_file_id, _ = upload_and_register_file(
                        client=client,
                        project_id=project_id,
                        owner_id=owner_id,
                        local_path=str(layout_3d),
                        category="layout-3d",
                        label=layout_3d.name,
                    )
                insert_layout(
                    client=client,
                    project_id=project_id,
                    pipeline_id=None,
                    layout_2d_file_id=layout_2d_file_id,
                    layout_3d_file_id=layout_3d_file_id,
                    data=result,
                )
            except Exception:
                pass

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
