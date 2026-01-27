import base64
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from flask import Blueprint, jsonify, request

from config import OUTPUT_DIRS, write_json
# Heavy imports moved to lazy loading for faster startup
# from utils.module_5.core import ...
from utils.module_5.negotiation_manager import (
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
    generate_voice_call_confirmation_email,
    generate_voice_call_confirmation_subject,
    generate_negotiation_link_email,
    generate_negotiation_link_subject,
    parse_supplier_response,
)
from utils.email_service import send_email, poll_inbox, watch_inbox
from utils.app_helpers import get_request_project_id
from utils.logger import get_logger
import supabase_utils

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

# Default test email override from env (can be overridden per-request via payload)
# If set, ALL supplier emails will be replaced with this address
# Leave empty to use the original supplier emails from JSON/scrapers
DEFAULT_TEST_RECIPIENT_EMAIL = os.getenv("TEST_RECIPIENT_EMAIL", "").strip()

# Log email config at startup for debugging
logger.info(f"Email config loaded: SMTP_HOST={NEGOTIATION_SMTP_HOST}, SMTP_USERNAME={NEGOTIATION_SMTP_USERNAME}, DEFAULT_TEST_RECIPIENT={DEFAULT_TEST_RECIPIENT_EMAIL}")


def get_test_recipient_email(payload: dict = None) -> str:
    """
    Get the test recipient email to use for overriding supplier emails.
    Priority:
    1. Request payload test_recipient_email (if provided and non-empty)
    2. Environment variable TEST_RECIPIENT_EMAIL (fallback)
    3. Empty string (use original supplier emails)
    """
    if payload:
        payload_email = payload.get("test_recipient_email", "").strip()
        if payload_email:
            return payload_email
    return DEFAULT_TEST_RECIPIENT_EMAIL


# ================================
# Module 4 → Module 5 Compatibility Layer
# ================================

def transform_module4_suppliers(suppliers: list) -> list:
    """
    Transform Module 4 supplier schema to Module 5 negotiation schema.
    
    Module 4 suppliers have:
    - emails: string[] (new field)
    - phones: string[] (new field)
    - contact_pages: string[] (new field)
    
    Module 5 expects:
    - email_address: string (required for negotiations)
    - phone: string (optional)
    
    Args:
        suppliers: List of supplier dicts from Module 4
        
    Returns:
        List of transformed supplier dicts compatible with Module 5
    """
    transformed = []
    
    for supplier in suppliers:
        # Create a copy to avoid modifying original
        supplier_copy = supplier.copy()
        
        # Transform emails array to single email_address
        emails = supplier.get('emails', [])
        if emails and len(emails) > 0:
            # Use first email
            supplier_copy['email_address'] = emails[0]
        elif 'email' in supplier:
            # Fallback: check for legacy 'email' field
            supplier_copy['email_address'] = supplier['email']
        else:
            # No email available - mark as unavailable
            supplier_copy['email_address'] = ""
            logger.warning(
                f"Supplier '{supplier.get('supplier_name', 'Unknown')}' has no email - "
                f"cannot be used for email negotiations"
            )
        
        # Transform phones array to single phone
        phones = supplier.get('phones', [])
        if phones and len(phones) > 0:
            supplier_copy['phone'] = phones[0]
        elif 'phone' not in supplier_copy:
            supplier_copy['phone'] = ""
        
        # Preserve all original fields for reference
        # (emails, phones, contact_pages arrays remain for future use)
        
        transformed.append(supplier_copy)
    
    # Filter out suppliers without email (cannot negotiate via email)
    negotiable = [s for s in transformed if s.get('email_address')]
    
    if len(negotiable) < len(transformed):
        logger.warning(
            f"Filtered out {len(transformed) - len(negotiable)} suppliers without email addresses. "
            f"{len(negotiable)} suppliers available for negotiation."
        )
    
    return negotiable


# ================================
# Utilities
# ================================


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
            filename = f"module_5_text_{int(datetime.now(timezone.utc).timestamp())}.json"
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
            filename = f"module_5_voice_{int(datetime.now(timezone.utc).timestamp())}.json"
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
            "currency": "DZD",
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
        
        # NEW: Transform Module 4 suppliers to Module 5 schema
        suppliers = transform_module4_suppliers(suppliers)
        
        if not suppliers:
            return jsonify({
                "error": "No suppliers with email addresses available for negotiation"
            }), 400
        
        email_config = _get_email_config(payload)
        
        created_threads = []
        send_results = []
        
        # Get test recipient email from payload or env
        test_recipient = get_test_recipient_email(payload)
        
        # Log if using test email override
        if test_recipient:
            logger.info(f"TEST MODE: All emails will be sent to {test_recipient}")
        
        for supplier in suppliers:
            # Get original email, then apply test override if configured
            original_email = supplier.get("email_address", "")
            supplier_email = test_recipient if test_recipient else original_email
            
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


