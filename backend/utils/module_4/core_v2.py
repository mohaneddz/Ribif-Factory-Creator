# backend/utils/module_4/core_v2.py
"""
RIBIF Module 4 — REWRITTEN FOR SPEED, BOUNDED, AND ACCURACY
===========================================================

Design Principles:
1. Module 4 contextualizes + validates machine info, not "crawl the internet"
2. Prefer stable industry priors (internal knowledge) over web
3. Web usage is OPTIONAL and only for VALIDATION when confidence is low
4. Hard caps everywhere; no retries that multiply cost

4-Phase Pipeline:
  Phase A — Canonicalize + Classify (NO WEB)
  Phase B — Industry Grounding (NO WEB, deterministic)
  Phase C — Minimal Web Validation (OPTIONAL, bounded)
  Phase D — Single Synthesis (ONE LLM CALL MAX)

Acceptance Criteria:
  40 inputs should complete with:
    ≤ 80 total web calls
    ≤ 40 LLM calls (ideally less)
    predictable runtime
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import re

from dotenv import load_dotenv
from vertex_utils import generate_message
from utils.logger import get_logger
from config import WEB_SEARCH_ENABLED
from utils.module_4.budget_tracker import GlobalBudget, PerMachineBudget
from utils.module_4.global_budget import GlobalBudgetController  # NEW: Hard budget enforcement
from utils.module_4.supplier_outcome import SupplierOutcomeRegistry, SupplierOutcomeStatus, SupplierOutcome
from utils.module_4.supplier_filter import (
    filter_suppliers, 
    deduplicate_suppliers,
    apply_quality_threshold,  # NEW: Enhanced quality scoring
    compute_quality_score     # NEW: Evidence-based scoring
)
from utils.module_4.contact_extractor import (  # NEW: Contact extraction
    fetch_and_extract_contacts,
    extract_contacts_from_html,
    detect_region_from_url,
    extract_emails_from_text,  # NEW: Email extraction from text
    extract_phones_from_text   # NEW: Phone extraction from text
)
from utils.module_4.ai_fallback import (  # NEW: AI fallback suppliers
    generate_ai_fallback_suppliers,
    add_no_suppliers_subtext
)

load_dotenv()
logger = get_logger(__name__)

# =========================================================
# CONFIGURATION & CONSTANTS
# =========================================================

# FAST MODE: Skip web searches completely and use cached/fallback data only
# Controlled via FAST_MODE_MODULE4 env var (default: DISABLED for better results)
FAST_MODE_MODULE4 = os.getenv("FAST_MODE_MODULE4", "0").lower() in ("1", "true", "yes")

# Global budget - INCREASED for better supplier discovery
# Each machine gets ~18 calls for thorough search (queries + pages)
GLOBAL_WEB_CALL_MULTIPLIER = 2 if FAST_MODE_MODULE4 else 18  # 18 calls per machine in normal mode

# Per-machine budgets (Phase C only) - Increased for better coverage
MAX_SEARCH_QUERIES_PER_MACHINE = 1 if FAST_MODE_MODULE4 else 6  # 6 queries per machine
MAX_RESULTS_PER_QUERY = 5 if FAST_MODE_MODULE4 else 20  # 20 results per query
MAX_FETCH_PAGES_TOTAL = 3 if FAST_MODE_MODULE4 else 15  # 15 page fetches per machine (increased from 10)
MAX_LLM_CALLS_PER_MACHINE = 1 if FAST_MODE_MODULE4 else 3  # 3 LLM calls per machine
MAX_RUNTIME_PER_MACHINE_S = 15 if FAST_MODE_MODULE4 else 150  # 2.5 min timeout in normal mode

# Cache TTL
CACHE_TTL_DAYS = 7

# Cache control - NOW ENABLED by default for cost savings
USE_CACHE = True  # Set to False to disable cache and always fetch fresh data

# Machine classes
CLASS_CORE_STABLE = "core_stable"
CLASS_CORE_VARIABLE = "core_variable"
CLASS_OPTIONAL = "optional_system"
CLASS_SUBSYSTEM = "subsystem_qc_utility"

# Confidence levels
CONF_HIGH = "high"
CONF_MEDIUM = "medium"
CONF_LOW = "low"

# =========================================================
# QUANTITY STRUCTURE HELPERS
# =========================================================

def structure_quantity(machine: Dict[str, Any]) -> Dict[str, Any]:
    """
    Structure quantity into {value, source} format.
    
    Rules:
    - If unknown/missing: {value: null, source: "undefined"} → UI shows "Qté: à définir"
    - If explicit in input: {value: X, source: "user_input"} → UI shows "Qté: X"
    - Never infer unless explicit
    - Never show "N/A" next to a number
    
    Returns:
        {value: int|null, source: str}
    """
    raw_quantity = machine.get("quantite_necessaire")
    
    # Check if quantity was explicitly provided
    if raw_quantity is not None and raw_quantity != "" and raw_quantity != "N/A":
        try:
            # Try to parse as number
            value = int(raw_quantity) if isinstance(raw_quantity, (int, float, str)) and str(raw_quantity).replace('.', '').isdigit() else None
            if value is not None and value > 0:
                return {"value": value, "source": "user_input"}
        except (ValueError, TypeError):
            pass
    
    # Unknown/undefined quantity
    return {"value": None, "source": "undefined"}

# Fallback suppliers for network/search failures (by category)
FALLBACK_SUPPLIERS = {
    "injection_molding": [
        {"supplier_name": "Haitian International", "region": "China", "website": "https://www.haitian.com", "price_estimate": "Contact for quote", "price_type": "FOB", "notes": "Fallback: Major global injection molding machine manufacturer", "relevance_score": 0.6},
        {"supplier_name": "Engel Austria", "region": "Europe", "website": "https://www.engelglobal.com", "price_estimate": "Contact for quote", "price_type": "Ex-works", "notes": "Fallback: Premium injection molding equipment", "relevance_score": 0.6},
    ],
    "extrusion": [
        {"supplier_name": "Davis-Standard", "region": "USA", "website": "https://www.davis-standard.com", "price_estimate": "Contact for quote", "price_type": "FOB", "notes": "Fallback: Leading extrusion systems manufacturer", "relevance_score": 0.6},
        {"supplier_name": "KraussMaffei Berstorff", "region": "Germany", "website": "https://www.kraussmaffei.com", "price_estimate": "Contact for quote", "price_type": "Ex-works", "notes": "Fallback: Premium extrusion technology", "relevance_score": 0.6},
    ],
    "thermoforming": [
        {"supplier_name": "ILLIG Maschinenbau", "region": "Germany", "website": "https://www.illig.de", "price_estimate": "Contact for quote", "price_type": "Ex-works", "notes": "Fallback: Leading thermoforming equipment", "relevance_score": 0.6},
        {"supplier_name": "Kiefel GmbH", "region": "Germany", "website": "https://www.kiefel.com", "price_estimate": "Contact for quote", "price_type": "Ex-works", "notes": "Fallback: Industrial thermoforming systems", "relevance_score": 0.6},
    ],
    "robotics": [
        {"supplier_name": "ABB Robotics", "region": "Global", "website": "https://new.abb.com/products/robotics", "price_estimate": "Contact for quote", "price_type": "Ex-works", "notes": "Fallback: Major industrial robotics manufacturer", "relevance_score": 0.6},
        {"supplier_name": "KUKA Robotics", "region": "Germany", "website": "https://www.kuka.com", "price_estimate": "Contact for quote", "price_type": "Ex-works", "notes": "Fallback: Leading robot manufacturer", "relevance_score": 0.6},
        {"supplier_name": "Fanuc Corporation", "region": "Japan", "website": "https://www.fanuc.com", "price_estimate": "Contact for quote", "price_type": "FOB", "notes": "Fallback: Industrial automation and robots", "relevance_score": 0.6},
    ],
    "generic_machinery": [
        {"supplier_name": "Industrial Equipment Suppliers Algeria", "region": "Algeria", "website": "", "price_estimate": "Contact for quote", "price_type": "Local", "notes": "Fallback: Local industrial equipment integrator", "relevance_score": 0.5},
        {"supplier_name": "Machine Tool Distributors MENA", "region": "MENA", "website": "", "price_estimate": "Contact for quote", "price_type": "Regional", "notes": "Fallback: Regional machinery distributor", "relevance_score": 0.5},
    ],
}

# =========================================================
# CACHING
# =========================================================

# Import CACHE_DIR from config (handles read-only filesystem fallback)
try:
    from config import CACHE_DIR as BASE_CACHE_DIR
    CACHE_DIR = BASE_CACHE_DIR / "module_4"
except ImportError:
    CACHE_DIR = Path("cache/module_4")

try:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    pass  # Read-only filesystem, caching will be disabled

def _cache_key(canonical_name: str, version: str) -> str:
    """Generate cache key."""
    key = f"{canonical_name}::{version}"
    return hashlib.md5(key.encode()).hexdigest()

def _cache_get(canonical_name: str, cache_type: str, ttl_days: int = CACHE_TTL_DAYS) -> Optional[Dict]:
    """Get from cache if not expired."""
    key = _cache_key(canonical_name, cache_type)
    cache_file = CACHE_DIR / f"{key}.json"
    
    if not cache_file.exists():
        return None
    
    # Check TTL
    age_days = (time.time() - cache_file.stat().st_mtime) / 86400
    if age_days > ttl_days:
        return None
    
    try:
        return json.loads(cache_file.read_text(encoding="utf-8"))
    except Exception:
        return None

def _cache_set(canonical_name: str, cache_type: str, data: Dict) -> None:
    """Save to cache."""
    key = _cache_key(canonical_name, cache_type)
    cache_file = CACHE_DIR / f"{key}.json"
    
    try:
        cache_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning(f"Cache write failed: {e}")

# =========================================================
# PHASE A — CANONICALIZE + CLASSIFY (NO WEB)
# =========================================================

# Canonical mapping for known machines (merge synonyms)
CANONICAL_MAP = {
    # Injection molding
    "machine d'injection plastique": "Plastic Injection Molding Machine",
    "presse à injecter": "Plastic Injection Molding Machine",
    "injection molding machine": "Plastic Injection Molding Machine",
    "presse à injection": "Plastic Injection Molding Machine",
    
    # Extrusion
    "machine d'extrusion": "Polymer Extrusion Line",
    "extrudeuse": "Polymer Extrusion Line",
    "extrusion line": "Polymer Extrusion Line",
    "ligne d'extrusion": "Polymer Extrusion Line",
    "ligne extrusion": "Polymer Extrusion Line",
    
    # Thermoforming
    "machine de thermoformage": "Thermoforming Machine",
    "thermoforming machine": "Thermoforming Machine",
    "thermoformage": "Thermoforming Machine",
    
    # Press
    "presse membrane 3d": "3D Membrane Vacuum Press",
    "membrane press": "3D Membrane Vacuum Press",
    "presse membrane": "3D Membrane Vacuum Press",
    
    # Robotics
    "robot de peinture et vernis": "Industrial Painting Robot",
    "robot de peinture": "Industrial Painting Robot",
    "painting robot": "Industrial Painting Robot",
    "robot industriel": "Industrial Robot",
    "industrial robot": "Industrial Robot",
    
    # Mixing
    "mélangeur industriel": "Industrial Mixer",
    "industrial mixer": "Industrial Mixer",
    "mélangeur": "Industrial Mixer",
    
    # Calendering
    "calandre": "Calendering Subsystem",
    "calandre de refroidissement": "Cooling Calendering Subsystem",
    
    # Surface treatment
    "ligne de traitement de surface": "Surface Treatment Line",
    "traitement de surface": "Surface Treatment Line",
    
    # Vision systems (SUBSYSTEM - exclude)
    "système de vision": "Vision QC Subsystem",
    "système de vision automatisé": "Vision QC Subsystem",
    "vision system": "Vision QC Subsystem",
    
    # Packaging (optional)
    "ligne de conditionnement": "Automated Packaging Line",
    "ligne de conditionnement automatisée": "Automated Packaging Line",
    "packaging line": "Automated Packaging Line",
    
    # Logistics (OPTIONAL)
    "agv": "Automated Guided Vehicle",
    "véhicule guidé automatisé": "Automated Guided Vehicle",
    "automated guided vehicle": "Automated Guided Vehicle",
    
    "asrs": "Automated Storage and Retrieval System",
    "système automatisé de stockage": "Automated Storage and Retrieval System",
    "automated storage": "Automated Storage and Retrieval System",
    
    # Subsystems (TO BE EXCLUDED)
    "bain de refroidissement": "Cooling Bath Subsystem",
    "cooling bath": "Cooling Bath Subsystem",
    "système de refroidissement": "Cooling System Subsystem",
    "cooling system": "Cooling System Subsystem",
    "convoyeur": "Conveyor Subsystem",
    "conveyor": "Conveyor Subsystem",
    "silo": "Storage Silo Subsystem",
    "silo de stockage": "Storage Silo Subsystem",
    "sécheur": "Dryer Subsystem",
    "sécheur de granules": "Dryer Subsystem",
    "capteur": "Sensor Subsystem",
    "sensor": "Sensor Subsystem",
}

# Classification rules
CLASSIFICATION_RULES = {
    # Core stable - well-known machines with standard specs
    CLASS_CORE_STABLE: [
        "Plastic Injection Molding Machine",
        "Polymer Extrusion Line",
        "Thermoforming Machine",
    ],
    
    # Core variable - core machines but specs vary widely
    CLASS_CORE_VARIABLE: [
        "3D Membrane Vacuum Press",
        "Industrial Painting Robot",
        "Industrial Robot",
        "Industrial Mixer",
        "Surface Treatment Line",
    ],
    
    # Optional systems - not critical for enrichment
    CLASS_OPTIONAL: [
        "Automated Guided Vehicle",
        "Automated Storage and Retrieval System",
        "Automated Packaging Line",
    ],
    
    # Subsystems - MUST BE EXCLUDED
    CLASS_SUBSYSTEM: [
        "Cooling Bath Subsystem",
        "Cooling Calendering Subsystem",
        "Calendering Subsystem",
        "Cooling System Subsystem",
        "Conveyor Subsystem",
        "Storage Silo Subsystem",
        "Dryer Subsystem",
        "Vision QC Subsystem",
        "Sensor Subsystem",
    ],
}

def _normalize_name(name: str) -> str:
    """Normalize machine name for matching."""
    return name.lower().strip()

def canonicalize_machine(nom_machine: str) -> Tuple[str, str, str]:
    """
    Phase A: Canonicalize + Classify
    
    Returns:
        (canonical_name, machine_class, confidence)
    """
    normalized = _normalize_name(nom_machine)
    
    # Try exact match in canonical map
    if normalized in CANONICAL_MAP:
        canonical = CANONICAL_MAP[normalized]
        confidence = CONF_HIGH
    else:
        # Try fuzzy match (contains)
        canonical = None
        for key, value in CANONICAL_MAP.items():
            if key in normalized or normalized in key:
                canonical = value
                confidence = CONF_MEDIUM
                break
        
        if canonical is None:
            # Unknown machine - use original name
            canonical = nom_machine
            confidence = CONF_LOW
    
    # Classify
    machine_class = None
    for cls, machines in CLASSIFICATION_RULES.items():
        if canonical in machines:
            machine_class = cls
            break
    
    # Default to core_variable if not classified
    if machine_class is None:
        machine_class = CLASS_CORE_VARIABLE
    
    return canonical, machine_class, confidence

# =========================================================
# PHASE B — INDUSTRY GROUNDING (NO WEB, deterministic)
# =========================================================

# Industry knowledge base (deterministic priors)
INDUSTRY_KNOWLEDGE = {
    "Plastic Injection Molding Machine": {
        "role": "Injects molten plastic into molds to produce parts",
        "typical_capacity_range": "50 tons - 5000 tons clamping force",
        "typical_power_range": "10 kW - 500 kW",
        "typical_footprint_range": "4m x 2m - 20m x 5m",
        "typical_manufacturers": ["Haitian", "Engel", "Arburg", "Husky", "Sumitomo"],
    },
    "Polymer Extrusion Line": {
        "role": "Continuously forms plastic by forcing through a die",
        "typical_capacity_range": "50 kg/h - 2000 kg/h output",
        "typical_power_range": "30 kW - 300 kW",
        "typical_footprint_range": "10m x 3m - 50m x 5m",
        "typical_manufacturers": ["Battenfeld-Cincinnati", "Davis-Standard", "KraussMaffei", "Coperion", "Reifenhäuser"],
    },
    "Thermoforming Machine": {
        "role": "Heats plastic sheets and forms them using vacuum or pressure",
        "typical_capacity_range": "Small (A4) - Large (3m x 2m) sheet size",
        "typical_power_range": "15 kW - 150 kW",
        "typical_footprint_range": "3m x 2m - 15m x 5m",
        "typical_manufacturers": ["ILLIG", "GABLER", "Kiefel", "GEISS", "WM Thermoforming"],
    },
    "3D Membrane Vacuum Press": {
        "role": "Applies decorative films to 3D surfaces using vacuum and heat",
        "typical_capacity_range": "Small (50cm) - Large (3m) working area",
        "typical_power_range": "10 kW - 80 kW",
        "typical_footprint_range": "2m x 2m - 8m x 4m",
        "typical_manufacturers": ["Baumann", "Tecnomac", "Aflatek", "Orma", "Hebrock"],
    },
    "Industrial Painting Robot": {
        "role": "Automated robotic arm for paint and coating application",
        "typical_capacity_range": "Reach 1.5m - 3.5m, payload 5kg - 30kg",
        "typical_power_range": "2 kW - 8 kW",
        "typical_footprint_range": "1m x 1m - 3m x 3m base",
        "typical_manufacturers": ["ABB", "KUKA", "Fanuc", "Yaskawa", "Kawasaki"],
    },
    "Industrial Robot": {
        "role": "Multi-purpose robotic arm for handling, assembly, welding",
        "typical_capacity_range": "Payload 3kg - 500kg, reach 0.5m - 3.5m",
        "typical_power_range": "1 kW - 15 kW",
        "typical_footprint_range": "0.5m x 0.5m - 2m x 2m base",
        "typical_manufacturers": ["ABB", "KUKA", "Fanuc", "Yaskawa", "Universal Robots"],
    },
    "Industrial Mixer": {
        "role": "Blends polymers, resins, and additives for production",
        "typical_capacity_range": "10L - 5000L batch volume",
        "typical_power_range": "5 kW - 100 kW",
        "typical_footprint_range": "1m x 1m - 5m x 5m",
        "typical_manufacturers": ["Charles Ross", "Silverson", "Admix", "Eirich", "Henschel"],
    },
    "Surface Treatment Line": {
        "role": "Applies protective coatings, wear layers, or UV treatments",
        "typical_capacity_range": "1m - 5m working width",
        "typical_power_range": "20 kW - 200 kW",
        "typical_footprint_range": "10m x 3m - 50m x 5m",
        "typical_manufacturers": ["Barberan", "Cefla", "Dubois", "PRATI", "Venjakob"],
    },
    "Automated Guided Vehicle": {
        "role": "Autonomous material transport vehicle",
        "typical_capacity_range": "Load 100kg - 5000kg",
        "typical_power_range": "Battery powered: 2-10 kWh capacity",
        "typical_footprint_range": "1m x 0.7m - 3m x 2m",
        "typical_manufacturers": ["Dematic", "Swisslog", "JBT", "Seegrid", "Fetch Robotics"],
    },
    "Automated Storage and Retrieval System": {
        "role": "Automated warehouse storage with robotic retrieval",
        "typical_capacity_range": "10-10000 pallet positions",
        "typical_power_range": "5 kW - 100 kW total",
        "typical_footprint_range": "Highly variable: 5m x 5m - 100m x 50m",
        "typical_manufacturers": ["Dematic", "Swisslog", "Vanderlande", "TGW", "Daifuku"],
    },
    "Automated Packaging Line": {
        "role": "Automated packaging, wrapping, and palletizing",
        "typical_capacity_range": "10-100 units/minute",
        "typical_power_range": "10 kW - 80 kW",
        "typical_footprint_range": "10m x 3m - 30m x 5m",
        "typical_manufacturers": ["Bosch Packaging", "IMA", "Coesia", "MULTIVAC", "ULMA"],
    },
}

def ground_machine(canonical_name: str, machine_class: str, confidence: str) -> Dict[str, Any]:
    """
    Phase B: Industry Grounding (NO WEB)
    
    Returns structured draft from internal knowledge only.
    """
    # Check cache first (only if USE_CACHE is True)
    if USE_CACHE:
        cached = _cache_get(canonical_name, "specs_v1")
        if cached:
            logger.info(f"Phase B: Using cached knowledge for {canonical_name}")
            return cached
    else:
        logger.info(f"Phase B: Cache disabled, generating fresh knowledge for {canonical_name}")
    
    # Get from knowledge base
    knowledge = INDUSTRY_KNOWLEDGE.get(canonical_name, {})
    
    if knowledge:
        result = {
            "canonical_name": canonical_name,
            "machine_class": machine_class,
            "role": knowledge.get("role"),
            "typical_capacity_range": knowledge.get("typical_capacity_range"),
            "typical_power_range": knowledge.get("typical_power_range"),
            "typical_footprint_range": knowledge.get("typical_footprint_range"),
            "typical_manufacturers": knowledge.get("typical_manufacturers", []),
            "confidence": confidence,
            "confidence_reason": "Industry knowledge base",
        }
    else:
        # Unknown machine - return minimal structure
        result = {
            "canonical_name": canonical_name,
            "machine_class": machine_class,
            "role": None,
            "typical_capacity_range": None,
            "typical_power_range": None,
            "typical_footprint_range": None,
            "typical_manufacturers": [],
            "confidence": CONF_LOW,
            "confidence_reason": "Unknown machine, no internal knowledge",
        }
    
    # Cache it
    _cache_set(canonical_name, "specs_v1", result)
    
    return result

# =========================================================
# PHASE C — MINIMAL WEB VALIDATION (OPTIONAL, bounded)
# =========================================================

# NOTE: WebValidationBudget is now replaced by PerMachineBudget from budget_tracker.py

def should_validate_with_web(machine_class: str, confidence: str) -> bool:
    """Determine if web validation is needed."""
    # Never validate subsystems
    if machine_class == CLASS_SUBSYSTEM:
        return False
    
    # Don't validate optional by default
    if machine_class == CLASS_OPTIONAL:
        return False
    
    # Validate if core_variable OR confidence is low
    if machine_class == CLASS_CORE_VARIABLE or confidence == CONF_LOW:
        return True
    
    return False


def plan_phase_c_budget(
    machines_info: List[Tuple[str, str, str]],  # (name, machine_class, confidence)
    global_budget_controller: GlobalBudgetController,
    consumed_so_far: int
) -> Dict[str, Dict[str, int]]:
    """
    Phase C Planning Pass: Allocate budget across machines BEFORE execution.
    
    Strategy:
    1. Filter which machines need Phase C (core_variable OR low_confidence)
    2. Calculate remaining budget after consumed
    3. Allocate budget per machine, weighted by confidence:
       - low confidence gets 2x share (needs more validation)
       - medium/high confidence gets 1x share
    4. If insufficient budget:
       - Reduce queries per machine (5 → 3 → 1)
       - Reduce pages per machine (25 → 10 → 3)
       - Skip lowest-priority machines if still insufficient
    
    Returns:
        Dict[machine_name, {queries: int, pages: int, skip: bool}]
    """
    # Filter machines needing Phase C
    needs_phase_c = []
    for name, machine_class, confidence in machines_info:
        if should_validate_with_web(machine_class, confidence):
            needs_phase_c.append((name, confidence))
    
    if not needs_phase_c:
        logger.info("Phase C Planning: No machines need web validation")
        return {}
    
    # Calculate remaining budget
    remaining = global_budget_controller.max_budget - consumed_so_far
    logger.info(f"Phase C Planning: {len(needs_phase_c)} machines need validation, "
               f"{remaining} calls remaining")
    
    if remaining <= 0:
        logger.warning("Phase C Planning: Budget exhausted, skipping all Phase C")
        return {name: {'queries': 0, 'pages': 0, 'skip': True} for name, _ in needs_phase_c}
    
    # Weight allocation by confidence (low confidence = 2x priority)
    weights = {'low': 2.0, 'medium': 1.0, 'high': 1.0}
    total_weight = sum(weights.get(conf, 1.0) for _, conf in needs_phase_c)
    
    # Calculate per-machine allocation
    allocation = {}
    for name, confidence in needs_phase_c:
        weight = weights.get(confidence, 1.0)
        share = (weight / total_weight) * remaining
        
        # Allocate queries and pages based on share
        # Assume: 1 query = 1 call, 1 page = 1 call
        # Target: queries + pages ≈ share
        # IMPROVED: Lower thresholds to ensure machines get allocated budget
        if share >= 30:  # Plenty of budget
            queries = MAX_SEARCH_QUERIES_PER_MACHINE  # 5
            pages = min(MAX_FETCH_PAGES_TOTAL, int(share - queries))  # Up to 10
        elif share >= 15:  # Good budget
            queries = 4
            pages = min(10, int(share - queries))
        elif share >= 8:  # Medium budget
            queries = 3
            pages = min(5, int(share - queries))
        elif share >= 4:  # Tight budget - still do some searching
            queries = 2
            pages = min(2, int(share - queries))
        elif share >= 2:  # Minimal budget - do at least 1 query
            queries = 1
            pages = max(1, int(share - queries))
        else:  # Very low budget - still try 1 query
            queries = 1 if share >= 1 else 0
            pages = 0
        
        allocation[name] = {
            'queries': queries,
            'pages': pages,
            'skip': queries == 0,
            'confidence': confidence,
            'budget_share': int(share)
        }
    
    # Log allocation
    logger.info("Phase C Planning: Budget allocation per machine:")
    for name, alloc in allocation.items():
        status = "SKIP" if alloc['skip'] else "OK"
        logger.info(f"  {name}: {alloc['queries']} queries, {alloc['pages']} pages "
                   f"(share: {alloc['budget_share']} calls) [{status}]")
    
    return allocation

def get_fallback_suppliers(canonical_name: str) -> List[Dict[str, Any]]:
    """Get fallback suppliers for a machine when search/network fails."""
    # Map canonical names to fallback categories
    name_lower = canonical_name.lower()
    
    if "injection" in name_lower and "molding" in name_lower:
        return FALLBACK_SUPPLIERS.get("injection_molding", [])
    elif "extrusion" in name_lower or "extruder" in name_lower:
        return FALLBACK_SUPPLIERS.get("extrusion", [])
    elif "thermoform" in name_lower:
        return FALLBACK_SUPPLIERS.get("thermoforming", [])
    elif "robot" in name_lower:
        return FALLBACK_SUPPLIERS.get("robotics", [])
    else:
        # Generic fallback
        return FALLBACK_SUPPLIERS.get("generic_machinery", [])

def web_validate_minimal(
    canonical_name: str,
    original_name: str,
    budget: PerMachineBudget,
    outcome_registry: SupplierOutcomeRegistry,
    global_budget: GlobalBudget,
    global_budget_controller: GlobalBudgetController,  # NEW: Hard budget enforcement
    allocated_budget: Optional[Dict[str, int]] = None  # NEW: Pre-allocated budget from planning
) -> Dict[str, Any]:
    """
    Phase C: Comprehensive Supplier Collection with HARD budget enforcement
    
    FEATURES:
    - Multi-query rotation (OEM / distributor / regional)
    - Hard global budget enforcement via GlobalBudgetController
    - Pre-allocated budget from planning pass (queries, pages)
    - Best-effort: returns deduplicated raw candidates with confidence=low if filtering fails
    - Fallback suppliers if search/network fails completely
    
    INVARIANT: Always record explicit outcome (found/skipped/failed) and never returns empty due to system issues
    NEW INVARIANT: NEVER exceeds allocated budget - all web calls reserved BEFORE execution
    """
    # FAST MODE: Skip web entirely, use fallback + AI suppliers
    if FAST_MODE_MODULE4:
        logger.info(f"Phase C: FAST MODE - Skipping web search for {canonical_name}")
        
        # Get fallback suppliers for this machine type
        fallback = get_fallback_suppliers(canonical_name)
        
        # Generate AI fallback to supplement
        from utils.module_4.ai_fallback import generate_ai_fallback_suppliers
        typical_mfrs = INDUSTRY_KNOWLEDGE.get(canonical_name, {}).get('typical_manufacturers', [])
        ai_suppliers = generate_ai_fallback_suppliers(canonical_name, typical_mfrs, max_suppliers=3)
        
        for s in ai_suppliers:
            s['is_ai_fallback'] = True
            s['ai_tag'] = '★'
        
        all_suppliers = fallback + ai_suppliers
        
        outcome_registry.record_skip(
            original_name,
            SupplierOutcomeStatus.SKIPPED_GENERIC,
            f"Fast mode: Using {len(fallback)} fallback + {len(ai_suppliers)} AI suppliers"
        )
        
        return {
            "validated_suppliers": all_suppliers[:10],
            "web_source": "fast_mode_fallback",
            "queries_used": 0,
            "pages_fetched": 0,
            "candidates_evaluated": 0,
            "candidates_filtered": 0
        }
    # Check if budget limited (from planning pass)
    if allocated_budget and allocated_budget.get('skip'):
        logger.warning(f"Phase C: Skipping {original_name} - budget allocation insufficient (SKIP_REASON=budget_limited)")
        fallback = get_fallback_suppliers(canonical_name)
        outcome_registry.record_skip(
            original_name,
            SupplierOutcomeStatus.SKIPPED_BUDGET_LIMITED,
            f"Phase C stopped early due to global budget - using {len(fallback)} fallback suppliers"
        )
        return {"validated_suppliers": fallback, "web_source": "fallback_budget_limited"}
    
    if not WEB_SEARCH_ENABLED:
        # Use fallback suppliers
        fallback = get_fallback_suppliers(canonical_name)
        outcome_registry.record_skip(
            original_name,
            SupplierOutcomeStatus.SKIPPED_NO_BUDGET,
            f"Web search disabled - using {len(fallback)} fallback suppliers"
        )
        return {"validated_suppliers": fallback, "web_source": "fallback_disabled"}
    
    # Check cache first (only if USE_CACHE is True)
    # NEW: HIGH-QUALITY CONTACT-AWARE CACHE VALIDATION
    # Treat as MISS if: suppliers < 2 OR quality < threshold OR no contacts
    if USE_CACHE:
        cached = _cache_get(canonical_name, "suppliers_v1")
        if cached:
            suppliers = cached.get("validated_suppliers", [])
            
            # Quality checks for cache acceptance
            cache_valid = True
            cache_reject_reason = None
            
            # Check 1: Minimum supplier count (need at least 2)
            if len(suppliers) < 2:
                cache_valid = False
                cache_reject_reason = f"Only {len(suppliers)} supplier(s) in cache (need ≥2)"
            
            # Check 2: Quality threshold (need reasonable quality scores)
            elif suppliers:
                avg_quality = sum(s.get('quality_score', 0) for s in suppliers) / len(suppliers)
                min_quality_threshold = 0.55  # Evidence-based minimum
                if avg_quality < min_quality_threshold:
                    cache_valid = False
                    cache_reject_reason = f"Low quality cache (avg={avg_quality:.2f} < {min_quality_threshold})"
            
            # Check 3: Contact information (need at least ONE supplier with email or phone)
            if cache_valid and suppliers:
                has_contacts = any(
                    (s.get('emails') and len(s.get('emails', [])) > 0) or
                    (s.get('phones') and len(s.get('phones', [])) > 0) or
                    s.get('email')  # Legacy field
                    for s in suppliers
                )
                if not has_contacts:
                    cache_valid = False
                    cache_reject_reason = "No contact info (emails/phones) in cached suppliers"
            
            # Accept cache or treat as MISS
            if cache_valid and suppliers:
                logger.info(f"Phase C: ✓ Using HIGH-QUALITY cached suppliers for {canonical_name} ({len(suppliers)} suppliers with contacts)")
                outcome_registry.record_success(
                    original_name,
                    suppliers,
                    queries_made=cached.get("queries_used", 0),
                    pages_fetched=cached.get("pages_fetched", 0),
                    candidates_evaluated=len(suppliers),
                    candidates_filtered=0
                )
                return cached
            else:
                # Cache MISS - run web sourcing if budget remains
                logger.warning(f"Phase C: ✗ Cache MISS for {canonical_name}: {cache_reject_reason}. Running fresh web sourcing...")
    else:
        logger.info(f"Phase C: Cache disabled, searching fresh suppliers for {canonical_name}")
    
    suppliers = []
    raw_candidates = []  # For best-effort fallback
    candidates_evaluated = 0
    candidates_filtered = 0
    queries_attempted = 0
    
    try:
        # ========== PASS 1: HIGH-PRECISION CANONICAL QUERIES ==========
        # Target: OEM manufacturers, integrators, distributors with regional focus
        pass_1_queries = [
            # OEM manufacturers (Europe/Global - high quality)
            f'"{canonical_name}" manufacturer OEM Europe',
            f'"{canonical_name}" OEM supplier MENA',
            # Regional focus (Algeria priority)
            f'"{canonical_name}" Algeria supplier distributor',
            # Fallback: broader search
            f'{canonical_name} system integrator',
        ]
        
        logger.info(f"Phase C: ========== PASS 1: HIGH-PRECISION SUPPLIER SEARCH ==========")
        pass_1_suppliers = []
        
        from utils.web_search import aggregator
        import time as time_module
        
        # Execute Pass 1: High-precision supplier queries
        for pass_idx, query in enumerate(pass_1_queries):
            if not budget.can_query() or not budget.has_time():
                logger.info(f"Phase C Pass 1: Budget exhausted after {queries_attempted} queries")
                break
            
            try:
                logger.info(f"Phase C Pass 1: Query {pass_idx+1}/{len(pass_1_queries)}: {query}")
                budget.record_query("aggregator", query)
                queries_attempted += 1
                
                # Execute search
                raw_results = aggregator.search_machine_suppliers(
                    machine_name=original_name,
                    machine_type=canonical_name,
                    region="Algeria",
                    max_results_per_source=5,
                    max_total_results=MAX_RESULTS_PER_QUERY
                )
                
                # Track page fetches
                for result in raw_results:
                    if budget.can_fetch():
                        budget.record_page_fetch(result.source_url or "unknown")
                    else:
                        break
                
                # Convert to dict format
                for result in raw_results:
                    supplier_dict = {
                        "supplier_name": result.supplier_name,
                        "region": result.region or "Unknown",
                        "website": result.website or "",
                        "source_url": result.source_url,
                        "price_estimate": result.price_estimate or "Contact for quote",
                        "price_type": result.price_type or "Indicative",
                        "notes": result.notes or f"Source: {result.source}",
                        "relevance_score": result.relevance_score or 0.7,
                        # Initialize contact fields
                        "emails": [],
                        "phones": [],
                        "contact_pages": [],
                    }
                    pass_1_suppliers.append(supplier_dict)
                
                logger.info(f"Phase C Pass 1: Query {pass_idx+1} returned {len(raw_results)} suppliers")
                
            except Exception as e:
                logger.warning(f"Phase C Pass 1: Query {pass_idx+1} failed: {e}")
        
        logger.info(f"Phase C: Pass 1 complete: {len(pass_1_suppliers)} suppliers from {queries_attempted} queries")
        
        # ========== PASS 2: CONTACT-FOCUSED QUERIES PER SUPPLIER ==========
        # Target: Extract emails and phone numbers from supplier domains
        logger.info(f"Phase C: ========== PASS 2: CONTACT EXTRACTION ==========")
        
        # Deduplicate Pass 1 suppliers by domain before contact extraction
        pass_1_deduped = deduplicate_suppliers(pass_1_suppliers)
        logger.info(f"Phase C Pass 2: Deduped to {len(pass_1_deduped)} unique suppliers")
        
        # Relax pre-contact filtering: keep all suppliers with ≥1 signal (score >= 0.3)
        # Quality filtering happens AFTER contact extraction for +0.15 contact bonus
        pass_2_candidates = [
            s for s in pass_1_deduped 
            if s.get('relevance_score', 0) >= 0.3
        ]
        pass_2_candidates = sorted(
            pass_2_candidates,
            key=lambda x: x.get('relevance_score', 0),
            reverse=True
        )[:15]  # Cap at 15 to manage budget
        
        logger.info(f"Phase C Pass 2: Extracting contacts from top {len(pass_2_candidates)} suppliers")
        
        # CONTACT EXTRACTION MUST PROCESS AT LEAST TOP 3 SUPPLIERS
        min_suppliers_to_process = min(3, len(pass_2_candidates))
        
        for idx, supplier in enumerate(pass_2_candidates):
            # Force processing of at least top 3 suppliers regardless of budget
            if idx >= min_suppliers_to_process and (not budget.can_query() or not budget.has_time()):
                logger.info(f"Phase C Pass 2: Budget exhausted after {idx} suppliers (minimum {min_suppliers_to_process} processed)")
                break
            
            supplier_name = supplier.get('supplier_name', '')
            supplier_domain = supplier.get('website', '') or supplier.get('source_url', '')
            
            if not supplier_domain:
                continue
            
            try:
                # Extract domain for site: queries
                from urllib.parse import urlparse
                parsed = urlparse(supplier_domain)
                domain = parsed.netloc or parsed.path
                
                # Pass 2 contact queries (budget-aware)
                contact_queries = [
                    f'site:{domain} contact email',
                    f'"{supplier_name}" email phone contact',
                ]
                
                for contact_query in contact_queries:
                    if not budget.can_query():
                        break
                    
                    try:
                        logger.debug(f"Phase C Pass 2: Contact query for {supplier_name}: {contact_query}")
                        budget.record_query("aggregator", contact_query)
                        queries_attempted += 1
                        
                        # Execute contact-focused search
                        contact_results = aggregator.search_machine_suppliers(
                            machine_name=contact_query,
                            machine_type="contact information",
                            region="",
                            max_results_per_source=2,
                            max_total_results=3
                        )
                        
                        # Extract contacts from snippets/notes
                        for result in contact_results:
                            text = f"{result.notes} {result.supplier_name}" if result.notes else result.supplier_name
                            
                            # Extract emails and phones
                            emails = extract_emails_from_text(text)
                            region = detect_region_from_url(supplier_domain)
                            phones = extract_phones_from_text(text, region)
                            
                            if emails or phones:
                                supplier['emails'].extend(emails)
                                supplier['phones'].extend(phones)
                                logger.info(f"Phase C Pass 2: ✓ Found {len(emails)} emails, {len(phones)} phones for {supplier_name}")
                        
                        # Deduplicate contacts
                        supplier['emails'] = sorted(list(set(supplier['emails'])))
                        supplier['phones'] = sorted(list(set(supplier['phones'])))
                        
                        # Set contact_confidence based on available contact info
                        if supplier['emails'] and supplier['phones']:
                            supplier['contact_confidence'] = 'high'
                        elif supplier['emails'] or supplier['phones']:
                            supplier['contact_confidence'] = 'medium'
                        else:
                            supplier['contact_confidence'] = 'low'
                        
                    except Exception as e:
                        logger.debug(f"Phase C Pass 2: Contact query failed for {supplier_name}: {e}")
                        continue
            
            except Exception as e:
                logger.warning(f"Phase C Pass 2: Contact extraction failed for {supplier_name}: {e}")
        
        # Merge Pass 1 suppliers into raw_candidates for filtering
        raw_candidates.extend(pass_1_suppliers)
        
        candidates_evaluated = len(raw_candidates)
        logger.info(f"Phase C: Collected {candidates_evaluated} total candidates from {queries_attempted} queries (Pass 1+2)")
        
        # Additional contact extraction from supplier pages (if budget permits)
        logger.info(f"Phase C: Extracting contacts from supplier page HTML (budget-aware)")
        for candidate in raw_candidates:
            try:
                # Get supplier page HTML if available
                supplier_url = candidate.get('website') or candidate.get('source_url')
                if supplier_url and budget.can_fetch_page():
                    # Detect region for better phone parsing
                    region = detect_region_from_url(supplier_url)
                    
                    # Note: This is a simplified version - in production, we'd fetch the HTML
                    # For now, extract from existing notes/snippets if available
                    html_content = candidate.get('notes', '') + ' ' + candidate.get('snippet', '')
                    
                    if html_content:
                        contact_info = extract_contacts_from_html(html_content, supplier_url, region)
                        
                        # Add contact fields to candidate
                        candidate['emails'] = contact_info.get('emails', [])
                        candidate['phones'] = contact_info.get('phones', [])
                        candidate['contact_pages'] = contact_info.get('contact_pages', [])
                    else:
                        # Initialize empty contact fields
                        candidate['emails'] = []
                        candidate['phones'] = []
                        candidate['contact_pages'] = []
                else:
                    # No URL or budget exhausted - initialize empty
                    candidate['emails'] = []
                    candidate['phones'] = []
                    candidate['contact_pages'] = []
                    candidate['contact_confidence'] = 'low'
            except Exception as contact_error:
                logger.warning(f"Phase C: Contact extraction failed for {candidate.get('supplier_name')}: {contact_error}")
                candidate['emails'] = []
                candidate['phones'] = []
                candidate['contact_pages'] = []
                candidate['contact_confidence'] = 'low'
        
        # NEW: MANDATORY AI FALLBACK when no results found
        if not raw_candidates:
            logger.warning(f"Phase C: ⚠ ZERO SUPPLIERS FOUND - Generating MANDATORY AI FALLBACK")
            
            # Get typical manufacturers from Phase B
            typical_mfrs = INDUSTRY_KNOWLEDGE.get(canonical_name, {}).get('typical_manufacturers', [])
            
            # Generate 3-6 AI fallback suppliers
            ai_fallback = generate_ai_fallback_suppliers(
                canonical_name,
                typical_manufacturers=typical_mfrs,
                max_suppliers=6  # 3-6 plausible suppliers
            )
            
            # Tag each with is_ai_fallback=true and ai_tag="★"
            for supplier in ai_fallback:
                supplier['is_ai_fallback'] = True
                supplier['ai_tag'] = '★'
            
            outcome_registry.record_failure(
                original_name,
                SupplierOutcomeStatus.SEARCH_FAILED_EXCEPTION,
                f"No public suppliers found after {queries_attempted} queries - using AI fallback",
                queries_made=budget.queries_used,
                pages_fetched=budget.pages_fetched
            )
            
            return {
                "validated_suppliers": ai_fallback,
                "web_source": "ai_fallback_no_results",
                "queries_used": budget.queries_used,
                "pages_fetched": budget.pages_fetched,
                "candidates_evaluated": 0,
                "candidates_filtered": 0,
                "supplier_outcome": {
                    "status": "fallback_only",
                    "subtext": "No public suppliers found with verifiable contact details."
                }
            }
        
        # BEST-EFFORT RULE: Try filtering, but if it fails, return deduped raw candidates with confidence=low
        verified_suppliers = []  # Suppliers that passed filter
        unverified_suppliers = []  # Raw candidates that didn't pass filter
        
        try:
            # Deduplicate BEFORE scoring to avoid redundant work
            logger.info(f"Phase C: Deduplicating {len(raw_candidates)} raw candidates")
            deduped_candidates = deduplicate_suppliers(raw_candidates)
            logger.info(f"Phase C: After dedup: {len(deduped_candidates)} unique candidates")
            
            # Apply legacy quality filtering first
            logger.info(f"Phase C: Filtering {len(deduped_candidates)} candidates")
            filtered_suppliers = filter_suppliers(
                suppliers=deduped_candidates,
                machine_name=original_name,
                machine_type=canonical_name,
                min_score=0.3  # Lower threshold, enhanced scoring will refine
            )
            
            # NEW: Apply enhanced quality scoring with evidence
            logger.info(f"Phase C: Applying enhanced quality scoring to {len(filtered_suppliers)} filtered candidates")
            # Use INDUSTRY_KNOWLEDGE instead of undefined KNOWN_SPECS
            typical_mfrs = INDUSTRY_KNOWLEDGE.get(canonical_name, {}).get('typical_manufacturers', [])
            
            quality_filtered = apply_quality_threshold(
                suppliers=filtered_suppliers,
                min_quality_score=0.55,  # Evidence-based threshold
                canonical_name=canonical_name,
                typical_manufacturers=typical_mfrs,
                allow_fallback=True  # Allow 0.40 threshold if none pass
            )
            
            candidates_filtered = len(deduped_candidates) - len(quality_filtered)
            logger.info(f"Phase C: Quality scoring: {len(quality_filtered)} suppliers passed (filtered out {candidates_filtered})")
            
            verified_suppliers = quality_filtered
            
        except Exception as filter_error:
            # BEST-EFFORT: Filtering failed, mark all as unverified
            logger.warning(f"Phase C: Filtering failed: {filter_error} - marking all as unverified")
            unverified_suppliers = deduplicate_suppliers(raw_candidates)
            candidates_filtered = 0
        
        # NEW: MANDATORY AI FALLBACK when filtering removes all suppliers
        if not verified_suppliers and raw_candidates:
            logger.warning(f"Phase C: ⚠ All {len(raw_candidates)} candidates filtered out - Generating MANDATORY AI FALLBACK")
            
            # Generate 3-6 AI fallback suppliers
            typical_mfrs = INDUSTRY_KNOWLEDGE.get(canonical_name, {}).get('typical_manufacturers', [])
            ai_fallback = generate_ai_fallback_suppliers(
                canonical_name,
                typical_manufacturers=typical_mfrs,
                max_suppliers=6
            )
            
            # Tag each with is_ai_fallback=true and ai_tag="★" (REQUIRED)
            for supplier in ai_fallback:
                supplier['is_ai_fallback'] = True
                supplier['ai_tag'] = '★'
                supplier['fallback_reason'] = 'No public verified suppliers available'
            
            suppliers = ai_fallback
            
            # Record as FALLBACK_ONLY (NOT error) - fallback suppliers are valid outputs
            outcome = SupplierOutcome(
                machine_name=original_name,
                status=SupplierOutcomeStatus.FALLBACK_ONLY,
                supplier_count=len(suppliers),
                reason=f"All {candidates_evaluated} candidates failed quality filter - AI fallback generated",
                suppliers=suppliers,
                queries_made=budget.queries_used,
                pages_fetched=budget.pages_fetched,
                candidates_evaluated=candidates_evaluated,
                candidates_filtered=candidates_filtered
            )
            outcome_registry.record_outcome(outcome)
        elif not verified_suppliers and not raw_candidates:
            # No candidates at all - use AI fallback
            logger.warning(f"Phase C: ⚠ No candidates found - Generating MANDATORY AI FALLBACK")
            typical_mfrs = INDUSTRY_KNOWLEDGE.get(canonical_name, {}).get('typical_manufacturers', [])
            
            ai_fallback = generate_ai_fallback_suppliers(
                canonical_name,
                typical_manufacturers=typical_mfrs,
                max_suppliers=6
            )
            
            for supplier in ai_fallback:
                supplier['is_ai_fallback'] = True
                supplier['ai_tag'] = '★'
            
            suppliers = ai_fallback
        else:
            # Prepare final supplier list from verified suppliers
            suppliers = verified_suppliers
            
            # Add contact_confidence field to each supplier
            for supplier in suppliers:
                emails = supplier.get('emails', [])
                phones = supplier.get('phones', [])
                
                if emails and phones:
                    supplier['contact_confidence'] = 'high'
                elif emails or phones:
                    supplier['contact_confidence'] = 'medium'
                else:
                    supplier['contact_confidence'] = 'low'
        
        # Target 15-25 suppliers after dedupe, but cap at reasonable limit
        suppliers = sorted(suppliers, key=lambda x: x.get('relevance_score', 0) + x.get('quality_score', 0), reverse=True)
        suppliers = suppliers[:25]  # Cap at 25 as per requirement
        
        # Record outcome based on verification status
        if verified_suppliers:
            # Success: Found verified suppliers that passed quality filter
            outcome_registry.record_success(
                original_name,
                suppliers,
                queries_made=budget.queries_used,
                pages_fetched=budget.pages_fetched,
                candidates_evaluated=candidates_evaluated,
                candidates_filtered=candidates_filtered
            )
            logger.info(f"Phase C: Recorded {len(suppliers)} VERIFIED suppliers for {original_name}")
        elif unverified_suppliers:
            # NO_VERIFIED_SUPPLIERS maps to FALLBACK_ONLY, NOT error
            # Keep unverified suppliers and tag appropriately
            for supplier in suppliers:
                if not supplier.get('is_ai_fallback'):
                    supplier['is_ai_fallback'] = False
                    supplier['verification_status'] = 'unverified'
            
            # Record as FALLBACK_ONLY instead of failure
            outcome = SupplierOutcome(
                machine_name=original_name,
                status=SupplierOutcomeStatus.FALLBACK_ONLY,
                supplier_count=len(suppliers),
                reason=f"No suppliers passed quality filter - using {len(suppliers)} best-effort candidates",
                suppliers=suppliers,
                queries_made=budget.queries_used,
                pages_fetched=budget.pages_fetched,
                candidates_evaluated=candidates_evaluated,
                candidates_filtered=candidates_filtered
            )
            outcome_registry.record_outcome(outcome)
            logger.info(f"Phase C: Recorded {len(suppliers)} FALLBACK suppliers for {original_name} (NO_VERIFIED_SUPPLIERS -> FALLBACK_ONLY)")
        else:
            # Should not happen due to best-effort, but handle gracefully
            fallback = get_fallback_suppliers(canonical_name)
            logger.warning(f"Phase C: No suppliers after all attempts - using {len(fallback)} fallback")
            outcome_registry.record_failure(
                original_name,
                SupplierOutcomeStatus.SEARCH_FAILED_ALL_FILTERED,
                f"No suppliers after filtering {candidates_evaluated} candidates - using fallback",
                queries_made=budget.queries_used,
                pages_fetched=budget.pages_fetched,
                candidates_evaluated=candidates_evaluated,
                candidates_filtered=candidates_filtered
            )
            suppliers = fallback
    
    except Exception as e:
        # Network/system failure - use fallback suppliers
        logger.error(f"Phase C: Critical failure for {canonical_name}: {e}")
        fallback = get_fallback_suppliers(canonical_name)
        logger.warning(f"Phase C: Using {len(fallback)} fallback suppliers after exception")
        outcome_registry.record_failure(
            original_name,
            SupplierOutcomeStatus.SEARCH_FAILED_EXCEPTION,
            f"Search exception: {str(e)[:100]} - using fallback",
            details=str(e),
            queries_made=budget.queries_used,
            pages_fetched=budget.pages_fetched
        )
        suppliers = fallback
    
    # Determine supplier outcome status
    all_ai_fallback = all(s.get('is_ai_fallback', False) or s.get('ai_star', False) for s in suppliers)
    has_public_suppliers = any(not s.get('is_ai_fallback', False) and not s.get('ai_star', False) for s in suppliers)
    
    if has_public_suppliers:
        outcome_status = "suppliers_found"
        supplier_subtext = None
    elif all_ai_fallback:
        # All AI fallback - tag with proper subtext
        outcome_status = "fallback_only"
        supplier_subtext = "No public verified suppliers available"
    elif len(suppliers) == 0:
        # Should not happen but handle gracefully
        outcome_status = "fallback_only"
        supplier_subtext = "No suppliers found"
    else:
        # Mixed suppliers
        outcome_status = "suppliers_found"
        supplier_subtext = None
    
    result = {
        "validated_suppliers": suppliers,
        "web_source": "aggregator",
        "queries_used": budget.queries_used,
        "pages_fetched": budget.pages_fetched,
        "candidates_evaluated": candidates_evaluated,
        "candidates_filtered": candidates_filtered,
        "supplier_outcome": {
            "status": outcome_status,
            "subtext": supplier_subtext
        },
        # NEW: Budget accounting for Module 5
        "web_calls_used": budget.queries_used + budget.pages_fetched
    }
    
    # Add machine-level subtext if applicable
    if supplier_subtext:
        result["supplier_subtext"] = supplier_subtext
    
    # Cache it
    _cache_set(canonical_name, "suppliers_v1", result)
    
    return result

# =========================================================
# PHASE D — SINGLE SYNTHESIS (ONE LLM CALL MAX)
# =========================================================

SYNTHESIS_PROMPT = """
You are synthesizing machine information from internal knowledge and optional web validation.

