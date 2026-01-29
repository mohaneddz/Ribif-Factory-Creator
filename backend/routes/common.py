from pathlib import Path
from flask import Blueprint, jsonify, send_file

from config import OUTPUT_DIRS

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