# ================================
# Voice Call Integration Endpoints
# ================================

@bp_module5.route("/api/module5/negotiations/<thread_id>/prepare-voice-call", methods=["GET"])
def prepare_voice_call(thread_id: str):
    """
    Prepare data for a voice call with the supplier.
    Returns negotiation context needed for the voice call UI.
    """
    try:
        thread = load_thread(thread_id)
        if not thread:
            return jsonify({"error": "Thread not found"}), 404
        
        # Calculate price boundaries for negotiation
        initial_price = None
        if thread.initial_price_estimate:
            try:
                # Parse price estimate (e.g., "5000 EUR" -> 5000)
                price_str = str(thread.initial_price_estimate).replace(",", "").replace(" ", "")
                import re
                price_match = re.search(r'(\d+(?:\.\d+)?)', price_str)
                if price_match:
                    initial_price = float(price_match.group(1))
            except:
                pass
        
        # Use current supplier offer price if available
        if thread.current_supplier_offer and thread.current_supplier_offer.get("price"):
            initial_price = thread.current_supplier_offer.get("price")
        
        # Default fallback
        if not initial_price:
            initial_price = 5000  # Default for demo
        
        negotiation_data = {
            "machine_input": {
                "id": thread.thread_id[:8].upper(),
                "name": thread.machine_name,
                "quantity": thread.quantity or 1
            },
            "suppliers": [{
                "supplier_name": thread.supplier_name,
                "website": thread.supplier_website or "",
                "region": thread.supplier_region or "Unknown",
                "price_estimate": initial_price,
                "email": thread.supplier_email,
                "phone_number": thread.supplier_phone or "",
                "relevance_score": 5.0
            }],
            "buyer_requirements": thread.buyer_requirements,
            "thread_id": thread.thread_id,
            "round_number": thread.round_number,
            "current_offer": thread.current_supplier_offer,
        }
        
        return jsonify({
            "status": "success",
            "negotiation_data": negotiation_data,
            "thread": thread.to_dict(),
        })
        
    except Exception as e:
        logger.exception(f"Error preparing voice call for {thread_id}")
        return jsonify({"error": str(e), "status": "error"}), 500


@bp_module5.route("/api/module5/get-negotiation-data/<session_id>", methods=["GET"])
def get_negotiation_data(session_id: str):
    """
    Get negotiation data for a voice call session.
    This endpoint is called by the voice call page.
    """
    try:
        thread = load_thread(session_id)
        if not thread:
            return jsonify({"error": "Session not found"}), 404
        
        # Calculate price boundaries
        initial_price = None
        if thread.initial_price_estimate:
            try:
                price_str = str(thread.initial_price_estimate).replace(",", "").replace(" ", "")
                import re
                price_match = re.search(r'(\d+(?:\.\d+)?)', price_str)
                if price_match:
                    initial_price = float(price_match.group(1))
            except:
                pass
        
        if thread.current_supplier_offer and thread.current_supplier_offer.get("price"):
            initial_price = thread.current_supplier_offer.get("price")
        
        if not initial_price:
            initial_price = 5000
        
        negotiation_data = {
            "machine_input": {
                "id": thread.thread_id[:8].upper(),
                "name": thread.machine_name,
                "quantity": thread.quantity or 1
            },
            "suppliers": [{
                "supplier_name": thread.supplier_name,
                "website": thread.supplier_website or "",
                "region": thread.supplier_region or "Unknown",
                "price_estimate": initial_price,
                "email": thread.supplier_email,
                "phone_number": thread.supplier_phone or "",
                "relevance_score": 5.0
            }]
        }
        
        return jsonify({
            "status": "success",
            "negotiation_data": negotiation_data,
        })
        
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500


