import base64
import json
from datetime import datetime
from flask import Blueprint, jsonify, request

from config import OUTPUT_DIRS, write_json
from utils.module_5.core import run_text_negotiation, run_voice_negotiation, summarize_best_offer
from utils.app_helpers import get_request_project_id

bp_module5 = Blueprint("module5", __name__)


def _parse_json_field(value):
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return json.loads(value)
        except Exception:
            return value
    return value


@bp_module5.route("/api/module5/text/negotiation", methods=["POST"])
def module5_text_negotiation():
    try:
        if not request.is_json:
            return jsonify({"error": "Expected JSON input"}), 400

        payload = request.get_json() or {}
        result = run_text_negotiation(payload)

        project_id = get_request_project_id(include_json=True)
        if project_id:
            result["project_id"] = project_id

        # Persist output for traceability
        output_dir = OUTPUT_DIRS.get("module5")
        if output_dir:
            filename = f"module_5_text_{int(datetime.utcnow().timestamp())}.json"
            write_json(output_dir / filename, result)

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500


@bp_module5.route("/api/module5/voice/negotiation", methods=["POST"])
def module5_voice_negotiation():
    try:
        payload = {}
        audio_bytes = None

        if request.is_json:
            payload = request.get_json() or {}
            if payload.get("audio_base64"):
                try:
                    audio_bytes = base64.b64decode(payload.get("audio_base64"))
                except Exception:
                    audio_bytes = None
        else:
            # form-data
            if request.form:
                for key in ["conversation", "buyer_requirements", "negotiation_state", "supplier_offer"]:
                    if key in request.form:
                        payload[key] = _parse_json_field(request.form.get(key))
                payload["supplier_text"] = request.form.get("supplier_text")
                payload["end_call"] = request.form.get("end_call") in ("1", "true", "True")
            if "audio" in request.files:
                f = request.files["audio"]
                audio_bytes = f.read()

        if audio_bytes:
            payload["audio_bytes"] = audio_bytes

        result = run_voice_negotiation(payload)

        project_id = get_request_project_id(include_json=True, include_form=True)
        if project_id:
            result["project_id"] = project_id

        # Persist output for traceability
        output_dir = OUTPUT_DIRS.get("module5")
        if output_dir:
            filename = f"module_5_voice_{int(datetime.utcnow().timestamp())}.json"
            write_json(output_dir / filename, result)

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500


@bp_module5.route("/api/module5/voice/summary", methods=["POST"])
def module5_voice_summary():
    try:
        if not request.is_json:
            return jsonify({"error": "Expected JSON input"}), 400
        payload = request.get_json() or {}
        conversation = payload.get("conversation") or []
        last_offer = payload.get("last_offer") or {}
        summary = summarize_best_offer(conversation, last_offer)
        return jsonify({"best_offer_summary": summary})
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500
