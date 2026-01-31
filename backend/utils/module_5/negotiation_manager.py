"""
Module 5: AI Negotiation Manager
================================
Orchestrates email-based negotiations with suppliers:
- Tracks negotiation threads per supplier
- Sends initial RFQ emails
- Monitors inbox for replies
- Parses supplier responses
- Generates AI-powered counter-offers
"""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum

from dotenv import load_dotenv

from utils.logger import get_logger, task

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

logger = get_logger(__name__)

# ================================
# Config
# ================================

NEGOTIATIONS_CACHE_DIR = Path(os.getenv(
    "NEGOTIATIONS_CACHE_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "cache", "negotiations")
))
NEGOTIATIONS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

MAX_NEGOTIATION_ROUNDS = int(os.getenv("MAX_NEGOTIATION_ROUNDS", "5"))
AUTO_ACCEPT_MARGIN = float(os.getenv("NEGOTIATION_AUTO_ACCEPT_MARGIN", "0.05"))  # Accept if within 5% of target


class NegotiationStatus(str, Enum):
    DRAFT = "draft"                    # Thread created but no email sent
    INITIAL_SENT = "initial_sent"      # RFQ email sent, waiting for reply
    PENDING_REPLY = "pending_reply"    # Counter sent, waiting for supplier reply
    NEGOTIATING = "negotiating"        # Reply received, ready for next round
    ACCEPTED = "accepted"              # Deal accepted
    REJECTED = "rejected"              # Deal rejected by buyer or max rounds
    CLOSED = "closed"                  # Manually closed


@dataclass
class EmailRecord:
    """Tracks a single email in the thread"""
    message_id: str
    direction: str  # "outbound" or "inbound"
    subject: str
    body_text: str
    timestamp: str
    from_address: str
    to_address: str
    parsed_offer: Optional[Dict[str, Any]] = None


@dataclass
class NegotiationThread:
    """Tracks negotiation state with a single supplier"""
    # Required fields (no defaults) - must come first
    thread_id: str
    supplier_name: str
    supplier_email: str
    machine_name: str
    
    # Optional fields with defaults
    project_id: Optional[str] = None
    
    # Supplier info (from module 4)
    supplier_website: Optional[str] = None
    supplier_phone: Optional[str] = None
    supplier_region: Optional[str] = None
    
    # Product info
    machine_type: Optional[str] = None
    quantity: int = 1
    initial_price_estimate: Optional[str] = None
    
    # Buyer requirements
    buyer_requirements: Dict[str, Any] = field(default_factory=dict)
    buyer_company: str = "RIBIF Algeria"
    buyer_email: str = ""
    buyer_contact_name: str = ""
    
    # Negotiation state
    status: str = NegotiationStatus.DRAFT.value
    round_number: int = 0
    max_rounds: int = MAX_NEGOTIATION_ROUNDS
    
    # Email tracking
    emails: List[Dict[str, Any]] = field(default_factory=list)
    last_outbound_message_id: Optional[str] = None
    last_inbound_message_id: Optional[str] = None
    
    # Offer tracking
    current_supplier_offer: Dict[str, Any] = field(default_factory=dict)
    last_counter_offer: Dict[str, Any] = field(default_factory=dict)
    best_offer: Dict[str, Any] = field(default_factory=dict)
    
    # Evaluation history
    evaluations: List[Dict[str, Any]] = field(default_factory=list)
    
    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_email_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NegotiationThread":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


def _thread_path(thread_id: str) -> Path:
    return NEGOTIATIONS_CACHE_DIR / f"{thread_id}.json"


def _project_index_path(project_id: str) -> Path:
    return NEGOTIATIONS_CACHE_DIR / f"project_{project_id}_index.json"