@bp_module5.route("/api/module5/save-negotiation", methods=["POST"])
def save_voice_negotiation():
    """
    Save voice negotiation result back to the thread.
    Called by the voice call page when a call ends.
    Also sends a confirmation email to the supplier.
    """
    try:
        if not request.is_json:
            return jsonify({"error": "Expected JSON input"}), 400
        
        payload = request.get_json() or {}
        
        # Extract thread ID from machine_id (first 8 chars) or look up by supplier
        machine_id = payload.get("machine_id", "")
        supplier_email = payload.get("supplier_email", "")
        send_confirmation_email = payload.get("send_confirmation_email", True)
        
        # Try to find the thread
        thread = None
        threads = list_threads()
        
        for t in threads:
            if t.thread_id.upper().startswith(machine_id.upper()):
                thread = t
                break
            if supplier_email and t.supplier_email.lower() == supplier_email.lower():
                thread = t
                break
        
        if not thread:
            # Save as standalone result if no thread found
            output_dir = OUTPUT_DIRS.get("module5")
            if output_dir:
                filename = f"voice_negotiation_{int(datetime.now(timezone.utc).timestamp())}.json"
                write_json(output_dir / filename, payload)
            
            return jsonify({
                "status": "success",
                "message": "Saved as standalone result (no thread found)",
                "saved_to": str(output_dir / filename) if output_dir else None,
            })
        
        # Update thread with voice call result
        voice_result = {
            "final_status": payload.get("final_status"),
            "final_price_per_unit": payload.get("final_price_per_unit"),
            "discount_achieved": payload.get("discount_achieved"),
            "total_value": payload.get("total_value"),
            "negotiation_rounds": payload.get("negotiation_rounds"),
            "rounds_history": payload.get("rounds_history"),
            "transcript": payload.get("transcript"),
            "timestamp": payload.get("timestamp", datetime.utcnow().isoformat()),
        }
        
        # Store voice result in thread
        thread.voice_call_result = voice_result
        thread.voice_call_transcript = payload.get("transcript", [])
        
        # Update status if deal was closed
        if payload.get("final_status") == "ACCEPTED":
            update_thread_status(thread, NegotiationStatus.ACCEPTED)
            thread.best_offer = {
                "price": payload.get("final_price_per_unit"),
                "currency": "DZD",
                "source": "voice_negotiation",
                "_score": 100,
            }
        
        save_thread(thread)
        
        # Send confirmation email to supplier
        email_result = None
        if send_confirmation_email and payload.get("final_status") == "ACCEPTED":
            try:
                # Apply test email override if configured (from payload or env)
                test_recipient = get_test_recipient_email(payload)
                recipient_email = test_recipient if test_recipient else thread.supplier_email
                
                # Generate email content
                subject = generate_voice_call_confirmation_subject(thread)
                body = generate_voice_call_confirmation_email(thread, voice_result)
                
                email_config = _get_email_config()
                
                send_payload = {
                    **email_config,
                    "to": [recipient_email],
                    "subject": subject,
                    "text": body,
                    "from_address": thread.buyer_email,
                    "reply_to": thread.buyer_email,
                }
                
                result = send_email(send_payload)
                
                # Record email in thread
                add_email_to_thread(
                    thread=thread,
                    message_id=result.get("message_id", ""),
                    direction="outbound",
                    subject=subject,
                    body_text=body,
                    from_address=thread.buyer_email,
                    to_address=recipient_email,
                )
                save_thread(thread)
                
                email_result = {
                    "status": "sent",
                    "message_id": result.get("message_id"),
                    "recipient": recipient_email,
                }
                logger.info(f"Sent voice call confirmation email to {recipient_email}")
                
            except Exception as e:
                logger.error(f"Failed to send confirmation email: {e}")
                email_result = {
                    "status": "failed",
                    "error": str(e),
                }
        
        return jsonify({
            "status": "success",
            "message": "Voice negotiation result saved to thread",
            "thread_id": thread.thread_id,
            "thread": thread.to_dict(),
            "confirmation_email": email_result,
        })
        
    except Exception as e:
        logger.exception("Error saving voice negotiation")
        return jsonify({"error": str(e), "status": "error"}), 500


# ============================================================
# NEW: Voice-First Negotiation Endpoints (Supabase-backed)
# ============================================================

# Frontend base URL for negotiation links
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000")


