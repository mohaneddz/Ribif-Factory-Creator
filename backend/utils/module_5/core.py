from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

from utils.logger import get_logger, log_skip, task


# ================================
# Module 5: AI Negotiation (Text + Voice)
# ================================
# Free-tier friendly design:
# - Text negotiation uses Gemini via vertex_utils.generate_message
# - Voice STT optionally uses Gemini audio (free tier for many accounts)
# - TTS is provided as text-only unless a free TTS provider is configured
#
# This module is intentionally robust to missing services and will fall back
# to templates when LLM or STT are unavailable.

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

logger = get_logger(__name__)

# ================================
# Config
# ================================

DEFAULT_CURRENCY = os.getenv("NEGOTIATION_DEFAULT_CURRENCY", "USD")
DEFAULT_LANGUAGE = os.getenv("NEGOTIATION_DEFAULT_LANGUAGE", "English")
DEFAULT_VOICE_STT_PROVIDER = os.getenv("VOICE_STT_PROVIDER", "none").strip().lower()
DEFAULT_VOICE_TTS_PROVIDER = os.getenv("VOICE_TTS_PROVIDER", "none").strip().lower()
DEFAULT_VOICE_TTS_VOICE = os.getenv("VOICE_TTS_VOICE", "neutral")

DEFAULT_CONCESSION_RATE = float(os.getenv("NEGOTIATION_CONCESSION_RATE", "0.03"))
DEFAULT_ANCHOR_DISCOUNT = float(os.getenv("NEGOTIATION_ANCHOR_DISCOUNT", "0.08"))
DEFAULT_MAX_ROUNDS = int(os.getenv("NEGOTIATION_MAX_ROUNDS", "4"))


# ================================
# Incoterms knowledge
# ================================

INCOTERMS_INFO: Dict[str, Dict[str, Any]] = {
    "EXW": {
        "description": "Ex Works: buyer handles pickup, export, freight, insurance, import, and delivery.",
        "buyer_risk": "High",
        "buyer_score": 0.15,
    },
    "FCA": {
        "description": "Free Carrier: seller delivers to carrier; buyer handles main carriage and import.",
        "buyer_risk": "High",
        "buyer_score": 0.30,
    },
    "FOB": {
        "description": "Free On Board: seller delivers to vessel; buyer handles ocean freight and import.",
        "buyer_risk": "Medium-High",
        "buyer_score": 0.40,
    },
    "CFR": {
        "description": "Cost and Freight: seller pays ocean freight; buyer handles insurance and import.",
        "buyer_risk": "Medium",
        "buyer_score": 0.55,
    },
    "CIF": {
        "description": "Cost, Insurance & Freight: seller pays freight + insurance; buyer handles import.",
        "buyer_risk": "Medium",
        "buyer_score": 0.65,
    },
    "CPT": {
        "description": "Carriage Paid To: seller pays main carriage; buyer handles insurance and import.",
        "buyer_risk": "Medium",
        "buyer_score": 0.60,
    },
    "CIP": {
        "description": "Carriage & Insurance Paid To: seller pays main carriage + insurance; buyer handles import.",
        "buyer_risk": "Medium",
        "buyer_score": 0.70,
    },
    "DAP": {
        "description": "Delivered At Place: seller delivers to destination; buyer handles import duties/taxes.",
        "buyer_risk": "Low-Medium",
        "buyer_score": 0.80,
    },
    "DPU": {
        "description": "Delivered at Place Unloaded: seller delivers and unloads; buyer handles import.",
        "buyer_risk": "Low-Medium",
        "buyer_score": 0.82,
    },
    "DDP": {
        "description": "Delivered Duty Paid: seller covers delivery and import duties/taxes.",
        "buyer_risk": "Low",
        "buyer_score": 0.92,
    },
}

DEFAULT_PREFERRED_INCOTERMS = ["DDP", "DAP", "CIP", "CIF", "CFR", "FOB", "FCA", "EXW"]


# ================================
# Parsing helpers
# ================================

CURRENCY_SYMBOLS = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
    "دج": "DZD",
}

