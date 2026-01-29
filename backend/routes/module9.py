from flask import Blueprint, jsonify, request

from config import BASE_URL, OUTPUT_DIRS
from utils.module_9.core import RIBIFModule9Catalog, CatalogInput

bp_module9 = Blueprint("module9", __name__)


@bp_module9.route("/api/module9/catalog", methods=["POST"])
def generate_catalog_module9():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        payload = data
        if "module1_data" not in payload:
            payload = {"module1_data": data}

        project_id = payload.get("project_id") or payload.get("module1_data", {}).get("project_id")
        module1_id = payload.get("module1_id") or payload.get("module1_data", {}).get("module1_id")

        catalog_input = CatalogInput(**payload)
        generator = RIBIFModule9Catalog(image_base_path=catalog_input.image_base_path)
        result = generator.generate_catalog(catalog_input, base_url=BASE_URL)

        data_payload = result.model_dump()
        pdf_file_id = None
        html_file_id = None

        return jsonify({
            "message": "Catalog generated successfully",
            "data": data_payload,
            "project_id": project_id,
            "pdf_file_id": pdf_file_id,
            "html_file_id": html_file_id,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