@bp_module5.route("/api/module5/v2/negotiations/create", methods=["POST"])
def create_negotiation_v2():
    """
    Create a new negotiation record in Supabase.
    Called after supplier confirms product info, before sending negotiation link.
    
    Required payload:
    {
        "project_id": "uuid",
        "supplier_name": "Supplier Corp",
        "machine_name": "CNC Mill X500",
        "quantity": 2,
        "supplier_email": "sales@supplier.com",
        "initial_price_estimate": 5000.00,
        ...
    }
    """
    try:
        if not request.is_json:
            return jsonify({"error": "Expected JSON input"}), 400
        
        payload = request.get_json() or {}
        
        project_id = payload.get("project_id")
        if not project_id:
            return jsonify({"error": "project_id is required"}), 400
        
        supplier_name = payload.get("supplier_name")
        machine_name = payload.get("machine_name")
        if not supplier_name or not machine_name:
            return jsonify({"error": "supplier_name and machine_name are required"}), 400
        
        client = supabase_utils.get_supabase()
        if not client:
            return jsonify({"error": "Supabase not configured"}), 500
        
        negotiation = supabase_utils.create_negotiation(
            client=client,
            project_id=project_id,
            supplier_name=supplier_name,
            machine_name=machine_name,
            quantity=payload.get("quantity", 1),
            supplier_email=payload.get("supplier_email"),
            supplier_phone=payload.get("supplier_phone"),
            supplier_website=payload.get("supplier_website"),
            supplier_region=payload.get("supplier_region"),
            machine_type=payload.get("machine_type"),
            initial_price_estimate=payload.get("initial_price_estimate"),
            currency=payload.get("currency", "DZD"),
            buyer_company=payload.get("buyer_company", "RIBIF Algeria"),
            buyer_email=payload.get("buyer_email"),
            buyer_contact_name=payload.get("buyer_contact_name"),
        )
        
        if not negotiation:
            return jsonify({"error": "Failed to create negotiation"}), 500
        
        return jsonify({
            "status": "success",
            "negotiation": negotiation,
        })
        
    except Exception as e:
        logger.exception("Error creating negotiation")
        return jsonify({"error": str(e), "status": "error"}), 500


@bp_module5.route("/api/module5/v2/negotiations/<negotiation_id>/send-link", methods=["POST"])
def send_negotiation_link(negotiation_id: str):
    """
    Send voice negotiation link email to the supplier.
    
    Optional payload:
    {
        "buyer_email": "override@company.com"  // Override sender email
    }
    """
    try:
        # Fix operator precedence and handle empty body gracefully
        payload = {}
        if request.is_json:
            try:
                payload = request.get_json(silent=True) or {}
            except Exception:
                payload = {}
        
        client = supabase_utils.get_supabase()
        if not client:
            return jsonify({"error": "Supabase not configured"}), 500
        
        # Get negotiation
        negotiation = supabase_utils.get_negotiation_by_id(client, negotiation_id)
        if not negotiation:
            return jsonify({"error": "Negotiation not found"}), 404
        
        supplier_email = negotiation.get("supplier_email")
        if not supplier_email:
            return jsonify({"error": "Supplier email not set"}), 400
        
        # Apply test override if configured (from payload or env)
        test_recipient = get_test_recipient_email(payload)
        recipient_email = test_recipient if test_recipient else supplier_email
        
        # Build negotiation link
        link_token = negotiation.get("link_token")
        negotiation_link = f"{FRONTEND_BASE_URL}/voice-call?token={link_token}"
        
        # Generate email
        subject = generate_negotiation_link_subject(negotiation.get("machine_name"))
        body = generate_negotiation_link_email(
            supplier_name=negotiation.get("supplier_name"),
            machine_name=negotiation.get("machine_name"),
            quantity=negotiation.get("quantity", 1),
            negotiation_link=negotiation_link,
            buyer_company=negotiation.get("buyer_company", "RIBIF Algeria"),
            buyer_contact_name=negotiation.get("buyer_contact_name", ""),
            initial_price_estimate=negotiation.get("initial_price_estimate"),
        )
        
        # Send email
        email_config = _get_email_config(payload)
        buyer_email = payload.get("buyer_email") or negotiation.get("buyer_email") or NEGOTIATION_SMTP_USERNAME
        
        send_payload = {
            **email_config,
            "to": [recipient_email],
            "subject": subject,
            "text": body,
            "from_address": buyer_email,
            "reply_to": buyer_email,
        }
        
        result = send_email(send_payload)
        
        # Update negotiation status
        supabase_utils.mark_negotiation_link_sent(client, negotiation_id)
        
        # Record email
        email_record = {
            "type": "negotiation_link",
            "message_id": result.get("message_id"),
            "recipient": recipient_email,
            "subject": subject,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }
        supabase_utils.add_email_to_negotiation(client, negotiation_id, email_record)
        
        logger.info(f"Sent negotiation link to {recipient_email} for negotiation {negotiation_id}")
        
        return jsonify({
            "status": "success",
            "message": "Negotiation link sent",
            "negotiation_id": negotiation_id,
            "recipient": recipient_email,
            "link": negotiation_link,
            "message_id": result.get("message_id"),
        })
        
    except Exception as e:
        logger.exception("Error sending negotiation link")
        return jsonify({"error": str(e), "status": "error"}), 500


