import base64
import json
import os
from datetime import datetime
from pathlib import Path
from flask import Blueprint, jsonify, request

from config import OUTPUT_DIRS, write_json
from utils.module_5.core import (
    run_text_negotiation,
    run_voice_negotiation,
    summarize_best_offer,
    evaluate_offer,
    compute_counter_offer,
    NegotiationConfig,
)
from utils.module_5.negotiation_manager import (
    NegotiationThread,
    NegotiationStatus,
    create_thread_from_supplier,
    load_thread,
    save_thread,
    list_threads,
    add_email_to_thread,
    update_thread_status,
    update_supplier_offer,
    update_counter_offer,
    increment_round,
    should_auto_accept,
    should_stop_negotiation,
    generate_initial_rfq_email,
    generate_initial_rfq_subject,
    generate_reply_subject,
    generate_negotiation_email,
    generate_acceptance_email,
    parse_supplier_response,
)
from utils.email_service import send_email, poll_inbox, watch_inbox
from utils.app_helpers import get_request_project_id
from utils.logger import get_logger

logger = get_logger(__name__)

bp_module5 = Blueprint("module5", __name__)


# ================================
# Configuration
# ================================

# Default SMTP/IMAP config for negotiation emails (override via env or payload)
NEGOTIATION_SMTP_HOST = os.getenv("NEGOTIATION_SMTP_HOST", os.getenv("SMTP_HOST", "smtp.gmail.com"))
NEGOTIATION_SMTP_PORT = int(os.getenv("NEGOTIATION_SMTP_PORT", os.getenv("SMTP_PORT", "587")))
NEGOTIATION_SMTP_USERNAME = os.getenv("NEGOTIATION_SMTP_USERNAME", os.getenv("SMTP_USERNAME", ""))
NEGOTIATION_SMTP_PASSWORD = os.getenv("NEGOTIATION_SMTP_PASSWORD", os.getenv("SMTP_PASSWORD", ""))
NEGOTIATION_IMAP_HOST = os.getenv("NEGOTIATION_IMAP_HOST", os.getenv("IMAP_HOST", "imap.gmail.com"))
NEGOTIATION_IMAP_PORT = int(os.getenv("NEGOTIATION_IMAP_PORT", os.getenv("IMAP_PORT", "993")))

# Test email override - if set, ALL supplier emails will be replaced with this address
# Leave empty to use the original supplier emails from JSON
TEST_RECIPIENT_EMAIL = os.getenv("TEST_RECIPIENT_EMAIL", "").strip()


def _get_email_config(payload: dict = None) -> dict:
    """Get email configuration from payload or env"""
    payload = payload or {}
    return {
        "smtp_host": payload.get("smtp_host") or NEGOTIATION_SMTP_HOST,
        "smtp_port": payload.get("smtp_port") or NEGOTIATION_SMTP_PORT,
        "smtp_username": payload.get("smtp_username") or NEGOTIATION_SMTP_USERNAME,
        "smtp_password": payload.get("smtp_password") or NEGOTIATION_SMTP_PASSWORD,
        "imap_host": payload.get("imap_host") or NEGOTIATION_IMAP_HOST,
        "imap_port": payload.get("imap_port") or NEGOTIATION_IMAP_PORT,
        "imap_username": payload.get("imap_username") or NEGOTIATION_SMTP_USERNAME,
        "imap_password": payload.get("imap_password") or NEGOTIATION_SMTP_PASSWORD,
    }


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


# ================================
# Email Negotiation Endpoints
# ================================

