from flask import Blueprint, jsonify, request

from pathlib import Path
from config import BASE_URL, OUTPUT_DIRS, SKIP_MODULE_9
from supabase_utils import get_supabase, insert_catalog
# Heavy imports moved to lazy loading for faster startup
from utils.app_helpers import get_request_user_id, load_template_payload, upload_and_register_file, upload_bytes_and_register_file
from utils.logger import log_skip, get_logger

logger = get_logger(__name__)
bp_module9 = Blueprint("module9", __name__)


@bp_module9.route("/api/module9/catalog", methods=["POST"])
def generate_catalog_module9():
    try:
        if SKIP_MODULE_9:
            log_skip("module9.generate_catalog_module9", reason="SKIP_MODULE_9")
            payload = load_template_payload("module9") or {}
            project_id = request.get_json(silent=True) or {}
            pid = project_id.get("project_id") or project_id.get("module1_data", {}).get("project_id")
            if isinstance(payload, dict) and pid:
                payload["project_id"] = payload.get("project_id") or pid
            return jsonify(payload)

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
        
        # Use in-memory generation for serverless environments
        result = generator.generate_catalog_in_memory(catalog_input)

        pdf_file_id = None
        pdf_url = None

        client = get_supabase()
        owner_id = get_request_user_id()
        if client and project_id:
            try:
                # Upload PDF content directly to Supabase (no local file)
                pdf_content = result.get("pdf_content")
                pdf_filename = result.get("pdf_filename")
                if pdf_content and pdf_filename:
                    pdf_file_id, pdf_url = upload_bytes_and_register_file(
                        client=client,
                        project_id=project_id,
                        owner_id=owner_id,
                        data=pdf_content,
                        filename=pdf_filename,
                        category="catalog-pdf",
                        content_type="application/pdf",
                        label=pdf_filename,
                    )
                
                # Remove bytes from result for JSON serialization
                data_payload = {k: v for k, v in result.items() if k != "pdf_content"}
                data_payload["pdf_download_url"] = pdf_url
                
                insert_catalog(
                    client=client,
                    project_id=project_id,
                    module1_id=module1_id,
                    pdf_file_id=pdf_file_id,
                    html_file_id=None,
                    data=data_payload,
                )
                logger.info("Catalog data saved to project %s", project_id)
            except Exception as e:
                logger.error("Failed to save catalog to DB: %s", e)
                # Continue with response even if DB save fails
                data_payload = {k: v for k, v in result.items() if k != "pdf_content"}
        else:
            data_payload = {k: v for k, v in result.items() if k != "pdf_content"}

        response_payload = {
            "message": "Catalog generated successfully",
            "data": data_payload,
            "project_id": project_id,
            "pdf_file_id": pdf_file_id,
            "html_file_id": None,
        }

        return jsonify(response_payload)
    except Exception as e:
        logger.error("Catalog generation failed: %s", e, exc_info=True)
        return jsonify({"error": str(e)}), 500
