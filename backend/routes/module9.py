from flask import Blueprint, jsonify, request

from pathlib import Path
from config import BASE_URL, OUTPUT_DIRS, SKIP_MODULE_9
from supabase_utils import get_supabase, insert_catalog
from utils.module_9.core import RIBIFModule9Catalog, CatalogInput
from utils.app_helpers import get_request_user_id, load_template_payload, upload_and_register_file

bp_module9 = Blueprint("module9", __name__)


@bp_module9.route("/api/module9/catalog", methods=["POST"])
def generate_catalog_module9():
    try:
        if SKIP_MODULE_9:
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
        result = generator.generate_catalog(catalog_input, base_url=BASE_URL)

        data_payload = result.model_dump()
        pdf_file_id = None
        html_file_id = None

        response_payload = {
            "message": "Catalog generated successfully",
            "data": data_payload,
            "project_id": project_id,
            "pdf_file_id": pdf_file_id,
            "html_file_id": html_file_id,
        }

        client = get_supabase()
        owner_id = get_request_user_id()
        if client and project_id:
            try:
                pdf_path = Path(result.pdf_filepath) if result.pdf_filepath else None
                html_path = Path(result.html_filepath) if result.html_filepath else None
                if pdf_path and pdf_path.exists():
                    pdf_file_id, pdf_url = upload_and_register_file(
                        client=client,
                        project_id=project_id,
                        owner_id=owner_id,
                        local_path=str(pdf_path),
                        category="catalog-pdf",
                        label=result.pdf_filename,
                    )
                    response_payload["pdf_file_id"] = pdf_file_id
                    response_payload["data"]["pdf_download_url"] = pdf_url or response_payload["data"].get("pdf_download_url")
                if html_path and html_path.exists():
                    html_file_id, html_url = upload_and_register_file(
                        client=client,
                        project_id=project_id,
                        owner_id=owner_id,
                        local_path=str(html_path),
                        category="catalog-html",
                        label=result.html_filename,
                    )
                    response_payload["html_file_id"] = html_file_id
                    response_payload["data"]["html_download_url"] = html_url or response_payload["data"].get("html_download_url")
                insert_catalog(
                    client=client,
                    project_id=project_id,
                    module1_id=module1_id,
                    pdf_file_id=response_payload.get("pdf_file_id"),
                    html_file_id=response_payload.get("html_file_id"),
                    data=data_payload,
                )
            except Exception:
                pass

        return jsonify(response_payload)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