CURRENCY_CODES = {"USD", "EUR", "GBP", "JPY", "DZD", "AED", "SAR", "CNY", "RMB"}


def _to_number(raw: Any) -> Optional[float]:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    text = str(raw).strip()
    if not text:
        return None

    # Handle K/M suffix
    m = re.search(r"(\d+(?:\.\d+)?)(\s*[kKmM])", text)
    if m:
        num = float(m.group(1))
        suffix = m.group(2).strip().lower()
        if suffix == "k":
            return num * 1_000
        if suffix == "m":
            return num * 1_000_000

    # Strip currency symbols and commas
    text = re.sub(r"[^0-9.]+", "", text)
    try:
        return float(text) if text else None
    except Exception:
        return None


def _normalize_currency(cur: Optional[str]) -> str:
    if not cur:
        return DEFAULT_CURRENCY
    cur = cur.strip().upper()
    if cur in CURRENCY_SYMBOLS:
        return CURRENCY_SYMBOLS[cur]
    if cur in CURRENCY_CODES:
        return cur
    return DEFAULT_CURRENCY


def parse_price(value: Any, default_currency: str = DEFAULT_CURRENCY) -> Tuple[Optional[float], str]:
    if isinstance(value, dict):
        amt = _to_number(value.get("amount"))
        cur = _normalize_currency(value.get("currency") or default_currency)
        return amt, cur
    if isinstance(value, (int, float)):
        return float(value), _normalize_currency(default_currency)

    text = str(value or "").strip()
    if not text:
        return None, _normalize_currency(default_currency)

    cur = None
    for symbol, code in CURRENCY_SYMBOLS.items():
        if symbol in text:
            cur = code
            break
    if not cur:
        for code in CURRENCY_CODES:
            if code in text.upper():
                cur = code
                break

    amt = _to_number(text)
    return amt, _normalize_currency(cur or default_currency)


