"""
Module 5: AI Negotiation System
================================
Email-based automated negotiation with suppliers.
"""
from utils.module_5.core import (
    run_text_negotiation,
    run_voice_negotiation,
    summarize_best_offer,
    evaluate_offer,
    compute_counter_offer,
    extract_offer_signals,
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

__all__ = [
    # Core negotiation
    "run_text_negotiation",
    "run_voice_negotiation",
    "summarize_best_offer",
    "evaluate_offer",
    "compute_counter_offer",
    "extract_offer_signals",
    "NegotiationConfig",
    # Thread management
    "NegotiationThread",
    "NegotiationStatus",
    "create_thread_from_supplier",
    "load_thread",
    "save_thread",
    "list_threads",
    "add_email_to_thread",
    "update_thread_status",
    "update_supplier_offer",
    "update_counter_offer",
    "increment_round",
    "should_auto_accept",
    "should_stop_negotiation",
    # Email generation
    "generate_initial_rfq_email",
    "generate_initial_rfq_subject",
    "generate_reply_subject",
    "generate_negotiation_email",
    "generate_acceptance_email",
    "parse_supplier_response",
]
