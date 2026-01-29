from flask import Blueprint, jsonify, request

from config import OUTPUT_DIRS
from utils.app_helpers import get_request_project_id

bp_module2 = Blueprint("module2", __name__)


@bp_module2.route("/api/module2/layout", methods=["POST"])
def generate_layout():
    try:
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

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
