from pathlib import Path
from flask import Blueprint, jsonify, send_file, request
from flask_cors import cross_origin

from config import OUTPUT_DIRS
from utils.app_helpers import load_template_payload, get_request_project_id
from supabase_utils import get_supabase, delete_project_files, delete_project

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
    OUTPUT_DIRS["email"],
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


@bp_common.route("/api/projects/<string:project_id>", methods=["DELETE"])
@cross_origin()
def delete_project_endpoint(project_id: str):
    """
    Delete a project and all its associated files from storage.
    """
    if not project_id:
        return jsonify({"error": "Project ID is required"}), 400
    
    client = get_supabase()
    if not client:
        return jsonify({"error": "Supabase client not available"}), 500
    
    try:
        # First, delete all files from the storage bucket
        files_deleted, files_error = delete_project_files(client, project_id)
        
        if files_error:
            return jsonify({
                "error": f"Failed to delete project files: {files_error}",
                "files_deleted": files_deleted
            }), 500
        
        # Then delete the project from the database
        db_error = delete_project(client, project_id)
        
        if db_error:
            return jsonify({
                "error": f"Failed to delete project from database: {db_error}",
                "files_deleted": files_deleted
            }), 500
        
        return jsonify({
            "success": True,
            "message": "Project deleted successfully",
            "files_deleted": files_deleted
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500