@bp_module5.route("/api/module5/v2/negotiations/by-token/<link_token>", methods=["GET"])
def get_negotiation_by_token(link_token: str):
    """
    Get negotiation data by link token (for supplier access via voice-call page).
    This is called by the voice-call page when a supplier clicks the negotiation link.
    """
    try:
        client = supabase_utils.get_supabase()
        if not client:
            return jsonify({"error": "Supabase not configured"}), 500
        
        negotiation = supabase_utils.get_negotiation_by_token(client, link_token)
        if not negotiation:
            return jsonify({"error": "Invalid or expired link"}), 404
        
        # Check if link is expired
        expires_at = negotiation.get("link_expires_at")
        if expires_at:
            from datetime import datetime
            try:
                exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if datetime.now(timezone.utc) > exp_dt:
                    return jsonify({"error": "This negotiation link has expired"}), 410
            except:
                pass
        
        # Check if already completed
        if negotiation.get("status") in ["completed", "accepted", "rejected"]:
            return jsonify({
                "error": "This negotiation has already been completed",
                "status": negotiation.get("status"),
            }), 410
        
        # Update status to in_progress if not already
        if negotiation.get("status") == "link_sent":
            supabase_utils.update_negotiation_status(client, negotiation["id"], "in_progress")
        
        # Return negotiation data formatted for voice-call page
        negotiation_data = {
            "machine_input": {
                "id": negotiation.get("id"),
                "name": negotiation.get("machine_name"),
                "quantity": negotiation.get("quantity", 1),
            },
            "suppliers": [{
                "id": negotiation.get("id"),
                "supplier_name": negotiation.get("supplier_name"),
                "name": negotiation.get("supplier_name"),
                "website": negotiation.get("supplier_website") or "",
                "region": negotiation.get("supplier_region") or "",
                "price_estimate": negotiation.get("initial_price_estimate") or 5000,
                "email": negotiation.get("supplier_email") or "",
                "phone_number": negotiation.get("supplier_phone") or "",
                "relevance_score": 100,
            }],
            "negotiation_id": negotiation.get("id"),
            "project_id": negotiation.get("project_id"),
        }
        
        return jsonify({
            "status": "success",
            "negotiation_data": negotiation_data,
        })
        
    except Exception as e:
        logger.exception("Error getting negotiation by token")
        return jsonify({"error": str(e), "status": "error"}), 500