@bp_module5.route("/api/module5/negotiations/start", methods=["POST"])
def start_negotiation():
    """
    Start negotiations with suppliers from Module 4 output.
    
    Payload:
    {
        "suppliers": [
            {
                "supplier_name": "...",
                "email_address": "...",
                "website": "...",
                "price_estimate": "...",
                ...
            }
        ],
        "machine": {
            "nom_machine": "...",
            "type": "...",
            "quantite_necessaire": 2
        },
        "buyer_requirements": {
            "target_price": 500000,
            "max_price": 600000,
            "currency": "EUR",
            "preferred_incoterms": ["DDP", "CIF"],
            "max_lead_time_days": 90,
            "min_warranty_months": 24,
            "max_deposit_pct": 30
        },
        "buyer_email": "buyer@company.com",
        "buyer_company": "RIBIF Algeria",
        "buyer_contact_name": "Ibrahim",
        "send_emails": true,
        "smtp_username": "...",  // optional, uses env if not provided
        "smtp_password": "..."   // optional, uses env if not provided
    }
    
    Returns created threads and optionally sends initial RFQ emails.
    """
    try:
        if not request.is_json:
            return jsonify({"error": "Expected JSON input"}), 400
        
        payload = request.get_json() or {}
        project_id = get_request_project_id(include_json=True)
        
        suppliers = payload.get("suppliers", [])
        machine = payload.get("machine", {})
        buyer_requirements = payload.get("buyer_requirements", {})
        buyer_email = payload.get("buyer_email", "")
        buyer_company = payload.get("buyer_company", "RIBIF Algeria")
        buyer_contact_name = payload.get("buyer_contact_name", "")
        send_emails = payload.get("send_emails", False)
        
        if not suppliers:
            return jsonify({"error": "No suppliers provided"}), 400
        if not buyer_email:
            return jsonify({"error": "buyer_email is required"}), 400
        
        email_config = _get_email_config(payload)
        
        created_threads = []
        send_results = []
        
        # Log if using test email override
        if TEST_RECIPIENT_EMAIL:
            logger.info(f"TEST MODE: All emails will be sent to {TEST_RECIPIENT_EMAIL}")
        
        for supplier in suppliers:
            # Get original email, then apply test override if configured
            original_email = supplier.get("email_address", "")
            supplier_email = TEST_RECIPIENT_EMAIL if TEST_RECIPIENT_EMAIL else original_email
            
            if not supplier_email:
                logger.warning(f"Skipping supplier {supplier.get('supplier_name')} - no email")
                continue
            
            # Update supplier dict with the (possibly overridden) email for thread creation
            supplier["email_address"] = supplier_email
            
            # Create negotiation thread
            thread = create_thread_from_supplier(
                supplier=supplier,
                machine=machine,
                buyer_requirements=buyer_requirements,
                buyer_email=buyer_email,
                buyer_company=buyer_company,
                buyer_contact_name=buyer_contact_name,
                project_id=project_id,
            )
            
            if send_emails:
                # Generate and send initial RFQ
                try:
                    subject = generate_initial_rfq_subject(thread)
                    body = generate_initial_rfq_email(thread)
                    
                    send_payload = {
                        **email_config,
                        "to": [supplier_email],
                        "subject": subject,
                        "text": body,
                        "from_address": buyer_email,
                        "reply_to": buyer_email,
                    }
                    
                    result = send_email(send_payload)
                    
                    # Record email in thread
                    add_email_to_thread(
                        thread=thread,
                        message_id=result.get("message_id", ""),
                        direction="outbound",
                        subject=subject,
                        body_text=body,
                        from_address=buyer_email,
                        to_address=supplier_email,
                    )
                    
                    # Update status
                    update_thread_status(thread, NegotiationStatus.INITIAL_SENT)
                    thread.round_number = 1
                    save_thread(thread)
                    
                    send_results.append({
                        "thread_id": thread.thread_id,
                        "supplier": supplier.get("supplier_name"),
                        "status": "sent",
                        "message_id": result.get("message_id"),
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to send email to {supplier_email}: {e}")
                    send_results.append({
                        "thread_id": thread.thread_id,
                        "supplier": supplier.get("supplier_name"),
                        "status": "failed",
                        "error": str(e),
                    })
            
            created_threads.append(thread.to_dict())
        
        return jsonify({
            "status": "success",
            "threads_created": len(created_threads),
            "threads": created_threads,
            "send_results": send_results if send_emails else None,
            "project_id": project_id,
        })
        
    except Exception as e:
        logger.exception("Error starting negotiation")
        return jsonify({"error": str(e), "status": "error"}), 500


@bp_module5.route("/api/module5/negotiations/list", methods=["GET", "POST"])
def list_negotiations():
    """
    List all negotiation threads.
    
    Query params or JSON payload:
    - project_id: Filter by project
    - status: Filter by status (draft, initial_sent, pending_reply, negotiating, accepted, rejected, closed)
    """
    try:
        if request.is_json:
            payload = request.get_json() or {}
        else:
            payload = {}
        
        project_id = payload.get("project_id") or request.args.get("project_id")
        status = payload.get("status") or request.args.get("status")
        
        threads = list_threads(project_id=project_id, status=status)
        
        return jsonify({
            "status": "success",
            "count": len(threads),
            "threads": [t.to_dict() for t in threads],
        })
        
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500


@bp_module5.route("/api/module5/negotiations/<thread_id>", methods=["GET"])
def get_negotiation(thread_id: str):
    """Get a specific negotiation thread by ID"""
    try:
        thread = load_thread(thread_id)
        if not thread:
            return jsonify({"error": "Thread not found"}), 404
        
        return jsonify({
            "status": "success",
            "thread": thread.to_dict(),
        })
        
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500


@bp_module5.route("/api/module5/negotiations/check-replies", methods=["POST"])
def check_replies():
    """
    Check inbox for supplier replies and match to threads.
    
    Payload:
    {
        "project_id": "optional - filter threads",
        "thread_ids": ["optional - specific threads to check"],
        "timeout_s": 30,  // optional, use 0 for instant check
        "imap_username": "...",  // optional
        "imap_password": "..."   // optional
    }
    """
    try:
        if not request.is_json:
            return jsonify({"error": "Expected JSON input"}), 400
        
        payload = request.get_json() or {}
        project_id = payload.get("project_id") or get_request_project_id(include_json=True)
        thread_ids = payload.get("thread_ids", [])
        timeout_s = payload.get("timeout_s", 0)
        
        email_config = _get_email_config(payload)
        
        # Get threads to check
        if thread_ids:
            threads = [load_thread(tid) for tid in thread_ids]
            threads = [t for t in threads if t is not None]
        else:
            # Get all threads waiting for replies
            threads = list_threads(
                project_id=project_id,
                status=None  # Check all statuses
            )
            threads = [t for t in threads if t.status in (
                NegotiationStatus.INITIAL_SENT.value,
                NegotiationStatus.PENDING_REPLY.value,
            )]
        
        if not threads:
            return jsonify({
                "status": "success",
                "message": "No threads waiting for replies",
                "matches": [],
            })
        
        # Build list of supplier emails to watch for
        supplier_emails = list(set(t.supplier_email for t in threads if t.supplier_email))
        
        matches = []
        
        for supplier_email in supplier_emails:
            # Poll inbox for emails from this supplier
            poll_payload = {
                **email_config,
                "from_address": supplier_email,
                "unseen_only": True,
                "include_body": True,
                "include_attachments": False,
                "mark_seen": False,  # Don't mark as seen until processed
            }
            
            if timeout_s > 0:
                poll_payload["timeout_s"] = timeout_s
                poll_payload["poll_interval_s"] = 5
                result = watch_inbox(poll_payload)
            else:
                result = poll_inbox(poll_payload)
            
            emails = result.get("emails", [])
            
            for email_data in emails:
                # Find matching thread
                for thread in threads:
                    if thread.supplier_email.lower() == supplier_email.lower():
                        # Check if this email is already recorded
                        existing_ids = [e.get("message_id") for e in thread.emails]
                        if email_data.get("message_id") in existing_ids:
                            continue
                        
                        # Parse the supplier's response
                        body_text = email_data.get("body_text", "")
                        parsed_offer = parse_supplier_response(body_text, thread)
                        
                        # Add email to thread
                        add_email_to_thread(
                            thread=thread,
                            message_id=email_data.get("message_id", ""),
                            direction="inbound",
                            subject=email_data.get("subject", ""),
                            body_text=body_text,
                            from_address=supplier_email,
                            to_address=thread.buyer_email,
                            parsed_offer=parsed_offer,
                        )
                        
                        # Update supplier offer and status
                        if parsed_offer:
                            cfg = NegotiationConfig()
                            evaluation = evaluate_offer(parsed_offer, thread.buyer_requirements, cfg)
                            update_supplier_offer(thread, parsed_offer, evaluation)
                        
                        update_thread_status(thread, NegotiationStatus.NEGOTIATING)
                        
                        matches.append({
                            "thread_id": thread.thread_id,
                            "supplier": thread.supplier_name,
                            "email_subject": email_data.get("subject"),
                            "parsed_offer": parsed_offer,
                            "message_id": email_data.get("message_id"),
                        })
                        break
        
        return jsonify({
            "status": "success",
            "threads_checked": len(threads),
            "matches_found": len(matches),
            "matches": matches,
        })
        
    except Exception as e:
        logger.exception("Error checking replies")
        return jsonify({"error": str(e), "status": "error"}), 500


@bp_module5.route("/api/module5/negotiations/<thread_id>/negotiate", methods=["POST"])
def negotiate_round(thread_id: str):
    """
    Run a negotiation round for a specific thread.
    
    Payload:
    {
        "send_email": true,  // whether to send the counter email
        "auto_accept": true,  // allow auto-acceptance if offer meets criteria
        "smtp_username": "...",  // optional
        "smtp_password": "..."   // optional
    }
    
    This will:
    1. Evaluate the current supplier offer
    2. Compute a counter-offer
    3. Generate a response email
    4. Optionally send the email
    5. Update thread state
    """
    try:
        if not request.is_json:
            return jsonify({"error": "Expected JSON input"}), 400
        
        payload = request.get_json() or {}
        send_email_flag = payload.get("send_email", True)
        auto_accept = payload.get("auto_accept", True)
        
        thread = load_thread(thread_id)
        if not thread:
            return jsonify({"error": "Thread not found"}), 404
        
        # Check if negotiation should stop
        should_stop, reason = should_stop_negotiation(thread)
        if should_stop:
            return jsonify({
                "status": "stopped",
                "reason": reason,
                "thread": thread.to_dict(),
            })
        
        # Get current supplier offer
        supplier_offer = thread.current_supplier_offer
        if not supplier_offer:
            return jsonify({
                "status": "error",
                "error": "No supplier offer to negotiate. Wait for a reply first.",
            }), 400
        
        # Evaluate offer
        cfg = NegotiationConfig()
        evaluation = evaluate_offer(supplier_offer, thread.buyer_requirements, cfg)
        
        # Check for auto-accept
        if auto_accept and should_auto_accept(thread, evaluation):
            # Generate acceptance email
            email_body = generate_acceptance_email(thread)
            subject = generate_reply_subject(thread)
            
            if send_email_flag:
                email_config = _get_email_config(payload)
                send_payload = {
                    **email_config,
                    "to": [thread.supplier_email],
                    "subject": subject,
                    "text": email_body,
                    "from_address": thread.buyer_email,
                    "reply_to": thread.buyer_email,
                }
                
                result = send_email(send_payload)
                
                add_email_to_thread(
                    thread=thread,
                    message_id=result.get("message_id", ""),
                    direction="outbound",
                    subject=subject,
                    body_text=email_body,
                    from_address=thread.buyer_email,
                    to_address=thread.supplier_email,
                )
            
            update_thread_status(thread, NegotiationStatus.ACCEPTED)
            
            return jsonify({
                "status": "accepted",
                "message": "Offer accepted",
                "evaluation": evaluation,
                "email_sent": send_email_flag,
                "email_body": email_body,
                "thread": thread.to_dict(),
            })
        
        # Compute counter-offer
        negotiation_state = {
            "round": thread.round_number,
            "max_rounds": thread.max_rounds,
        }
        counter_offer = compute_counter_offer(
            supplier_offer,
            thread.buyer_requirements,
            negotiation_state,
            cfg,
        )
        update_counter_offer(thread, counter_offer)
        
        # Generate negotiation email
        email_body = generate_negotiation_email(thread, evaluation, counter_offer)
        subject = generate_reply_subject(thread)
        
        send_result = None
        if send_email_flag:
            try:
                email_config = _get_email_config(payload)
                send_payload = {
                    **email_config,
                    "to": [thread.supplier_email],
                    "subject": subject,
                    "text": email_body,
                    "from_address": thread.buyer_email,
                    "reply_to": thread.buyer_email,
                }
                
                result = send_email(send_payload)
                
                add_email_to_thread(
                    thread=thread,
                    message_id=result.get("message_id", ""),
                    direction="outbound",
                    subject=subject,
                    body_text=email_body,
                    from_address=thread.buyer_email,
                    to_address=thread.supplier_email,
                )
                
                send_result = {"status": "sent", "message_id": result.get("message_id")}
                
            except Exception as e:
                send_result = {"status": "failed", "error": str(e)}
        
        # Update thread state
        increment_round(thread)
        update_thread_status(thread, NegotiationStatus.PENDING_REPLY)
        
        return jsonify({
            "status": "counter_sent" if send_email_flag else "counter_generated",
            "round": thread.round_number,
            "evaluation": evaluation,
            "counter_offer": counter_offer,
            "email_subject": subject,
            "email_body": email_body,
            "send_result": send_result,
            "next_action": evaluation.get("recommendation"),
            "thread": thread.to_dict(),
        })
        
    except Exception as e:
        logger.exception(f"Error in negotiation round for {thread_id}")
        return jsonify({"error": str(e), "status": "error"}), 500


@bp_module5.route("/api/module5/negotiations/<thread_id>/accept", methods=["POST"])
def accept_offer(thread_id: str):
    """Manually accept the current offer"""
    try:
        payload = request.get_json() or {} if request.is_json else {}
        send_email_flag = payload.get("send_email", True)
        
        thread = load_thread(thread_id)
        if not thread:
            return jsonify({"error": "Thread not found"}), 404
        
        email_body = generate_acceptance_email(thread)
        subject = generate_reply_subject(thread)
        
        if send_email_flag:
            email_config = _get_email_config(payload)
            send_payload = {
                **email_config,
                "to": [thread.supplier_email],
                "subject": subject,
                "text": email_body,
                "from_address": thread.buyer_email,
                "reply_to": thread.buyer_email,
            }
            
            result = send_email(send_payload)
            
            add_email_to_thread(
                thread=thread,
                message_id=result.get("message_id", ""),
                direction="outbound",
                subject=subject,
                body_text=email_body,
                from_address=thread.buyer_email,
                to_address=thread.supplier_email,
            )
        
        update_thread_status(thread, NegotiationStatus.ACCEPTED)
        
        return jsonify({
            "status": "success",
            "message": "Offer accepted",
            "email_sent": send_email_flag,
            "thread": thread.to_dict(),
        })
        
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500


@bp_module5.route("/api/module5/negotiations/<thread_id>/reject", methods=["POST"])
def reject_offer(thread_id: str):
    """Manually reject and close the negotiation"""
    try:
        payload = request.get_json() or {} if request.is_json else {}
        reason = payload.get("reason", "")
        
        thread = load_thread(thread_id)
        if not thread:
            return jsonify({"error": "Thread not found"}), 404
        
        update_thread_status(thread, NegotiationStatus.REJECTED)
        
        return jsonify({
            "status": "success",
            "message": "Negotiation rejected",
            "reason": reason,
            "thread": thread.to_dict(),
        })
        
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500


@bp_module5.route("/api/module5/negotiations/<thread_id>/close", methods=["POST"])
def close_negotiation(thread_id: str):
    """Close a negotiation thread without accepting or rejecting"""
    try:
        thread = load_thread(thread_id)
        if not thread:
            return jsonify({"error": "Thread not found"}), 404
        
        update_thread_status(thread, NegotiationStatus.CLOSED)
        
        return jsonify({
            "status": "success",
            "message": "Negotiation closed",
            "thread": thread.to_dict(),
        })
        
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500


@bp_module5.route("/api/module5/negotiations/summary", methods=["POST"])
def get_negotiations_summary():
    """
    Get a summary of all negotiations for a project.
    
    Payload:
    {
        "project_id": "optional"
    }
    """
    try:
        payload = request.get_json() or {} if request.is_json else {}
        project_id = payload.get("project_id") or get_request_project_id(include_json=True)
        
        threads = list_threads(project_id=project_id)
        
        status_counts = {}
        for t in threads:
            status_counts[t.status] = status_counts.get(t.status, 0) + 1
        
        # Find best offers across all threads
        best_offers = []
        for t in threads:
            if t.best_offer and t.best_offer.get("_score", 0) > 0:
                best_offers.append({
                    "thread_id": t.thread_id,
                    "supplier": t.supplier_name,
                    "machine": t.machine_name,
                    "offer": t.best_offer,
                    "status": t.status,
                })
        
        best_offers.sort(key=lambda x: x["offer"].get("_score", 0), reverse=True)
        
        return jsonify({
            "status": "success",
            "total_threads": len(threads),
            "status_breakdown": status_counts,
            "best_offers": best_offers[:5],  # Top 5
            "project_id": project_id,
        })
        
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500

