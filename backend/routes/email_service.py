import json
from datetime import datetime
from flask import Blueprint, jsonify, request

from config import OUTPUT_DIRS, write_json
from utils.app_helpers import get_request_project_id
from utils.email_service import send_email, poll_inbox, watch_inbox, extract_contacts, scrape_company
from utils.logger import get_logger

bp_email_service = Blueprint("email_service", __name__)
logger = get_logger(__name__)


def _parse_payload():
    if request.is_json:
        return request.get_json(silent=True) or {}
    if request.form:
        payload = dict(request.form)
        for key, value in list(payload.items()):
            if isinstance(value, str) and value.strip().startswith(("{", "[")):
                try:
                    payload[key] = json.loads(value)
                except Exception:
                    payload[key] = value
        return payload
    return {}


def _persist_output(tag: str, result: dict) -> None:
    output_dir = OUTPUT_DIRS.get("email")
    if not output_dir:
        return
    ts = int(datetime.utcnow().timestamp())
    write_json(output_dir / f"email_{tag}_{ts}.json", result)


@bp_email_service.route("/api/email/send", methods=["POST"])
def email_send():
    try:
        payload = _parse_payload()
        result = send_email(payload)
        project_id = get_request_project_id(include_json=True, include_form=True)
        if project_id:
            result["project_id"] = project_id
        _persist_output("send", result)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc), "status": "error"}), 500


@bp_email_service.route("/api/email/poll", methods=["POST"])
def email_poll():
    try:
        payload = _parse_payload()
        result = poll_inbox(payload, write_state=True)
        project_id = get_request_project_id(include_json=True, include_form=True)
        if project_id:
            result["project_id"] = project_id
        _persist_output("poll", result)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc), "status": "error"}), 500


@bp_email_service.route("/api/email/watch", methods=["POST"])
def email_watch():
    try:
        payload = _parse_payload()
        result = watch_inbox(payload)
        project_id = get_request_project_id(include_json=True, include_form=True)
        if project_id:
            result["project_id"] = project_id
        _persist_output("watch", result)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc), "status": "error"}), 500


@bp_email_service.route("/api/email/contacts", methods=["POST"])
def email_contacts():
    try:
        payload = _parse_payload()
        result = extract_contacts(payload)
        project_id = get_request_project_id(include_json=True, include_form=True)
        if project_id:
            result["project_id"] = project_id
        _persist_output("contacts", result)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc), "status": "error"}), 500


@bp_email_service.route("/api/email/scrape-company", methods=["POST"])
def email_scrape_company():
    try:
        payload = _parse_payload()
        result = scrape_company(payload)
        project_id = get_request_project_id(include_json=True, include_form=True)
        if project_id:
            result["project_id"] = project_id
        _persist_output("company", result)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc), "status": "error"}), 500