@bp_module5.route("/api/module5/v2/negotiations/<negotiation_id>/save-result", methods=["POST"])
def save_negotiation_result_v2(negotiation_id: str):
    """
    Save voice negotiation result to Supabase.
    Called by the voice-call page when negotiation completes.
    Also sends confirmation email to supplier.
    
    Payload:
    {
        "final_status": "accepted",  // accepted, rejected, no_deal
        "final_price": 4500.00,
        "discount_achieved": 10.0,
        "total_value": 9000.00,
        "negotiation_rounds": 3,
        "transcript": [...],
        "rounds_history": [...]
    }
    """
    try:
        if not request.is_json:
            return jsonify({"error": "Expected JSON input"}), 400
        
        payload = request.get_json() or {}
        
        client = supabase_utils.get_supabase()
        if not client:
            return jsonify({"error": "Supabase not configured"}), 500
        
        # Get negotiation
        negotiation = supabase_utils.get_negotiation_by_id(client, negotiation_id)
        if not negotiation:
            return jsonify({"error": "Negotiation not found"}), 404
        
        # Map status
        final_status = payload.get("final_status", "completed")
        if final_status == "ACCEPTED":
            final_status = "accepted"
        elif final_status == "no_deal":
            final_status = "rejected"
        
        # Save result
        result = supabase_utils.save_voice_call_result(
            client=client,
            negotiation_id=negotiation_id,
            final_price=payload.get("final_price") or payload.get("final_price_per_unit"),
            discount_achieved=payload.get("discount_achieved", 0),
            total_value=payload.get("total_value", 0),
            negotiation_rounds=payload.get("negotiation_rounds", 1),
            transcript=payload.get("transcript", []),
            rounds_history=payload.get("rounds_history", []),
            status=final_status,
        )
        
        if not result:
            return jsonify({"error": "Failed to save result"}), 500
        
        # Update project's module5_data
        project_id = negotiation.get("project_id")
        if project_id:
            summary = supabase_utils.get_negotiations_summary(client, project_id)
            supabase_utils.update_project_module5_data(client, project_id, {
                "summary": summary,
                "last_updated": datetime.now(timezone.utc).isoformat(),
            })
        
        # Send confirmation email if accepted or completed (always send after voice call)
        email_result = None
        send_confirmation = payload.get("send_confirmation_email", True)
        if send_confirmation and final_status in ("accepted", "completed"):
            try:
                supplier_email = negotiation.get("supplier_email")
                if supplier_email:
                    # Apply test email override if configured (from payload or env)
                    test_recipient = get_test_recipient_email(payload)
                    recipient_email = test_recipient if test_recipient else supplier_email
                    
                    # Create a minimal thread-like object for the email generator
                    class MinimalThread:
                        pass
                    thread = MinimalThread()
                    thread.supplier_name = negotiation.get("supplier_name")
                    thread.machine_name = negotiation.get("machine_name")
                    thread.quantity = negotiation.get("quantity", 1)
                    thread.buyer_company = negotiation.get("buyer_company", "RIBIF Algeria")
                    thread.buyer_contact_name = negotiation.get("buyer_contact_name", "")
                    thread.buyer_email = negotiation.get("buyer_email", "")
                    
                    voice_result = {
                        "final_status": final_status,
                        "final_price_per_unit": payload.get("final_price") or payload.get("final_price_per_unit"),
                        "discount_achieved": payload.get("discount_achieved", 0),
                        "total_value": payload.get("total_value", 0),
                        "negotiation_rounds": payload.get("negotiation_rounds", 1),
                    }
                    
                    subject = generate_voice_call_confirmation_subject(thread)
                    body = generate_voice_call_confirmation_email(thread, voice_result)
                    
                    email_config = _get_email_config()
                    buyer_email = negotiation.get("buyer_email") or NEGOTIATION_SMTP_USERNAME
                    
                    send_payload = {
                        **email_config,
                        "to": [recipient_email],
                        "subject": subject,
                        "text": body,
                        "from_address": buyer_email,
                        "reply_to": buyer_email,
                    }
                    
                    email_send_result = send_email(send_payload)
                    
                    # Record email
                    email_record = {
                        "type": "confirmation",
                        "message_id": email_send_result.get("message_id"),
                        "recipient": recipient_email,
                        "subject": subject,
                        "sent_at": datetime.now(timezone.utc).isoformat(),
                    }
                    supabase_utils.add_email_to_negotiation(client, negotiation_id, email_record)
                    
                    email_result = {
                        "status": "sent",
                        "message_id": email_send_result.get("message_id"),
                        "recipient": recipient_email,
                    }
                    logger.info(f"Sent confirmation email to {recipient_email}")
                    
            except Exception as e:
                logger.error(f"Failed to send confirmation email: {e}")
                email_result = {"status": "failed", "error": str(e)}
        
        return jsonify({
            "status": "success",
            "message": "Negotiation result saved",
            "negotiation_id": negotiation_id,
            "negotiation": result,
            "confirmation_email": email_result,
        })
        
    except Exception as e:
        logger.exception("Error saving negotiation result")
        return jsonify({"error": str(e), "status": "error"}), 500


@bp_module5.route("/api/module5/v2/negotiations/project/<project_id>", methods=["GET"])
def get_project_negotiations(project_id: str):
    """
    Get all negotiations for a project.
    """
    try:
        client = supabase_utils.get_supabase()
        if not client:
            return jsonify({"error": "Supabase not configured"}), 500
        
        negotiations = supabase_utils.get_negotiations_by_project(client, project_id)
        summary = supabase_utils.get_negotiations_summary(client, project_id)
        
        return jsonify({
            "status": "success",
            "negotiations": negotiations,
            "summary": summary,
        })
        
    except Exception as e:
        logger.exception("Error getting project negotiations")
        return jsonify({"error": str(e), "status": "error"}), 500


@bp_module5.route("/api/module5/v2/negotiations/<negotiation_id>", methods=["GET"])
def get_negotiation_v2(negotiation_id: str):
    """
    Get a single negotiation by ID.
    """
    try:
        client = supabase_utils.get_supabase()
        if not client:
            return jsonify({"error": "Supabase not configured"}), 500
        
        negotiation = supabase_utils.get_negotiation_by_id(client, negotiation_id)
        if not negotiation:
            return jsonify({"error": "Negotiation not found"}), 404
        
        return jsonify({
            "status": "success",
            "negotiation": negotiation,
        })
        
    except Exception as e:
        logger.exception("Error getting negotiation")
        return jsonify({"error": str(e), "status": "error"}), 500


