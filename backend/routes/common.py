from pathlib import Path
from flask import Blueprint, jsonify, send_file

from config import OUTPUT_DIRS
from utils.app_helpers import load_template_payload, get_request_project_id

bp_common = Blueprint("common", __name__)

DOWNLOAD_FOLDERS = [
    OUTPUT_DIRS["module1"],
    OUTPUT_DIRS["module2"],
    OUTPUT_DIRS["module3"],
    OUTPUT_DIRS["module4"],
    OUTPUT_DIRS["module6"],
    OUTPUT_DIRS["module7"],
    OUTPUT_DIRS["module8"],
    OUTPUT_DIRS["module9"],
    OUTPUT_DIRS["catalogs"],
    OUTPUT_DIRS["videos"],
]


@bp_common.route("/download/<path:filename>", methods=["GET"])
def download_file(filename: str):
    safe_name = Path(filename).name
    for folder in DOWNLOAD_FOLDERS:
        candidate = folder / safe_name
        if candidate.exists() and candidate.is_file():
            return send_file(candidate, as_attachment=True)
    return jsonify({"error": "File not found"}), 404


@bp_common.route("/api/templates/<string:step>", methods=["GET"])
def get_template(step: str):
    payload = load_template_payload(step)
    if payload is None:
        return jsonify({"error": "Template not found"}), 404
    project_id = get_request_project_id(include_json=True, include_form=True)
    if project_id:
        if isinstance(payload, dict):
            if "project_id" in payload:
                payload["project_id"] = project_id
            if "data" in payload and isinstance(payload["data"], dict):
                payload["data"]["project_id"] = payload["data"].get("project_id") or project_id
            if "ribif_metadata" in payload and isinstance(payload["ribif_metadata"], dict):
                payload["ribif_metadata"]["project_id"] = payload["ribif_metadata"].get("project_id") or project_id
            if "data" in payload and isinstance(payload["data"], dict):
                meta = payload["data"].get("ribif_metadata")
                if isinstance(meta, dict):
                    meta["project_id"] = meta.get("project_id") or project_id
    return jsonify(payload)
