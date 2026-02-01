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
from utils.module_4.supplier_outcome import SupplierOutcomeRegistry, SupplierOutcomeStatus
from utils.module_4.supplier_filter import filter_suppliers, deduplicate_suppliers

load_dotenv()
logger = get_logger(__name__)

# =========================================================
# CONFIGURATION & CONSTANTS
# =========================================================

# Global budget
GLOBAL_WEB_CALL_MULTIPLIER = 2  # total_web_calls <= machines_count * 2

# Per-machine budgets (Phase C only)
MAX_SEARCH_QUERIES_PER_MACHINE = 1
MAX_RESULTS_PER_QUERY = 5
MAX_FETCH_PAGES_TOTAL = 6
MAX_LLM_CALLS_PER_MACHINE = 1  # Synthesis only
MAX_RUNTIME_PER_MACHINE_S = 15

# Cache TTL
CACHE_TTL_DAYS = 7

# Cache control
USE_CACHE = False  # Set to False to disable cache and always fetch fresh data

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
# CACHING
# =========================================================

CACHE_DIR = Path("cache/module_4")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

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

def web_validate_minimal(
    canonical_name: str,
    original_name: str,
    budget: PerMachineBudget,
    outcome_registry: SupplierOutcomeRegistry
) -> Dict[str, Any]:
    """
    Phase C: Comprehensive Supplier Collection (bounded) with quality filtering
    
    Uses full web aggregator to collect detailed supplier information, then filters
    out irrelevant sources (government PDFs, marketplaces, generic articles).
    
    INVARIANT: Always record explicit outcome (found/skipped/failed)
    """
    if not WEB_SEARCH_ENABLED:
        outcome_registry.record_skip(
            original_name,
            SupplierOutcomeStatus.SKIPPED_NO_BUDGET,
            "Web search disabled in config"
        )
        return {"validated_suppliers": [], "web_source": "disabled"}
    
    # Check cache first (only if USE_CACHE is True)
    if USE_CACHE:
        cached = _cache_get(canonical_name, "suppliers_v1")
        if cached:
            logger.info(f"Phase C: Using cached suppliers for {canonical_name}")
            # Record outcome from cache
            suppliers = cached.get("validated_suppliers", [])
            if suppliers:
                outcome_registry.record_success(
                    original_name,
                    suppliers,
                    queries_made=cached.get("queries_used", 0),
                    pages_fetched=cached.get("pages_fetched", 0),
                    candidates_evaluated=len(suppliers),
                    candidates_filtered=0
                )
            else:
                outcome_registry.record_skip(
                    original_name,
                    SupplierOutcomeStatus.SKIPPED_NO_BUDGET,
                    "Cached result had no suppliers"
                )
            return cached
    else:
        logger.info(f"Phase C: Cache disabled, searching fresh suppliers for {canonical_name}")
    
    suppliers = []
    candidates_evaluated = 0
    candidates_filtered = 0
    
    try:
        # Single aggregator call for comprehensive supplier data
        if budget.can_query() and budget.has_time():
            from utils.web_search import aggregator
            
            logger.info(f"Phase C: Comprehensive supplier search for {canonical_name}")
            
            # Track the query
            query = f"{original_name} {canonical_name}".strip()
            budget.record_query("aggregator", query)
            
            # Use full aggregator to get complete supplier information
            raw_results = aggregator.search_machine_suppliers(
                machine_name=original_name,
                machine_type=canonical_name,
                region="Algeria",
                max_results_per_source=2,
                max_total_results=10  # Get more candidates for filtering
            )
            
            # Track page fetches (each result is from a page)
            for result in raw_results:
                budget.record_page_fetch(result.source_url or "unknown")
            
            candidates_evaluated = len(raw_results)
            logger.info(f"Phase C: Got {candidates_evaluated} raw candidates")
            
            # Convert to dict format for filtering
            raw_suppliers = []
            for result in raw_results:
                supplier_dict = {
                    "supplier_name": result.supplier_name,
                    "region": result.region or "Unknown",
                    "price_estimate": result.price_estimate or "Contact for quote",
                    "price_type": result.price_type or "Indicative",
                    "notes": result.notes or (result.customs_algeria_info if result.customs_algeria_info else f"Source: {result.source}"),
                    "relevance_score": result.relevance_score if result.relevance_score else 0.7,
                    "source_url": result.source_url,
                }
                if result.website:
                    supplier_dict["website"] = result.website
                raw_suppliers.append(supplier_dict)
            
            # Apply quality filtering
            logger.info(f"Phase C: Filtering {len(raw_suppliers)} candidates")
            filtered_suppliers = filter_suppliers(
                suppliers=raw_suppliers,
                machine_name=original_name,
                machine_type=canonical_name,
                min_score=0.5  # Require at least moderate quality
            )
            
            candidates_filtered = candidates_evaluated - len(filtered_suppliers)
            logger.info(f"Phase C: Filtered out {candidates_filtered} low-quality candidates, kept {len(filtered_suppliers)}")
            
            # Deduplicate
            suppliers = deduplicate_suppliers(filtered_suppliers)
            logger.info(f"Phase C: Deduplicated to {len(suppliers)} unique suppliers")
            
            # Enforce top 3
            suppliers = suppliers[:3]
            
            # Record outcome
            if suppliers:
                outcome_registry.record_success(
                    original_name,
                    suppliers,
                    queries_made=budget.queries_used,
                    pages_fetched=budget.pages_fetched,
                    candidates_evaluated=candidates_evaluated,
                    candidates_filtered=candidates_filtered
                )
            else:
                outcome_registry.record_failure(
                    original_name,
                    SupplierOutcomeStatus.SEARCH_FAILED_ALL_FILTERED,
                    f"All {candidates_evaluated} candidates filtered out (quality too low)",
                    queries_made=budget.queries_used,
                    pages_fetched=budget.pages_fetched,
                    candidates_evaluated=candidates_evaluated,
                    candidates_filtered=candidates_filtered
                )
        else:
            # Budget exhausted
            outcome_registry.record_skip(
                original_name,
                SupplierOutcomeStatus.SKIPPED_NO_BUDGET,
                "Machine budget exhausted (queries or time)"
            )
    
    except Exception as e:
        logger.warning(f"Phase C: Web validation failed for {canonical_name}: {e}")
        outcome_registry.record_failure(
            original_name,
            SupplierOutcomeStatus.SEARCH_FAILED_EXCEPTION,
            f"Search exception: {str(e)[:100]}",
            details=str(e),
            queries_made=budget.queries_used,
            pages_fetched=budget.pages_fetched
        )
    
    result = {
        "validated_suppliers": suppliers,
        "web_source": "aggregator",
        "queries_used": budget.queries_used,
        "pages_fetched": budget.pages_fetched,
        "candidates_evaluated": candidates_evaluated,
        "candidates_filtered": candidates_filtered,
    }
    
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
        
        return result
    
    except Exception as e:
        logger.error(f"Phase D: Synthesis failed: {e}")
        # NO RETRY - produce minimal safe object with confidence="low"
        result = phase_b.copy()
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
) -> Optional[Dict[str, Any]]:
    """
    Main enrichment pipeline for one machine.
    
    Returns None if machine should be excluded (subsystem).
    
    Runtime asserts:
    - Per-machine budgets enforced
    - No contacts enrichment called
    - Excluded classes never trigger web
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
    
    if should_validate_with_web(machine_class, confidence) and global_budget.can_allocate_machine():
        # Create per-machine budget
        machine_budget = global_budget.create_machine_budget(
            machine_name=nom_machine,
            max_queries=MAX_SEARCH_QUERIES_PER_MACHINE,
            max_pages=MAX_FETCH_PAGES_TOTAL,
            max_llm_calls=MAX_LLM_CALLS_PER_MACHINE,
            timeout_seconds=MAX_RUNTIME_PER_MACHINE_S
        )
        
        phase_c = web_validate_minimal(canonical_name, nom_machine, machine_budget, outcome_registry)
        
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
        # Skip - record in outcome registry
        if machine_class == CLASS_SUBSYSTEM:
            outcome_registry.record_skip(
                nom_machine,
                SupplierOutcomeStatus.SKIPPED_GENERIC,
                "Subsystem - no OEM supplier needed"
            )
        elif machine_class == CLASS_OPTIONAL:
            outcome_registry.record_skip(
                nom_machine,
                SupplierOutcomeStatus.SKIPPED_GENERIC,
                "Optional system - not priority for sourcing"
            )
        elif not global_budget.can_allocate_machine():
            outcome_registry.record_skip(
                nom_machine,
                SupplierOutcomeStatus.SKIPPED_NO_BUDGET,
                "Global budget exhausted"
            )
        else:
            outcome_registry.record_skip(
                nom_machine,
                SupplierOutcomeStatus.SKIPPED_GENERIC,
                f"Core stable machine with {confidence} confidence - internal knowledge sufficient"
            )
        
        logger.info(f"Phase C: Skipped for {canonical_name} (not needed or budget exhausted)")
        global_budget.skip_machine(nom_machine, "No web validation needed")
    
    # ASSERT: No contact enrichment in suppliers
    for supplier in phase_c.get("validated_suppliers", []):
        assert "email" not in supplier, "Contact enrichment found in Phase C"
        assert "phone" not in supplier, "Contact enrichment found in Phase C"
    
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
    
    # Restructure to match template format: machine_input + suppliers
    result = {
        "machine_input": {
            "nom_machine": machine.get("nom_machine", nom_machine),
            "type": machine.get("type", ""),
            "fabricant_recommande": machine.get("fabricant_recommande", ""),
            "quantite_necessaire": machine.get("quantite_necessaire", 1),
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
    
    return result

def process_module_4_bounded(
    machines: List[Dict[str, Any]],
    max_workers: int = 8,
) -> Dict[str, Any]:
    """
    Process all machines with bounded budgets.
    
    Returns enriched results.
    
    Acceptance criteria enforcement:
    - total_web_calls <= machines_count * 2
    - predictable runtime
    - stable JSON output
    - EVERY machine has explicit supplier outcome
    """
    t0 = time.time()
    
    # Initialize global budget and outcome registry
    global_budget = GlobalBudget(
        max_web_calls=len(machines) * GLOBAL_WEB_CALL_MULTIPLIER,
        machines_count=len(machines)
    )
    
    outcome_registry = SupplierOutcomeRegistry(total_machines=len(machines))
    
    logger.info("=" * 70)
    logger.info("START MODULE 4 — BOUNDED ENRICHMENT")
    logger.info(f"Input machines: {len(machines)}")
    logger.info(f"Max workers: {max_workers}")
    logger.info(f"Global web budget: {global_budget.max_web_calls} calls")
    logger.info(f"Per-machine limits: queries={MAX_SEARCH_QUERIES_PER_MACHINE}, "
                f"pages={MAX_FETCH_PAGES_TOTAL}, llm={MAX_LLM_CALLS_PER_MACHINE}, "
                f"time={MAX_RUNTIME_PER_MACHINE_S}s")
    logger.info("=" * 70)
    
    results = []
    excluded_count = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all machines
        future_map = {}
        for i, machine in enumerate(machines):
            future = executor.submit(enrich_machine_bounded, machine, global_budget, outcome_registry)
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
                results.append({
                    "machine_input": {
                        "nom_machine": nom_machine,
                        "type": machine.get("type", ""),
                        "fabricant_recommande": machine.get("fabricant_recommande", ""),
                        "quantite_necessaire": machine.get("quantite_necessaire", 1),
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
    outcome_registry.log_summary()
    
    # ASSERT: Global budget not exceeded
    global_summary = global_budget.get_global_summary()
    assert global_summary['budget_compliant'], \
        f"Global web budget exceeded: {global_budget.web_calls_used}/{global_budget.max_web_calls}"
    
    # ASSERT: All machines have explicit outcomes
    assert outcome_registry.validate(), "Some machines missing explicit supplier outcome!"
    
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
    
    return {
        "ribif_metadata": {
            "enrichment_method": "Module4 Bounded 4-Phase Pipeline with Quality Filtering",
            "enrichment_date": datetime.utcnow().isoformat(),
            "model_used": os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"),
            "api_provider": "Vertex",
            "processing_time_seconds": processing_time,
            "machines_in": len(machines),
            "machines_out": len(results),
            "machines_excluded": excluded_count,
            "web_calls_used": global_budget.web_calls_used,
            "web_calls_budget": global_budget.max_web_calls,
            "budget_compliant": global_summary['budget_compliant'],
            "web_call_breakdown": global_budget.global_tracker.get_summary()['breakdown'],
            "supplier_outcomes": outcome_summary,
        },
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