@bp_module5.route("/api/module5/v2/negotiations/bulk-create", methods=["POST"])
def bulk_create_negotiations():
    """
    Create negotiations for multiple suppliers at once (from module 4 data).
    
    Payload:
    {
        "project_id": "uuid",
        "machine_name": "CNC Mill",
        "machine_type": "milling",
        "quantity": 2,
        "suppliers": [
            {
                "supplier_name": "Supplier A",
                "email_address": "a@supplier.com",
                "price_estimate": 5000,
                ...
            }
        ],
        "buyer_email": "buyer@company.com",
        "buyer_company": "RIBIF Algeria",
        "buyer_contact_name": "Ibrahim"
    }
    """
    try:
        if not request.is_json:
            return jsonify({"error": "Expected JSON input"}), 400
        
        payload = request.get_json() or {}
        
        project_id = payload.get("project_id")
        if not project_id:
            return jsonify({"error": "project_id is required"}), 400
        
        suppliers = payload.get("suppliers", [])
        if not suppliers:
            return jsonify({"error": "No suppliers provided"}), 400
        
        client = supabase_utils.get_supabase()
        if not client:
            return jsonify({"error": "Supabase not configured"}), 500
        
        machine_name = payload.get("machine_name", payload.get("machine", {}).get("name", "Equipment"))
        machine_type = payload.get("machine_type", payload.get("machine", {}).get("type"))
        raw_quantity = payload.get("quantity", payload.get("machine", {}).get("quantity", 1))
        # Handle quantity that may be an object like {"source":"user_input","value":1} or just an int
        if isinstance(raw_quantity, dict):
            quantity = raw_quantity.get("value", 1)
        else:
            quantity = raw_quantity
        # Ensure it's an integer
        try:
            quantity = int(quantity) if quantity else 1
        except (ValueError, TypeError):
            quantity = 1
        buyer_email = payload.get("buyer_email")
        buyer_company = payload.get("buyer_company", "RIBIF Algeria")
        buyer_contact_name = payload.get("buyer_contact_name", "")
        
        # Get test recipient email from payload or env
        test_recipient = get_test_recipient_email(payload)
        
        created = []
        failed = []
        
        for supplier in suppliers:
            try:
                # Parse price estimate
                price_estimate = supplier.get("price_estimate")
                if isinstance(price_estimate, str):
                    import re
                    match = re.search(r'[\d,]+(?:\.\d+)?', price_estimate.replace(",", ""))
                    price_estimate = float(match.group()) if match else None
                
                # Extract supplier email - try multiple field names
                supplier_email = supplier.get("email_address") or supplier.get("email") or supplier.get("contact_email")
                supplier_name = supplier.get("supplier_name") or supplier.get("name") or "Unknown"
                
                # If no supplier email and test_recipient is configured, use it as placeholder
                # This allows the negotiation flow to proceed in test/demo mode
                if not supplier_email and test_recipient:
                    supplier_email = test_recipient
                    logger.info(f"Using test recipient email for supplier: {supplier_name}")
                
                logger.info(f"Creating negotiation for supplier: {supplier_name}, email: {supplier_email}")
                
                negotiation = supabase_utils.create_negotiation(
                    client=client,
                    project_id=project_id,
                    supplier_name=supplier_name,
                    machine_name=machine_name,
                    quantity=quantity,
                    supplier_email=supplier_email,
                    supplier_phone=supplier.get("phone_number", supplier.get("phone")),
                    supplier_website=supplier.get("website"),
                    supplier_region=supplier.get("region"),
                    machine_type=machine_type,
                    initial_price_estimate=price_estimate,
                    currency=supplier.get("currency", "DZD"),
                    buyer_company=buyer_company,
                    buyer_email=buyer_email,
                    buyer_contact_name=buyer_contact_name,
                )
                
                if negotiation:
                    created.append(negotiation)
                else:
                    failed.append({
                        "supplier": supplier.get("supplier_name"),
                        "error": "Failed to create",
                    })
                    
            except Exception as e:
                failed.append({
                    "supplier": supplier.get("supplier_name"),
                    "error": str(e),
                })
        
        return jsonify({
            "status": "success",
            "created_count": len(created),
            "failed_count": len(failed),
            "negotiations": created,
            "failed": failed,
        })
        
    except Exception as e:
        logger.exception("Error bulk creating negotiations")
        return jsonify({"error": str(e), "status": "error"}), 500


