# backend/utils/module_4/__init__.py
"""
Module 4 - Machine Enrichment

Provides both legacy (unbounded) and new (bounded) enrichment approaches.

DEFAULT: Uses bounded approach (core_v2)
LEGACY: Available via core.py for backward compatibility
"""

# NEW: Bounded approach (default)
from .core_v2 import (
    process_module_4_bounded,
    canonicalize_machine,
    ground_machine,
    web_validate_minimal,
    synthesize_final,
)

# LEGACY: Unbounded approach (backward compatibility)
# from .core import build_machines_enriched

__all__ = [
    # Bounded (recommended)
    "process_module_4_bounded",
    "canonicalize_machine",
    "ground_machine",
    "web_validate_minimal",
    "synthesize_final",
    
    # Legacy (for reference)
    # "build_machines_enriched",
]

# Version info
__version__ = "2.0.0-bounded"
__bounded__ = True