def parse_percent(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None


def parse_days(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    t = text.lower()
    m = re.search(r"(\d+)\s*day", t)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)\s*week", t)
    if m:
        return int(m.group(1)) * 7
    m = re.search(r"(\d+)\s*month", t)
    if m:
        return int(m.group(1)) * 30
    return None


def parse_months(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    t = text.lower()
    m = re.search(r"(\d+)\s*month", t)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)\s*year", t)
    if m:
        return int(m.group(1)) * 12
    return None


def parse_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(float(value))
    except Exception:
        return None


def extract_incoterm(text: str) -> Optional[str]:
    if not text:
        return None
    t = text.upper()
    for inc in INCOTERMS_INFO.keys():
        if inc in t:
            return inc
    return None


def extract_offer_signals(text: str) -> Dict[str, Any]:
    if not text:
        return {}

    price, currency = parse_price(text, DEFAULT_CURRENCY)
    incoterm = extract_incoterm(text)
    lead_time_days = parse_days(text)
    warranty_months = parse_months(text)
    deposit_pct = parse_percent(text)

    return {
        "price": price,
        "currency": currency,
        "incoterm": incoterm,
        "lead_time_days": lead_time_days,
        "warranty_months": warranty_months,
        "deposit_pct": deposit_pct,
    }


# ================================
# Negotiation logic
# ================================

@dataclass
class NegotiationConfig:
    price_weight: float = 0.5
    incoterm_weight: float = 0.15
    payment_weight: float = 0.15
    lead_time_weight: float = 0.1
    warranty_weight: float = 0.05
    moq_weight: float = 0.05

    concession_rate: float = DEFAULT_CONCESSION_RATE
    anchor_discount: float = DEFAULT_ANCHOR_DISCOUNT
    max_rounds: int = DEFAULT_MAX_ROUNDS


def evaluate_incoterm(incoterm: Optional[str], preferred: Optional[List[str]] = None) -> Dict[str, Any]:
    if not incoterm:
        return {
            "incoterm": None,
            "status": "missing",
            "buyer_score": 0.4,
            "description": "No incoterm provided.",
            "buyer_risk": "Unknown",
            "preferred": preferred or DEFAULT_PREFERRED_INCOTERMS,
        }

    inc = incoterm.strip().upper()
    info = INCOTERMS_INFO.get(inc)
    if not info:
        return {
            "incoterm": inc,
            "status": "unknown",
            "buyer_score": 0.45,
            "description": "Unknown incoterm. Please confirm responsibilities.",
            "buyer_risk": "Unknown",
            "preferred": preferred or DEFAULT_PREFERRED_INCOTERMS,
        }

    preferred = preferred or DEFAULT_PREFERRED_INCOTERMS
    preferred = [p.upper() for p in preferred]
    preferred_match = inc in preferred

    # boost if preferred
    buyer_score = info["buyer_score"] + (0.08 if preferred_match else 0.0)
    buyer_score = min(buyer_score, 1.0)

    return {
        "incoterm": inc,
        "status": "ok",
        "buyer_score": buyer_score,
        "description": info["description"],
        "buyer_risk": info["buyer_risk"],
        "preferred": preferred,
        "preferred_match": preferred_match,
    }


def score_price(offer_price: Optional[float], target_price: Optional[float], max_price: Optional[float]) -> float:
    if offer_price is None or target_price is None:
        return 0.5
    if offer_price <= target_price:
        return 1.0
    if max_price is not None and offer_price >= max_price:
        return 0.0
    if max_price is not None and max_price > target_price:
        return max(0.0, 1.0 - (offer_price - target_price) / (max_price - target_price))
    return max(0.0, 1.0 - (offer_price - target_price) / max(target_price, 1.0))


def score_lead_time(lead_time_days: Optional[int], max_lead_time_days: Optional[int]) -> float:
    if lead_time_days is None or max_lead_time_days is None:
        return 0.5
    if lead_time_days <= max_lead_time_days:
        return 1.0
    return max(0.0, 1.0 - (lead_time_days - max_lead_time_days) / max(max_lead_time_days, 1))


def score_warranty(warranty_months: Optional[int], min_warranty_months: Optional[int]) -> float:
    if warranty_months is None or min_warranty_months is None:
        return 0.5
    if warranty_months >= min_warranty_months:
        return 1.0
    return max(0.0, warranty_months / max(min_warranty_months, 1))


def score_moq(moq: Optional[int], max_moq: Optional[int]) -> float:
    if moq is None or max_moq is None:
        return 0.5
    if moq <= max_moq:
        return 1.0
    return max(0.0, 1.0 - (moq - max_moq) / max(max_moq, 1))


def score_payment_terms(payment_terms: Optional[str], max_deposit_pct: Optional[float]) -> float:
    if not payment_terms and max_deposit_pct is None:
        return 0.5
    deposit = parse_percent(payment_terms) if payment_terms else None
    if deposit is None and max_deposit_pct is None:
        return 0.5
    if deposit is None:
        return 0.6
    if max_deposit_pct is None:
        return 0.6 if deposit <= 30 else 0.3
    if deposit <= max_deposit_pct:
        return 1.0
    # degrade as deposit increases beyond preferred max
    return max(0.0, 1.0 - (deposit - max_deposit_pct) / max(max_deposit_pct, 1))


def evaluate_offer(
    supplier_offer: Dict[str, Any],
    buyer_requirements: Dict[str, Any],
    cfg: NegotiationConfig,
) -> Dict[str, Any]:
    offer_price, offer_currency = parse_price(supplier_offer.get("price"), buyer_requirements.get("currency", DEFAULT_CURRENCY))
    target_price, _ = parse_price(buyer_requirements.get("target_price"), offer_currency)
    max_price, _ = parse_price(buyer_requirements.get("max_price"), offer_currency)

    incoterm_eval = evaluate_incoterm(supplier_offer.get("incoterm"), buyer_requirements.get("preferred_incoterms"))

    lead_time_offer = parse_int(supplier_offer.get("lead_time_days")) or parse_days(supplier_offer.get("lead_time"))
    warranty_offer = parse_int(supplier_offer.get("warranty_months")) or parse_months(supplier_offer.get("warranty"))
    moq_offer = parse_int(supplier_offer.get("moq"))

    max_lead = parse_int(buyer_requirements.get("max_lead_time_days"))
    min_warranty = parse_int(buyer_requirements.get("min_warranty_months"))
    max_moq = parse_int(buyer_requirements.get("max_moq"))

    max_deposit_pct = buyer_requirements.get("max_deposit_pct")
    if isinstance(max_deposit_pct, str):
        max_deposit_pct = parse_percent(max_deposit_pct)

    price_score = score_price(offer_price, target_price, max_price)
    incoterm_score = incoterm_eval["buyer_score"]
    payment_score = score_payment_terms(supplier_offer.get("payment_terms"), max_deposit_pct)
    lead_time_score = score_lead_time(lead_time_offer, max_lead)
    warranty_score = score_warranty(warranty_offer, min_warranty)
    moq_score = score_moq(moq_offer, max_moq)

    overall = (
        price_score * cfg.price_weight
        + incoterm_score * cfg.incoterm_weight
        + payment_score * cfg.payment_weight
        + lead_time_score * cfg.lead_time_weight
        + warranty_score * cfg.warranty_weight
        + moq_score * cfg.moq_weight
    )

    issues = []
    if offer_price is not None and target_price is not None and offer_price > target_price:
        issues.append("Price above target")
    if max_price is not None and offer_price is not None and offer_price > max_price:
        issues.append("Price above maximum")
    if incoterm_eval.get("preferred_match") is False:
        issues.append("Incoterm not preferred")
    if lead_time_offer is not None and max_lead is not None and lead_time_offer > max_lead:
        issues.append("Lead time above target")
    if warranty_offer is not None and min_warranty is not None and warranty_offer < min_warranty:
        issues.append("Warranty below target")
    if moq_offer is not None and max_moq is not None and moq_offer > max_moq:
        issues.append("MOQ above target")

    recommendation = "counter"
    if overall >= 0.85:
        recommendation = "accept"
    elif overall <= 0.45:
        recommendation = "counter_aggressively"

    return {
        "price": offer_price,
        "currency": offer_currency,
        "scores": {
            "price": round(price_score, 3),
            "incoterm": round(incoterm_score, 3),
            "payment": round(payment_score, 3),
            "lead_time": round(lead_time_score, 3),
            "warranty": round(warranty_score, 3),
            "moq": round(moq_score, 3),
            "overall": round(overall, 3),
        },
        "incoterm_evaluation": incoterm_eval,
        "issues": issues,
        "recommendation": recommendation,
    }


def _round_price(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return round(value, 2)


def compute_counter_offer(
    supplier_offer: Dict[str, Any],
    buyer_requirements: Dict[str, Any],
    negotiation_state: Dict[str, Any],
    cfg: NegotiationConfig,
) -> Dict[str, Any]:
    offer_price, offer_currency = parse_price(supplier_offer.get("price"), buyer_requirements.get("currency", DEFAULT_CURRENCY))
    target_price, _ = parse_price(buyer_requirements.get("target_price"), offer_currency)
    max_price, _ = parse_price(buyer_requirements.get("max_price"), offer_currency)

    round_index = int(negotiation_state.get("round", 1) or 1)
    round_index = max(1, round_index)

    anchor_discount = float(negotiation_state.get("anchor_discount", cfg.anchor_discount))
    concession_rate = float(negotiation_state.get("concession_rate", cfg.concession_rate))

    if target_price is None:
        counter_price = offer_price
    else:
        anchor_price = target_price * (1 - anchor_discount)
        counter_price = anchor_price + (round_index - 1) * (concession_rate * target_price)
        if offer_price is not None:
            # Never counter above supplier price unless needed
            counter_price = min(counter_price, offer_price)
        if max_price is not None:
            counter_price = min(counter_price, max_price)

    # Terms improvements
    preferred_incoterms = buyer_requirements.get("preferred_incoterms") or DEFAULT_PREFERRED_INCOTERMS
    preferred_incoterm = preferred_incoterms[0] if preferred_incoterms else supplier_offer.get("incoterm")

    payment_terms = buyer_requirements.get("preferred_payment_terms") or "30% deposit, 70% against BL"

    max_lead = parse_int(buyer_requirements.get("max_lead_time_days"))
    min_warranty = parse_int(buyer_requirements.get("min_warranty_months"))
    max_moq = parse_int(buyer_requirements.get("max_moq"))

    counter = {
        "price": _round_price(counter_price),
        "currency": offer_currency,
        "incoterm": preferred_incoterm,
        "payment_terms": payment_terms,
        "lead_time_days": max_lead or supplier_offer.get("lead_time_days"),
        "warranty_months": min_warranty or supplier_offer.get("warranty_months"),
        "moq": max_moq or supplier_offer.get("moq"),
        "valid_until": (datetime.utcnow() + timedelta(days=7)).strftime("%Y-%m-%d"),
    }

    return counter


def _llm_generate(prompt: str, system_instruction: str, temperature: float = 0.3) -> Optional[str]:
    try:
        from vertex_utils import generate_message
        with task("module5.llm_generate", logger):
            return generate_message(
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=temperature,
                top_p=0.95,
            )
    except Exception:
        return None


def draft_email(
    email_type: str,
    buyer_context: Dict[str, Any],
    supplier_offer: Dict[str, Any],
    counter_offer: Dict[str, Any],
    evaluation: Dict[str, Any],
    language: str = DEFAULT_LANGUAGE,
) -> str:
    buyer_company = buyer_context.get("buyer_company", "Buyer")
    supplier_company = buyer_context.get("supplier_company", "Supplier")
    product_name = buyer_context.get("product_name", "equipment")
    quantity = buyer_context.get("quantity", 1)
    contact_name = buyer_context.get("contact_name", "")

    system = (
        "You are a procurement negotiator. Write concise, professional emails in English. "
        "Be polite, firm, and specific about requested changes."
    )

    prompt = f"""
Write a {email_type} negotiation email.

Context:
- Buyer company: {buyer_company}
- Supplier company: {supplier_company}
- Product: {product_name}
- Quantity: {quantity}
- Contact name: {contact_name}

Supplier offer (JSON):
{json.dumps(supplier_offer, ensure_ascii=False)}

Counter offer (JSON):
{json.dumps(counter_offer, ensure_ascii=False)}

Evaluation:
{json.dumps(evaluation, ensure_ascii=False)}

Requirements:
- Keep it under 180 words.
- Ask for the counter terms explicitly.
- Close with a clear next step.
"""

    text = _llm_generate(prompt, system, temperature=0.3)
    if text:
        return text.strip()

    # Fallback template
    counter_price = counter_offer.get("price")
    currency = counter_offer.get("currency", DEFAULT_CURRENCY)
    incoterm = counter_offer.get("incoterm")
    payment_terms = counter_offer.get("payment_terms")

    return (
        f"Hello {contact_name or ''},\n\n"
        f"Thank you for the offer on {product_name} (qty {quantity}). "
        f"We are interested, but to proceed we need a better commercial package. "
        f"Our counter is {counter_price} {currency} per unit on {incoterm} terms, "
        f"with payment terms {payment_terms}.\n\n"
        "Please confirm if you can adjust price and terms accordingly, or propose your best offer. "
        "If aligned, we can move to PO and confirm the delivery schedule.\n\n"
        f"Regards,\n{buyer_company}"
    ).strip()


def draft_voice_reply(
    conversation: List[Dict[str, str]],
    buyer_requirements: Dict[str, Any],
    counter_offer: Dict[str, Any],
    evaluation: Dict[str, Any],
) -> str:
    system = (
        "You are a skilled procurement negotiator. Respond in English with a short spoken reply. "
        "Be polite, firm, and concise."
    )

    convo_text = "\n".join([
        f"{m.get('role', 'speaker').title()}: {m.get('text', '')}" for m in conversation[-8:]
    ])

    prompt = f"""
Conversation so far:
{convo_text}

Buyer requirements:
{json.dumps(buyer_requirements, ensure_ascii=False)}

Counter offer:
{json.dumps(counter_offer, ensure_ascii=False)}

Evaluation:
{json.dumps(evaluation, ensure_ascii=False)}

Generate the next spoken reply (max 70 words)."
"""

    text = _llm_generate(prompt, system, temperature=0.4)
    if text:
        return text.strip()

    # Fallback
    return "Thanks for the update. We can proceed if you can match our target price and improve terms on delivery and payment. Please confirm your best offer so we can finalize."


def summarize_best_offer(
    conversation: List[Dict[str, str]],
    last_offer: Dict[str, Any],
) -> str:
    system = "You are a procurement analyst. Summarize the best offer from the conversation." \
             " Provide a concise bullet list in English."

    convo_text = "\n".join([
        f"{m.get('role', 'speaker').title()}: {m.get('text', '')}" for m in conversation[-12:]
    ])

    prompt = f"""
Conversation:
{convo_text}

Last known offer (JSON):
{json.dumps(last_offer, ensure_ascii=False)}

Summarize the best offer in 4-6 bullets (price, incoterm, payment, lead time, warranty, MOQ)."
"""

    text = _llm_generate(prompt, system, temperature=0.2)
    if text:
        return text.strip()

    # Fallback
    return "- Best offer summary unavailable (LLM failed)."


# ================================
# Voice helpers
# ================================

def transcribe_audio(audio_bytes: bytes) -> Dict[str, Any]:
    provider = DEFAULT_VOICE_STT_PROVIDER
    if provider not in ("gemini", "none"):
        provider = "none"

    if provider == "none":
        return {
            "status": "not_configured",
            "transcript": None,
            "provider": provider,
            "detail": "No free-tier STT provider configured. Provide supplier_text or set VOICE_STT_PROVIDER=gemini.",
        }

    try:
        from vertex_utils import generate_message
        prompt = "Transcribe the following audio in English. Return plain text only."
        text = generate_message(
            prompt=prompt,
            system_instruction="Return only the transcript text.",
            audio=[audio_bytes],
            temperature=0.0,
            top_p=1.0,
        )
        return {
            "status": "ok",
            "transcript": (text or "").strip(),
            "provider": "gemini",
        }
    except Exception as e:
        return {
            "status": "error",
            "transcript": None,
            "provider": "gemini",
            "detail": str(e),
        }


def synthesize_speech(text: str) -> Dict[str, Any]:
    provider = DEFAULT_VOICE_TTS_PROVIDER
    if provider not in ("none",):
        provider = "none"

    return {
        "status": "not_configured",
        "provider": provider,
        "voice": DEFAULT_VOICE_TTS_VOICE,
        "audio_b64": None,
        "detail": "No free-tier TTS provider configured. Use tts_text with client-side TTS.",
    }


# ================================
# High-level orchestration
# ================================

def run_text_negotiation(payload: Dict[str, Any]) -> Dict[str, Any]:
    with task("module5.run_text_negotiation", logger):
        buyer_requirements = payload.get("buyer_requirements") or {}
        if not isinstance(buyer_requirements, dict):
            buyer_requirements = {}
        supplier_offer = payload.get("supplier_offer") or {}
        if not isinstance(supplier_offer, dict):
            supplier_offer = {}
        negotiation_state = payload.get("negotiation_state") or {}
        if not isinstance(negotiation_state, dict):
            negotiation_state = {}
        email_context = payload.get("email_context") or payload.get("context") or {}
        if not isinstance(email_context, dict):
            email_context = {}

        cfg = NegotiationConfig()

        with task("module5.evaluate_offer", logger):
            evaluation = evaluate_offer(supplier_offer, buyer_requirements, cfg)
        with task("module5.compute_counter_offer", logger):
            counter_offer = compute_counter_offer(supplier_offer, buyer_requirements, negotiation_state, cfg)

        email_type = payload.get("email_type")
        if not email_type:
            email_type = "accept" if evaluation.get("recommendation") == "accept" else "counter"

        with task("module5.draft_email", logger):
            email_draft = draft_email(
                email_type=email_type,
                buyer_context=email_context,
                supplier_offer=supplier_offer,
                counter_offer=counter_offer,
                evaluation=evaluation,
                language=DEFAULT_LANGUAGE,
            )

        negotiation_state_out = dict(negotiation_state)
        negotiation_state_out["round"] = int(negotiation_state.get("round", 1) or 1) + 1
        negotiation_state_out["max_rounds"] = negotiation_state.get("max_rounds", cfg.max_rounds)

        return {
            "evaluation": evaluation,
            "counter_offer": counter_offer,
            "email_draft": email_draft,
            "next_action": evaluation.get("recommendation"),
            "negotiation_state": negotiation_state_out,
            "timestamp": datetime.utcnow().isoformat(),
        }


def run_voice_negotiation(payload: Dict[str, Any]) -> Dict[str, Any]:
    with task("module5.run_voice_negotiation", logger):
        buyer_requirements = payload.get("buyer_requirements") or {}
        if not isinstance(buyer_requirements, dict):
            buyer_requirements = {}
        negotiation_state = payload.get("negotiation_state") or {}
        if not isinstance(negotiation_state, dict):
            negotiation_state = {}
        conversation = payload.get("conversation") or []
        if not isinstance(conversation, list):
            conversation = []

        supplier_text = payload.get("supplier_text")
        audio_bytes = payload.get("audio_bytes")

        transcript_info = None
        if audio_bytes:
            with task("module5.transcribe_audio", logger):
                transcript_info = transcribe_audio(audio_bytes)
            supplier_text = supplier_text or transcript_info.get("transcript")
        else:
            log_skip("module5.transcribe_audio", reason="no_audio_bytes", logger=logger)
            transcript_info = {
                "status": "skipped",
                "transcript": supplier_text,
                "provider": None,
            }

        if supplier_text:
            conversation.append({"role": "supplier", "text": supplier_text})

        with task("module5.extract_offer_signals", logger):
            offer_signals = extract_offer_signals(supplier_text or "")
        supplier_offer = payload.get("supplier_offer") or {}
        if not isinstance(supplier_offer, dict):
            supplier_offer = {}
        for key, value in offer_signals.items():
            if value is not None:
                supplier_offer[key] = value

        cfg = NegotiationConfig()
        with task("module5.evaluate_offer", logger):
            evaluation = evaluate_offer(supplier_offer, buyer_requirements, cfg)
        with task("module5.compute_counter_offer", logger):
            counter_offer = compute_counter_offer(supplier_offer, buyer_requirements, negotiation_state, cfg)

        with task("module5.draft_voice_reply", logger):
            reply_text = draft_voice_reply(conversation, buyer_requirements, counter_offer, evaluation)

        conversation.append({"role": "assistant", "text": reply_text})

        with task("module5.synthesize_speech", logger):
            tts_payload = synthesize_speech(reply_text)

        end_call = bool(payload.get("end_call"))
        best_offer_summary = None
        if end_call:
            with task("module5.summarize_best_offer", logger):
                best_offer_summary = summarize_best_offer(conversation, supplier_offer)
        else:
            log_skip("module5.summarize_best_offer", reason="end_call_false", logger=logger)

        negotiation_state_out = dict(negotiation_state)
        negotiation_state_out["round"] = int(negotiation_state.get("round", 1) or 1) + 1
        negotiation_state_out["max_rounds"] = negotiation_state.get("max_rounds", cfg.max_rounds)

        return {
            "transcript": transcript_info,
            "conversation": conversation,
            "evaluation": evaluation,
            "counter_offer": counter_offer,
            "reply_text": reply_text,
            "tts": tts_payload,
            "best_offer_summary": best_offer_summary,
            "next_action": evaluation.get("recommendation"),
            "negotiation_state": negotiation_state_out,
            "timestamp": datetime.utcnow().isoformat(),
        }