@bp_module5.route("/api/module5/v2/negotiations/project/<project_id>/send-all-links", methods=["POST"])
def send_all_negotiation_links(project_id: str):
    """
    Send negotiation link emails to all pending suppliers for a project.
    Only sends to negotiations with status 'pending' and valid supplier email.
    Accepts test_recipient_email in payload to override supplier emails.
    """
    try:
        logger.info(f"send_all_negotiation_links called for project {project_id}")
        # Fix operator precedence and handle empty body gracefully
        payload = {}
        if request.is_json:
            try:
                payload = request.get_json(silent=True) or {}
            except Exception:
                payload = {}
        
        client = supabase_utils.get_supabase()
        if not client:
            logger.error("Supabase not configured")
            return jsonify({"error": "Supabase not configured"}), 500
        
        # Get test recipient email from payload or env
        test_recipient = get_test_recipient_email(payload)
        
        # Get all negotiations for project
        negotiations = supabase_utils.get_negotiations_by_project(client, project_id)
        logger.info(f"Found {len(negotiations)} total negotiations for project")
        
        # Filter to only pending ones
        # If test_recipient is set, include negotiations without emails (test mode)
        # Otherwise, only include negotiations with supplier emails
        if test_recipient:
            pending = [n for n in negotiations if n.get("status") == "pending"]
            logger.info(f"TEST MODE: Found {len(pending)} pending negotiations (will use test email: {test_recipient})")
        else:
            pending = [n for n in negotiations if n.get("status") == "pending" and n.get("supplier_email")]
            logger.info(f"Found {len(pending)} pending negotiations with supplier emails")
        
        if not pending:
            return jsonify({
                "status": "success",
                "message": "No pending negotiations with supplier emails found",
                "sent_count": 0,
                "failed_count": 0,
            })
        
        sent = []
        failed = []
        
        for negotiation in pending:
            try:
                supplier_email = negotiation.get("supplier_email")
                # Use test_recipient if configured (test mode), otherwise use supplier email
                recipient_email = test_recipient if test_recipient else supplier_email
                
                # Skip if no recipient email available
                if not recipient_email:
                    logger.warning(f"Skipping negotiation {negotiation.get('id')} - no recipient email")
                    failed.append({
                        "negotiation_id": negotiation.get("id"),
                        "supplier_name": negotiation.get("supplier_name"),
                        "error": "No recipient email available",
                    })
                    continue
                
                # Build negotiation link
                link_token = negotiation.get("link_token")
                negotiation_link = f"{FRONTEND_BASE_URL}/voice-call?token={link_token}"
                
                # Generate email
                subject = generate_negotiation_link_subject(negotiation.get("machine_name"))
                body = generate_negotiation_link_email(
                    supplier_name=negotiation.get("supplier_name"),
                    machine_name=negotiation.get("machine_name"),
                    quantity=negotiation.get("quantity", 1),
                    negotiation_link=negotiation_link,
                    buyer_company=negotiation.get("buyer_company", "RIBIF Algeria"),
                    buyer_contact_name=negotiation.get("buyer_contact_name", ""),
                    initial_price_estimate=negotiation.get("initial_price_estimate"),
                )
                
                # Send email
                email_config = _get_email_config(payload)
                buyer_email = payload.get("buyer_email") or negotiation.get("buyer_email") or NEGOTIATION_SMTP_USERNAME
                
                logger.info(f"Sending email: from={buyer_email}, to={recipient_email}, subject={subject}")
                
                send_payload = {
                    **email_config,
                    "to": [recipient_email],
                    "subject": subject,
                    "text": body,
                    "from_address": buyer_email,
                    "reply_to": buyer_email,
                }
                
                result = send_email(send_payload)
                logger.info(f"Email sent result: {result}")
                
                # Update negotiation status
                supabase_utils.mark_negotiation_link_sent(client, negotiation.get("id"))
                
                # Record email
                email_record = {
                    "type": "negotiation_link",
                    "message_id": result.get("message_id"),
                    "recipient": recipient_email,
                    "subject": subject,
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                }
                supabase_utils.add_email_to_negotiation(client, negotiation.get("id"), email_record)
                
                sent.append({
                    "negotiation_id": negotiation.get("id"),
                    "supplier_name": negotiation.get("supplier_name"),
                    "recipient": recipient_email,
                })
                
                logger.info(f"Sent negotiation link to {recipient_email} for supplier {negotiation.get('supplier_name')}")
                
            except Exception as e:
                failed.append({
                    "negotiation_id": negotiation.get("id"),
                    "supplier_name": negotiation.get("supplier_name"),
                    "error": str(e),
                })
                logger.error(f"Failed to send link to {negotiation.get('supplier_name')}: {e}")
        
        return jsonify({
            "status": "success",
            "sent_count": len(sent),
            "failed_count": len(failed),
            "sent": sent,
            "failed": failed,
        })
        
    except Exception as e:
        logger.exception("Error sending all negotiation links")
        return jsonify({"error": str(e), "status": "error"}), 500