def save_thread(thread: NegotiationThread) -> None:
    """Persist thread to disk"""
    thread.updated_at = datetime.utcnow().isoformat()
    path = _thread_path(thread.thread_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(thread.to_dict(), f, ensure_ascii=False, indent=2)
    
    # Update project index
    if thread.project_id:
        _update_project_index(thread.project_id, thread.thread_id)


def load_thread(thread_id: str) -> Optional[NegotiationThread]:
    """Load thread from disk"""
    path = _thread_path(thread_id)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return NegotiationThread.from_dict(data)
    except Exception as e:
        logger.error(f"Failed to load thread {thread_id}: {e}")
        return None


def list_threads(project_id: Optional[str] = None, status: Optional[str] = None) -> List[NegotiationThread]:
    """List all threads, optionally filtered"""
    threads = []
    
    if project_id:
        # Use project index for efficiency
        index_path = _project_index_path(project_id)
        if index_path.exists():
            try:
                with open(index_path, "r", encoding="utf-8") as f:
                    thread_ids = json.load(f)
                for tid in thread_ids:
                    t = load_thread(tid)
                    if t and (status is None or t.status == status):
                        threads.append(t)
            except Exception:
                pass
    else:
        # Scan all thread files
        for p in NEGOTIATIONS_CACHE_DIR.glob("*.json"):
            if p.name.startswith("project_"):
                continue
            t = load_thread(p.stem)
            if t and (status is None or t.status == status):
                threads.append(t)
    
    return sorted(threads, key=lambda x: x.updated_at, reverse=True)


def _update_project_index(project_id: str, thread_id: str) -> None:
    """Add thread to project index"""
    index_path = _project_index_path(project_id)
    thread_ids = []
    if index_path.exists():
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                thread_ids = json.load(f)
        except Exception:
            thread_ids = []
    
    if thread_id not in thread_ids:
        thread_ids.append(thread_id)
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(thread_ids, f)


def create_thread_from_supplier(
    supplier: Dict[str, Any],
    machine: Dict[str, Any],
    buyer_requirements: Dict[str, Any],
    buyer_email: str,
    buyer_company: str = "RIBIF Algeria",
    buyer_contact_name: str = "",
    project_id: Optional[str] = None,
) -> NegotiationThread:
    """Create a new negotiation thread from module 4 supplier data"""
    
    thread = NegotiationThread(
        thread_id=str(uuid.uuid4()),
        project_id=project_id,
        supplier_name=supplier.get("supplier_name", "Unknown Supplier"),
        supplier_email=supplier.get("email_address", ""),
        supplier_website=supplier.get("website"),
        supplier_phone=supplier.get("phone_number"),
        supplier_region=supplier.get("region"),
        machine_name=machine.get("nom_machine", "Equipment"),
        machine_type=machine.get("type"),
        quantity=machine.get("quantite_necessaire", 1),
        initial_price_estimate=supplier.get("price_estimate"),
        buyer_requirements=buyer_requirements,
        buyer_company=buyer_company,
        buyer_email=buyer_email,
        buyer_contact_name=buyer_contact_name,
    )
    
    save_thread(thread)
    return thread


def add_email_to_thread(
    thread: NegotiationThread,
    message_id: str,
    direction: str,
    subject: str,
    body_text: str,
    from_address: str,
    to_address: str,
    parsed_offer: Optional[Dict[str, Any]] = None,
) -> None:
    """Add an email record to thread"""
    email = {
        "message_id": message_id,
        "direction": direction,
        "subject": subject,
        "body_text": body_text,
        "timestamp": datetime.utcnow().isoformat(),
        "from_address": from_address,
        "to_address": to_address,
        "parsed_offer": parsed_offer,
    }
    thread.emails.append(email)
    thread.last_email_at = email["timestamp"]
    
    if direction == "outbound":
        thread.last_outbound_message_id = message_id
    else:
        thread.last_inbound_message_id = message_id
    
    save_thread(thread)


def update_thread_status(thread: NegotiationThread, status: NegotiationStatus) -> None:
    """Update thread status"""
    thread.status = status.value
    save_thread(thread)


def update_supplier_offer(
    thread: NegotiationThread,
    offer: Dict[str, Any],
    evaluation: Optional[Dict[str, Any]] = None
) -> None:
    """Update current supplier offer and optionally add evaluation"""
    thread.current_supplier_offer = offer
    
    # Track best offer (by overall score)
    if evaluation:
        thread.evaluations.append({
            "round": thread.round_number,
            "timestamp": datetime.utcnow().isoformat(),
            "evaluation": evaluation,
        })
        
        current_score = evaluation.get("scores", {}).get("overall", 0)
        best_score = thread.best_offer.get("_score", 0)
        if current_score > best_score:
            thread.best_offer = {**offer, "_score": current_score}
    
    save_thread(thread)


def update_counter_offer(thread: NegotiationThread, counter: Dict[str, Any]) -> None:
    """Update last counter offer"""
    thread.last_counter_offer = counter
    save_thread(thread)


def increment_round(thread: NegotiationThread) -> None:
    """Increment negotiation round"""
    thread.round_number += 1
    save_thread(thread)


def should_auto_accept(thread: NegotiationThread, evaluation: Dict[str, Any]) -> bool:
    """Check if offer should be auto-accepted"""
    # Accept if recommendation is accept
    if evaluation.get("recommendation") == "accept":
        return True
    
    # Accept if within margin of target price
    offer_price = evaluation.get("price")
    target_price = thread.buyer_requirements.get("target_price")
    
    if offer_price and target_price:
        margin = (offer_price - target_price) / target_price
        if margin <= AUTO_ACCEPT_MARGIN:
            return True
    
    return False


def should_stop_negotiation(thread: NegotiationThread) -> tuple[bool, str]:
    """Check if negotiation should stop"""
    if thread.round_number >= thread.max_rounds:
        return True, "max_rounds_reached"
    
    if thread.status in (NegotiationStatus.ACCEPTED.value, NegotiationStatus.REJECTED.value, NegotiationStatus.CLOSED.value):
        return True, f"status_{thread.status}"
    
    return False, ""


# ================================
# Email Generation
# ================================

def generate_initial_rfq_subject(thread: NegotiationThread) -> str:
    """Generate subject line for initial RFQ"""
    return f"RFQ: {thread.machine_name} x{thread.quantity} - {thread.buyer_company}"


def generate_reply_subject(thread: NegotiationThread) -> str:
    """Generate subject for reply (Re: original subject)"""
    if thread.emails:
        # Find the original subject
        for email in thread.emails:
            if email.get("direction") == "outbound":
                original = email.get("subject", "")
                if not original.startswith("Re:"):
                    return f"Re: {original}"
                return original
    return f"Re: RFQ - {thread.machine_name}"


def generate_initial_rfq_email(thread: NegotiationThread) -> str:
    """Generate initial RFQ email body using LLM"""
    from utils.module_5.core import _llm_generate
    
    system = (
        "You are a professional procurement specialist writing an initial Request for Quote (RFQ) email. "
        "Be professional, clear, and specific about requirements. Write in English."
    )
    
    specs = thread.buyer_requirements.get("specifications", {})
    
    prompt = f"""
Write an initial RFQ email to a supplier.

Context:
- Buyer company: {thread.buyer_company}
- Contact name: {thread.buyer_contact_name}
- Supplier company: {thread.supplier_name}
- Product: {thread.machine_name}
- Type: {thread.machine_type or "Industrial Equipment"}
- Quantity: {thread.quantity}
- Their initial price estimate: {thread.initial_price_estimate or "Not specified"}

Buyer requirements:
- Target price: {thread.buyer_requirements.get("target_price")} {thread.buyer_requirements.get("currency", "EUR")}
- Preferred Incoterms: {thread.buyer_requirements.get("preferred_incoterms", ["DDP", "CIF"])}
- Maximum lead time: {thread.buyer_requirements.get("max_lead_time_days", 90)} days
- Minimum warranty: {thread.buyer_requirements.get("min_warranty_months", 24)} months
- Maximum deposit: {thread.buyer_requirements.get("max_deposit_pct", 30)}%

Additional specifications:
{json.dumps(specs, indent=2) if specs else "Standard specifications"}

Requirements:
1. Introduce the company and project briefly
2. Specify the equipment needed with quantity
3. Request a formal quotation including:
   - Unit price and total price
   - Incoterms (prefer DDP or CIF Algiers)
   - Payment terms
   - Lead time / delivery schedule
   - Warranty terms
   - Technical specifications confirmation
4. Mention destination: Algeria
5. Request validity of 30 days minimum
6. Keep it under 250 words
7. End with a clear call to action
"""
    
    text = _llm_generate(prompt, system, temperature=0.3)
    if text:
        return text.strip()
    
    # Fallback template
    return f"""Dear {thread.supplier_name} Team,

We are {thread.buyer_company}, an industrial company based in Algeria. We are currently sourcing equipment for our production facility and are interested in your {thread.machine_name}.

We would like to request a formal quotation for:
- Product: {thread.machine_name}
- Quantity: {thread.quantity} unit(s)
- Destination: Algeria

Please include in your quote:
1. Unit price and total price
2. Incoterms (we prefer DDP or CIF Algiers Port)
3. Payment terms
4. Lead time / delivery schedule
5. Warranty terms
6. Technical specifications

Our target budget is around {thread.buyer_requirements.get("target_price", "competitive")} {thread.buyer_requirements.get("currency", "EUR")} per unit.

Please provide a quotation valid for at least 30 days.

We look forward to your response.

Best regards,
{thread.buyer_contact_name or "Procurement Team"}
{thread.buyer_company}
{thread.buyer_email}
"""


def generate_negotiation_email(
    thread: NegotiationThread,
    evaluation: Dict[str, Any],
    counter_offer: Dict[str, Any],
) -> str:
    """Generate negotiation/counter-offer email using LLM"""
    from utils.module_5.core import _llm_generate, draft_email
    
    email_context = {
        "buyer_company": thread.buyer_company,
        "supplier_company": thread.supplier_name,
        "product_name": thread.machine_name,
        "quantity": thread.quantity,
        "contact_name": thread.buyer_contact_name,
    }
    
    email_type = "counter"
    if evaluation.get("recommendation") == "accept":
        email_type = "accept"
    elif evaluation.get("recommendation") == "counter_aggressively":
        email_type = "counter_aggressively"
    
    return draft_email(
        email_type=email_type,
        buyer_context=email_context,
        supplier_offer=thread.current_supplier_offer,
        counter_offer=counter_offer,
        evaluation=evaluation,
    )


def generate_acceptance_email(thread: NegotiationThread) -> str:
    """Generate acceptance email"""
    from utils.module_5.core import _llm_generate
    
    system = "You are a procurement specialist writing an acceptance email. Be professional and confirm key terms."
    
    offer = thread.current_supplier_offer
    prompt = f"""
Write an acceptance email for an offer.

Context:
- Buyer: {thread.buyer_company}
- Supplier: {thread.supplier_name}
- Product: {thread.machine_name} x{thread.quantity}

Accepted offer:
{json.dumps(offer, indent=2)}

Requirements:
1. Confirm acceptance of the offer
2. Summarize key terms (price, incoterms, payment, delivery)
3. Request proforma invoice
4. Mention next steps
5. Keep under 150 words
"""
    
    text = _llm_generate(prompt, system, temperature=0.3)
    if text:
        return text.strip()
    
    return f"""Dear {thread.supplier_name} Team,

We are pleased to accept your offer for {thread.machine_name} x{thread.quantity}.

Confirmed terms:
- Price: {offer.get("price")} {offer.get("currency", "EUR")}
- Incoterms: {offer.get("incoterm")}
- Payment: {offer.get("payment_terms")}
- Delivery: {offer.get("lead_time_days")} days

Please send us the proforma invoice so we can proceed with the order.

Best regards,
{thread.buyer_contact_name or "Procurement Team"}
{thread.buyer_company}
"""


# ================================
# Response Parsing
# ================================

def parse_supplier_response(email_body: str, thread: NegotiationThread) -> Dict[str, Any]:
    """Parse supplier email to extract offer details using LLM"""
    from utils.module_5.core import _llm_generate, extract_offer_signals
    
    # First try regex-based extraction
    signals = extract_offer_signals(email_body)
    
    # Then use LLM for more comprehensive parsing
    system = (
        "You are a procurement analyst. Extract offer details from supplier emails. "
        "Return a valid JSON object with the extracted values. Use null for missing fields."
    )
    
    prompt = f"""
Extract the supplier's offer from this email:

---
{email_body[:3000]}
---

Context:
- Product: {thread.machine_name}
- Quantity: {thread.quantity}
- Expected currency: {thread.buyer_requirements.get("currency", "EUR")}

Extract and return ONLY a JSON object with these fields:
{{
    "price": <number or null - unit price>,
    "total_price": <number or null - total if mentioned>,
    "currency": <string - EUR, USD, etc.>,
    "incoterm": <string - EXW, FOB, CIF, DDP, etc. or null>,
    "payment_terms": <string - e.g. "30% deposit, 70% against BL" or null>,
    "lead_time_days": <number or null>,
    "warranty_months": <number or null>,
    "moq": <number or null - minimum order quantity>,
    "validity_days": <number or null - quote validity>,
    "notes": <string - any important conditions or notes>
}}
"""
    
    text = _llm_generate(prompt, system, temperature=0.1)
    
    llm_parsed = {}
    if text:
        # Extract JSON from response
        try:
            # Find JSON in response
            import re
            json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
            if json_match:
                llm_parsed = json.loads(json_match.group())
        except Exception as e:
            logger.warning(f"Failed to parse LLM response: {e}")
    
    # Merge LLM results with regex signals (LLM takes priority for non-null)
    result = {**signals}
    for key, value in llm_parsed.items():
        if value is not None:
            result[key] = value
    
    return result