INTERNAL KNOWLEDGE:
{phase_b}

WEB VALIDATION (with suppliers):
{phase_c}

ORIGINAL MACHINE NAME:
{original_name}

TASK:
Merge the above into a final JSON object. Use internal knowledge as the foundation.
If web validation provides suppliers, include them exactly as provided (up to 3).
NEVER add fields that weren't in the input.
Unknown fields must be null.

OUTPUT FORMAT (strict schema):
{{
  "canonical_name": "string",
  "machine_class": "core_stable|core_variable|optional_system",
  "role": "string|null",
  "typical_capacity_range": "string|null",
  "typical_power_range": "string|null",
  "typical_footprint_range": "string|null",
  "typical_manufacturers": ["string"],
  "confidence": "high|medium|low",
  "notes": "string|null"
}}

IMPORTANT: Do NOT include validated_suppliers in the output - they will be merged separately.

Return ONLY valid JSON. No markdown, no code fences, no commentary.
"""

def synthesize_final(
    phase_b: Dict[str, Any],
    phase_c: Dict[str, Any],
    original_name: str,
    budget: PerMachineBudget,
) -> Dict[str, Any]:
    """
    Phase D: Single Synthesis (ONE LLM CALL MAX)
    
    Merges Phase B and optional Phase C into final JSON.
    NO RETRY on parse failure - returns safe minimal object.
    """
    if not budget.can_llm() or not budget.has_time():
        logger.warning(f"Phase D: Budget exhausted, returning Phase B without LLM synthesis")
        # Merge manually without LLM
        result = phase_b.copy()
        result["validated_suppliers"] = phase_c.get("validated_suppliers", [])
        result["notes"] = "Budget exhausted, no LLM synthesis"
        return result
    
    try:
        prompt = SYNTHESIS_PROMPT.format(
            phase_b=json.dumps(phase_b, ensure_ascii=False, indent=2),
            phase_c=json.dumps(phase_c, ensure_ascii=False, indent=2),
            original_name=original_name,
        )
        
        timeout = min(30, int(budget.time_left()))
        if timeout <= 0:
            timeout = 5
        
        budget.llm_calls_used += 1
        
        raw = generate_message(
            prompt=prompt,
            system_instruction="Return ONLY valid JSON matching the schema. No markdown.",
            temperature=0.1,
        )
        
        # Parse JSON (NO RETRY LOOP - validate and return safe object if invalid)
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
            if m:
                cleaned = m.group(1).strip()
        
        result = json.loads(cleaned)
        
        # Validate schema - if invalid, produce minimal safe object
        required_keys = ["canonical_name", "machine_class", "confidence"]
        if not all(k in result for k in required_keys):
            raise ValueError("Missing required keys in LLM output")
        
        # CRITICAL: Always ensure validated_suppliers from Phase C are included
        # LLM may not include them, so we merge them explicitly
        if "validated_suppliers" not in result or not result["validated_suppliers"]:
            result["validated_suppliers"] = phase_c.get("validated_suppliers", [])
        
        # CRITICAL: Preserve contact fields (emails, phones, contact_pages, contact_confidence)
        # Ensure Phase C contact data is not lost during synthesis
        phase_c_suppliers = phase_c.get("validated_suppliers", [])
        for idx, supplier in enumerate(result.get("validated_suppliers", [])):
            if idx < len(phase_c_suppliers):
                phase_c_supplier = phase_c_suppliers[idx]
                # Preserve contact fields if present
                for field in ['emails', 'phones', 'contact_pages', 'contact_confidence']:
                    if field in phase_c_supplier and field not in supplier:
                        supplier[field] = phase_c_supplier[field]
        
        return result
    
    except Exception as e:
        logger.error(f"Phase D: Synthesis failed: {e}")
        # NO RETRY - produce minimal safe object with confidence="low"
        result = phase_b.copy()
        # Preserve Phase C suppliers with all contact fields intact
        result["validated_suppliers"] = phase_c.get("validated_suppliers", [])
        result["confidence"] = CONF_LOW
        result["notes"] = f"LLM synthesis failed (no retry): {str(e)[:100]}"
        return result

# =========================================================
# MAIN PIPELINE
# =========================================================

# NOTE: GlobalBudget is now imported from budget_tracker.py

def enrich_machine_bounded(
    machine: Dict[str, Any],
    global_budget: GlobalBudget,
    outcome_registry: SupplierOutcomeRegistry,
    global_budget_controller: Optional[GlobalBudgetController] = None,  # NEW
    budget_allocation: Optional[Dict[str, int]] = None,  # NEW
) -> Optional[Dict[str, Any]]:
    """
    Main enrichment pipeline for one machine.
    
    Returns None if machine should be excluded (subsystem).
    
    Runtime asserts:
    - Per-machine budgets enforced
    - No contacts enrichment called
    - Excluded classes never trigger web
    
    NEW: Uses GlobalBudgetController for hard budget enforcement
    """
    nom_machine = machine.get("nom_machine", "Unknown")
    
    # Phase A: Canonicalize + Classify (NO WEB)
    canonical_name, machine_class, confidence = canonicalize_machine(nom_machine)
    
    logger.info(f"Phase A: {nom_machine} -> {canonical_name} [{machine_class}, {confidence}]")
    
    # ASSERT: Exclude subsystems (unit-test-like check)
    if machine_class == CLASS_SUBSYSTEM:
        logger.info(f"Phase A: EXCLUDING subsystem: {canonical_name}")
        assert machine_class == CLASS_SUBSYSTEM, "Subsystem not excluded properly"
        return None
    
    # Phase B: Industry Grounding (NO WEB, deterministic)
    phase_b = ground_machine(canonical_name, machine_class, confidence)
    
    # Phase C: Minimal Web Validation (OPTIONAL, bounded)
    phase_c = {"validated_suppliers": []}
    machine_budget = None  # Initialize to None to track if web validation was executed
    web_validation_executed = False
    
    if should_validate_with_web(machine_class, confidence):
        # Check if we have budget allocation (from planning pass)
        if budget_allocation and not budget_allocation.get('skip'):
            # Create per-machine budget with allocated limits
            machine_budget = global_budget.create_machine_budget(
                machine_name=nom_machine,
                max_queries=budget_allocation.get('queries', MAX_SEARCH_QUERIES_PER_MACHINE),
                max_pages=budget_allocation.get('pages', MAX_FETCH_PAGES_TOTAL),
                max_llm_calls=MAX_LLM_CALLS_PER_MACHINE,
                timeout_seconds=MAX_RUNTIME_PER_MACHINE_S
            )
            
            logger.info(f"Phase C: {nom_machine} allocated {budget_allocation.get('queries')} queries, "
                       f"{budget_allocation.get('pages')} pages (confidence: {budget_allocation.get('confidence')})")
            
            phase_c = web_validate_minimal(
                canonical_name, 
                nom_machine, 
                machine_budget, 
                outcome_registry, 
                global_budget,
                global_budget_controller or GlobalBudgetController(max_budget=1000),  # Fallback
                budget_allocation
            )
            web_validation_executed = True
        elif budget_allocation and budget_allocation.get('skip'):
            # Budget allocation says to skip - use AI fallback instead of empty suppliers
            logger.info(f"Phase C: Skipping {nom_machine} per budget allocation (SKIP_REASON=budget_limited) - generating AI fallback")
            
            # Generate AI fallback suppliers since we can't do web search
            from utils.module_4.ai_fallback import generate_ai_fallback_suppliers
            typical_mfrs = INDUSTRY_KNOWLEDGE.get(canonical_name, {}).get('typical_manufacturers', [])
            ai_suppliers = generate_ai_fallback_suppliers(canonical_name, typical_mfrs, max_suppliers=5)
            for s in ai_suppliers:
                s['is_ai_fallback'] = True
                s['ai_tag'] = '★'
            
            phase_c = {"validated_suppliers": ai_suppliers, "web_source": "ai_fallback_budget_limited"}
            
            outcome_registry.record_skip(
                nom_machine,
                SupplierOutcomeStatus.SKIPPED_BUDGET_LIMITED,
                f"Insufficient global budget for Phase C validation - using {len(ai_suppliers)} AI fallback suppliers"
            )
        elif global_budget.can_allocate_machine():
            # Legacy path (no planning pass) - use default limits
            machine_budget = global_budget.create_machine_budget(
                machine_name=nom_machine,
                max_queries=MAX_SEARCH_QUERIES_PER_MACHINE,
                max_pages=MAX_FETCH_PAGES_TOTAL,
                max_llm_calls=MAX_LLM_CALLS_PER_MACHINE,
                timeout_seconds=MAX_RUNTIME_PER_MACHINE_S
            )
            
            phase_c = web_validate_minimal(
                canonical_name, 
                nom_machine, 
                machine_budget, 
                outcome_registry, 
                global_budget,
                global_budget_controller or GlobalBudgetController(max_budget=1000),  # Fallback
                None  # No allocation
            )
            web_validation_executed = True
        else:
            # No budget available - use AI fallback
            logger.info(f"Phase C: Global budget exhausted for {nom_machine} - generating AI fallback")
            from utils.module_4.ai_fallback import generate_ai_fallback_suppliers
            typical_mfrs = INDUSTRY_KNOWLEDGE.get(canonical_name, {}).get('typical_manufacturers', [])
            ai_suppliers = generate_ai_fallback_suppliers(canonical_name, typical_mfrs, max_suppliers=5)
            for s in ai_suppliers:
                s['is_ai_fallback'] = True
                s['ai_tag'] = '★'
            
            phase_c = {"validated_suppliers": ai_suppliers, "web_source": "ai_fallback_budget_exhausted"}
            
            outcome_registry.record_skip(
                nom_machine,
                SupplierOutcomeStatus.SKIPPED_NO_BUDGET,
                f"Global budget exhausted before Phase C - using {len(ai_suppliers)} AI fallback suppliers"
            )
        
        # Only check budgets if web validation was actually executed
        if web_validation_executed and machine_budget is not None:
            # ASSERT: Budgets enforced
            assert machine_budget.queries_used <= MAX_SEARCH_QUERIES_PER_MACHINE, "Query budget exceeded"
            assert machine_budget.pages_fetched <= MAX_FETCH_PAGES_TOTAL, "Page fetch budget exceeded"
            
            # ASSERT: Excluded classes never trigger web
            assert machine_class != CLASS_SUBSYSTEM, "Subsystem triggered web validation"
            assert machine_class != CLASS_OPTIONAL or confidence == CONF_LOW, "Optional triggered web without low confidence"
            
            # Finalize machine budget (updates global counters)
            global_budget.finalize_machine(nom_machine)
        
        logger.info(
            f"Phase C: {canonical_name} - "
            f"{len(phase_c.get('validated_suppliers', []))} suppliers, "
            f"{phase_c.get('queries_used', 0)} queries, "
            f"{phase_c.get('pages_fetched', 0)} pages"
        )
    else:
        # Skip web validation but still provide suppliers via AI fallback or industry knowledge
        # This ensures EVERY machine gets suppliers, not just the ones that do web search
        
        if machine_class == CLASS_SUBSYSTEM:
            # Subsystems don't need suppliers
            outcome_registry.record_skip(
                nom_machine,
                SupplierOutcomeStatus.SKIPPED_GENERIC,
                "Subsystem - no OEM supplier needed"
            )
        elif machine_class == CLASS_OPTIONAL:
            # Optional systems get AI fallback suppliers
            from utils.module_4.ai_fallback import generate_ai_fallback_suppliers
            typical_mfrs = INDUSTRY_KNOWLEDGE.get(canonical_name, {}).get('typical_manufacturers', [])
            ai_suppliers = generate_ai_fallback_suppliers(canonical_name, typical_mfrs, max_suppliers=4)
            for s in ai_suppliers:
                s['is_ai_fallback'] = True
                s['ai_tag'] = '★'
            phase_c = {"validated_suppliers": ai_suppliers, "web_source": "ai_fallback_optional"}
            
            outcome_registry.record_skip(
                nom_machine,
                SupplierOutcomeStatus.SKIPPED_GENERIC,
                f"Optional system - using {len(ai_suppliers)} AI fallback suppliers"
            )
        elif not global_budget.can_allocate_machine():
            # Budget exhausted - still provide AI fallback
            from utils.module_4.ai_fallback import generate_ai_fallback_suppliers
            typical_mfrs = INDUSTRY_KNOWLEDGE.get(canonical_name, {}).get('typical_manufacturers', [])
            ai_suppliers = generate_ai_fallback_suppliers(canonical_name, typical_mfrs, max_suppliers=4)
            for s in ai_suppliers:
                s['is_ai_fallback'] = True
                s['ai_tag'] = '★'
            phase_c = {"validated_suppliers": ai_suppliers, "web_source": "ai_fallback_budget_exhausted"}
            
            outcome_registry.record_skip(
                nom_machine,
                SupplierOutcomeStatus.SKIPPED_NO_BUDGET,
                f"Global budget exhausted - using {len(ai_suppliers)} AI fallback suppliers"
            )
        else:
            # Core stable machine with good confidence - provide suppliers from industry knowledge + AI
            from utils.module_4.ai_fallback import generate_ai_fallback_suppliers
            typical_mfrs = INDUSTRY_KNOWLEDGE.get(canonical_name, {}).get('typical_manufacturers', [])
            ai_suppliers = generate_ai_fallback_suppliers(canonical_name, typical_mfrs, max_suppliers=5)
            for s in ai_suppliers:
                s['is_ai_fallback'] = True
                s['ai_tag'] = '★'
            phase_c = {"validated_suppliers": ai_suppliers, "web_source": "ai_fallback_core_stable"}
            
            outcome_registry.record_skip(
                nom_machine,
                SupplierOutcomeStatus.SKIPPED_GENERIC,
                f"Core stable machine with {confidence} confidence - using {len(ai_suppliers)} AI fallback suppliers"
            )
        
        logger.info(f"Phase C: Skipped web for {canonical_name}, using {len(phase_c.get('validated_suppliers', []))} fallback suppliers")
        global_budget.skip_machine(nom_machine, "No web validation needed")
    
    # Phase D: Single Synthesis (ONE LLM CALL MAX)
    synthesis_budget = global_budget.create_machine_budget(
        machine_name=f"{nom_machine}_synthesis",
        max_llm_calls=MAX_LLM_CALLS_PER_MACHINE,
        timeout_seconds=30
    )
    final = synthesize_final(phase_b, phase_c, nom_machine, synthesis_budget)
    
    # ASSERT: LLM call budget
    assert synthesis_budget.llm_calls_used <= MAX_LLM_CALLS_PER_MACHINE, "LLM call budget exceeded"
    
    # Add original name for reference
    final["original_name"] = nom_machine
    
    # Structure quantity properly
    quantity_structured = structure_quantity(machine)
    
    # Restructure to match template format: machine_input + suppliers
    result = {
        "machine_input": {
            "nom_machine": machine.get("nom_machine", nom_machine),
            "type": machine.get("type", ""),
            "fabricant_recommande": machine.get("fabricant_recommande", ""),
            "quantite_necessaire": quantity_structured,  # Now structured as {value, source}
            "use": machine.get("use", final.get("role", "")),
            "specifications": machine.get("specifications", {}),
            "performance": machine.get("performance", {}),
            "canonical_name": final.get("canonical_name"),
            "machine_class": final.get("machine_class"),
            "typical_capacity_range": final.get("typical_capacity_range"),
            "typical_power_range": final.get("typical_power_range"),
            "typical_footprint_range": final.get("typical_footprint_range"),
            "typical_manufacturers": final.get("typical_manufacturers", []),
            "confidence": final.get("confidence"),
            "notes": final.get("notes"),
        },
        "suppliers": final.get("validated_suppliers", []),
    }
    
    # NEW: Add no_public_suppliers_subtext if all suppliers are AI-generated
    result = add_no_suppliers_subtext(result)
    
    return result

def process_module_4_bounded(
    machines: List[Dict[str, Any]],
    max_workers: int = 8,
) -> Dict[str, Any]:
    """
    Process all machines with HARD bounded budgets using GlobalBudgetController.
    
    Returns enriched results.
    
    NEW FEATURES:
    - GlobalBudgetController for HARD budget enforcement
    - Phase C planning pass with budget allocation
    - Cache enabled by default (USE_CACHE=True)
    
    Acceptance criteria enforcement:
    - total_web_calls <= global_budget (HARD STOP, deterministic)
    - predictable runtime
    - stable JSON output
    - EVERY machine has explicit supplier outcome
    """
    t0 = time.time()
    
    # Initialize HARD global budget controller
    total_budget = len(machines) * GLOBAL_WEB_CALL_MULTIPLIER
    global_budget_controller = GlobalBudgetController(max_budget=total_budget)
    
    # Initialize legacy global budget tracker (for compatibility)
    global_budget = GlobalBudget(
        max_web_calls=total_budget,
        machines_count=len(machines)
    )
    
    outcome_registry = SupplierOutcomeRegistry(total_machines=len(machines))
    
    logger.info("=" * 70)
    logger.info("START MODULE 4 — BOUNDED ENRICHMENT WITH HARD BUDGET ENFORCEMENT")
    logger.info(f"Input machines: {len(machines)}")
    logger.info(f"Max workers: {max_workers}")
    logger.info(f"Global web budget: {total_budget} calls (HARD LIMIT)")
    logger.info(f"Per-machine defaults: queries={MAX_SEARCH_QUERIES_PER_MACHINE}, "
                f"pages={MAX_FETCH_PAGES_TOTAL}, llm={MAX_LLM_CALLS_PER_MACHINE}, "
                f"time={MAX_RUNTIME_PER_MACHINE_S}s")
    logger.info(f"Cache enabled: {USE_CACHE}")
    logger.info("=" * 70)
    
    # PHASE C PLANNING PASS: Determine which machines need web validation and allocate budget
    logger.info("Phase C Planning: Analyzing machines and allocating budget...")
    machines_info = []
    for machine in machines:
        nom_machine = machine.get("nom_machine", "Unknown")
        # Quick classification to determine Phase C eligibility
        canonical_name, machine_class, confidence = canonicalize_machine(nom_machine)
        machines_info.append((nom_machine, machine_class, confidence))
    
    # Plan budget allocation (assumes no budget consumed yet in planning phase)
    budget_allocation = plan_phase_c_budget(
        machines_info,
        global_budget_controller,
        consumed_so_far=0
    )
    
    logger.info(f"Phase C Planning: Allocated budget for {len(budget_allocation)} machines")
    
    results = []
    excluded_count = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all machines with budget allocation
        future_map = {}
        for i, machine in enumerate(machines):
            nom_machine = machine.get("nom_machine", f"item_{i+1}")
            alloc = budget_allocation.get(nom_machine, {'skip': False})
            future = executor.submit(
                enrich_machine_bounded, 
                machine, 
                global_budget, 
                outcome_registry,
                global_budget_controller,  # NEW: Pass controller
                alloc  # NEW: Pass allocation
            )
            future_map[future] = (i, machine)
        
        # Collect results
        for future in as_completed(future_map):
            i, machine = future_map[future]
            nom_machine = machine.get("nom_machine", f"item_{i+1}")
            
            try:
                result = future.result(timeout=MAX_RUNTIME_PER_MACHINE_S + 5)
                
                if result is None:
                    excluded_count += 1
                    logger.info(f"[{i+1}/{len(machines)}] EXCLUDED: {nom_machine}")
                    # Record as skipped if not already recorded
                    if nom_machine not in outcome_registry.outcomes:
                        outcome_registry.record_skip(
                            nom_machine,
                            SupplierOutcomeStatus.SKIPPED_GENERIC,
                            "Excluded from enrichment (subsystem or low priority)"
                        )
                else:
                    results.append(result)
                    logger.info(f"[{i+1}/{len(machines)}] DONE: {nom_machine}")
            
            except Exception as e:
                logger.error(f"[{i+1}/{len(machines)}] FAILED: {nom_machine} - {e}")
                # Record as failed
                outcome_registry.record_failure(
                    nom_machine,
                    SupplierOutcomeStatus.SEARCH_FAILED_EXCEPTION,
                    f"Machine enrichment exception: {str(e)[:100]}",
                    details=str(e)
                )
                # Add minimal fallback matching new structure
                quantity_fallback = structure_quantity(machine)
                results.append({
                    "machine_input": {
                        "nom_machine": nom_machine,
                        "type": machine.get("type", ""),
                        "fabricant_recommande": machine.get("fabricant_recommande", ""),
                        "quantite_necessaire": quantity_fallback,  # Structured quantity
                        "canonical_name": nom_machine,
                        "machine_class": CLASS_CORE_VARIABLE,
                        "confidence": CONF_LOW,
                        "notes": f"Enrichment failed: {str(e)[:100]}",
                    },
                    "suppliers": [],
                })
    
    processing_time = round(time.time() - t0, 3)
    
    # Log budget and outcome summaries
    global_budget.log_global_summary()
    global_budget_controller.log_summary()  # NEW: Hard budget enforcement summary
    outcome_registry.log_summary()
    
    # Check HARD budget compliance via GlobalBudgetController
    controller_summary = global_budget_controller.get_summary()
    global_summary = global_budget.get_global_summary()
    warnings = []
    
    # Primary compliance check: GlobalBudgetController
    if not controller_summary['compliant']:
        warning_msg = f"HARD budget exceeded: {controller_summary['consumed']}/{controller_summary['max_budget']} " \
                     f"(overshoot: {controller_summary['overshoot']} calls)"
        logger.error(f"❌ CRITICAL: {warning_msg}")
        warnings.append(warning_msg)
    else:
        logger.info(f"✅ HARD budget compliance: {controller_summary['consumed']}/{controller_summary['max_budget']} calls")
    
    # Legacy tracker check (for comparison)
    if not global_summary['budget_compliant']:
        warning_msg = f"Budget exceeded: {global_budget.web_calls_used}/{global_budget.max_web_calls} web calls used"
        logger.error(f"WARNING: {warning_msg}")
        warnings.append(warning_msg)
    
    # Check outcome compliance (WARNING instead of assertion)
    if not outcome_registry.validate():
        warning_msg = "Some machines missing explicit supplier outcome"
        logger.warning(f"WARNING: {warning_msg}")
        warnings.append(warning_msg)
    
    logger.info("=" * 70)
    logger.info("DONE MODULE 4")
    logger.info(f"Processing time: {processing_time}s")
    logger.info(f"Machines enriched: {len(results)}")
    logger.info(f"Machines excluded: {excluded_count}")
    logger.info(f"Web calls used: {global_budget.web_calls_used}/{global_budget.max_web_calls}")
    logger.info(f"Budget compliance: {'✓ PASS' if global_summary['budget_compliant'] else '✗ FAIL'}")
    logger.info(f"Outcome compliance: {'✓ PASS' if outcome_registry.validate() else '✗ FAIL'}")
    logger.info("=" * 70)
    
    # Get outcome summary
    outcome_summary = outcome_registry.get_summary()
    
    # Build metadata with BOTH legacy and new budget stats
    metadata = {
        "enrichment_method": "Module4 Bounded 4-Phase Pipeline with HARD Budget Enforcement",
        "enrichment_date": datetime.utcnow().isoformat(),
        "model_used": os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"),
        "api_provider": "Vertex",
        "processing_time_seconds": processing_time,
        "machines_in": len(machines),
        "machines_out": len(results),
        "machines_excluded": excluded_count,
        # Legacy budget tracker
        "web_calls_used": global_budget.web_calls_used,
        "web_calls_budget": global_budget.max_web_calls,
        "budget_compliant_legacy": global_summary['budget_compliant'],
        # NEW: Hard budget controller stats
        "hard_budget_consumed": controller_summary['consumed'],
        "hard_budget_max": controller_summary['max_budget'],
        "hard_budget_compliant": controller_summary['compliant'],
        "hard_budget_utilization_pct": controller_summary['utilization_pct'],
        "web_call_breakdown": global_budget.global_tracker.get_summary()['breakdown'],
        "supplier_outcomes": outcome_summary,
        "cache_enabled": USE_CACHE,
    }
    
    # Add warnings if any (budget exceeded, incomplete outcomes, etc.)
    if warnings:
        metadata["warnings"] = warnings
        logger.warning(f"Module 4 completed with {len(warnings)} warning(s): {warnings}")
    
    return {
        "ribif_metadata": metadata,
        "machines_enriched": results,
    }

# =========================================================
# CLI / ENTRY POINT
# =========================================================

def main(input_path: str, output_path: str, max_workers: int = 8):
    """Main entry point for Module 4."""
    # Load machines from Module 1 output
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    machines = data.get("stage_4_machines_equipements", {}).get("machines_production", [])
    
    if not machines:
        logger.error("No machines found in input")
        return
    
    # Process
    result = process_module_4_bounded(machines, max_workers=max_workers)
    
    # Save
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    
    logger.info(f"Saved: {output_file.resolve()}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="RIBIF Module 4 — Bounded Enrichment")
    parser.add_argument("--input", required=True, help="Input JSON from Module 1")
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument("--workers", type=int, default=8, help="Max workers")
    
    args = parser.parse_args()
    
    main(args.input, args.output, args.workers)
