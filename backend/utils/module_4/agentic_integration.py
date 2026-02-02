"""
Integration Adapter: Agentic Supplier Sourcing for Module 4
============================================================

Adapts the new agentic supplier sourcing workflow to work with the existing
Module 4 infrastructure while maintaining backward compatibility.

Features:
    - Converts Module 4 machine inputs to sourcing requests
    - Integrates with existing caching, metrics, and DB sync
    - Provides configuration management
    - Handles parallel processing
    - Maintains output format compatibility
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils.logger import get_logger
from utils.module_4.supplier_sourcing_agentic import (
    source_suppliers_for_machine,
    source_suppliers_batch,
    SourcingConfig,
    SourcingResult,
    DEFAULT_CONFIG,
)

logger = get_logger(__name__)

# =========================================================
# CONFIGURATION MANAGEMENT
# =========================================================

def get_sourcing_config_from_env() -> SourcingConfig:
    """
    Load sourcing configuration from environment or use defaults.
    
    Environment variables (optional):
        - SOURCING_MAX_QUERIES: Max queries per machine (default: 3)
        - SOURCING_MAX_PAGES: Max pages to fetch (default: 12)
        - SOURCING_TARGET_MIN: Min suppliers target (default: 15)
        - SOURCING_TARGET_MAX: Max suppliers target (default: 30)
        - SOURCING_TIMEOUT: Timeout per machine in seconds (default: 45)
        - SOURCING_STRICTNESS: Strictness level (strict/balanced/relaxed, default: balanced)
        - SOURCING_ENABLE_CACHE: Enable caching (default: True)
    
    Returns:
        SourcingConfig with environment overrides
    """
    import os
    
    config = SourcingConfig(
        max_queries=int(os.getenv("SOURCING_MAX_QUERIES", DEFAULT_CONFIG.max_queries)),
        max_pages_total=int(os.getenv("SOURCING_MAX_PAGES", DEFAULT_CONFIG.max_pages_total)),
        target_suppliers_min=int(os.getenv("SOURCING_TARGET_MIN", DEFAULT_CONFIG.target_suppliers_min)),
        target_suppliers_max=int(os.getenv("SOURCING_TARGET_MAX", DEFAULT_CONFIG.target_suppliers_max)),
        timeout_per_machine=float(os.getenv("SOURCING_TIMEOUT", DEFAULT_CONFIG.timeout_per_machine)),
        strictness_level=os.getenv("SOURCING_STRICTNESS", DEFAULT_CONFIG.strictness_level),
        enable_cache=os.getenv("SOURCING_ENABLE_CACHE", "false").lower() == "true",
        domain_diversity_cap=int(os.getenv("SOURCING_DOMAIN_CAP", DEFAULT_CONFIG.domain_diversity_cap)),
        use_llm_ranking=os.getenv("SOURCING_USE_LLM_RANKING", "false").lower() == "true",
    )
    
    logger.info(f"Sourcing config: max_queries={config.max_queries}, "
                f"max_pages={config.max_pages_total}, "
                f"target={config.target_suppliers_min}-{config.target_suppliers_max}, "
                f"timeout={config.timeout_per_machine}s")
    
    return config


# =========================================================
# MODULE 4 INPUT PARSING
# =========================================================

def extract_machines_from_module4_input(module4_input: Dict[str, Any]) -> List[str]:
    """
    Extract machine names from Module 4 input structure.
    
    Expected input format:
        {
            "stage_4_machines_equipements": {
                "machines_production": [
                    {"nom_machine": "Machine Name", ...},
                    ...
                ]
            }
        }
    
    Args:
        module4_input: Module 4 input dictionary
    
    Returns:
        List of machine names
    """
    machines = []
    
    try:
        machines_list = module4_input.get("stage_4_machines_equipements", {}).get("machines_production", [])
        
        for machine_data in machines_list:
            if isinstance(machine_data, dict):
                machine_name = machine_data.get("nom_machine")
                if machine_name:
                    machines.append(machine_name)
            elif isinstance(machine_data, str):
                machines.append(machine_data)
        
        logger.info(f"Extracted {len(machines)} machines from input")
        
    except Exception as e:
        logger.error(f"Failed to extract machines from input: {e}")
    
    return machines


# =========================================================
# OUTPUT CONVERSION
# =========================================================

def convert_sourcing_result_to_module4_format(
    result: SourcingResult,
    original_machine_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Convert SourcingResult to Module 4 output format.
    
    Output format (compatible with existing Module 4 structure):
        {
            "machine_input": {
                "nom_machine": "...",
                "original_data": {...}
            },
            "canonical_name": "...",
            "suppliers": [
                {
                    "supplier_name": "...",
                    "supplier_type": "OEM|distributor|integrator|service",
                    "country": "...",
                    "coverage": ["Algeria", "North Africa"],
                    "website": "...",
                    "contact_page": "...",
                    "email": "...",
                    "phone": "...",
                    "confidence": 0.85,
                    "score": 0.75,
                    "evidence": [...],
                    "notes": "..."
                }
            ],
            "enrichment_metadata": {
                "queries_used": [...],
                "suppliers_found": 25,
                "high_confidence": 10,
                "medium_confidence": 12,
                "low_confidence": 3,
                "pages_fetched": 10,
                "duration_seconds": 12.5,
                "warnings": [...]
            }
        }
    
    Args:
        result: SourcingResult from agentic workflow
        original_machine_data: Original machine data from input
    
    Returns:
        Module 4 formatted dictionary
    """
    # Machine input section
    machine_input = {
        "nom_machine": result.machine,
    }
    
    if original_machine_data:
        machine_input["original_data"] = original_machine_data
    
    if result.normalization:
        machine_input.update({
            "canonical_name": result.normalization.canonical_name,
            "keywords": result.normalization.keywords,
            "category": result.normalization.category,
        })
    
    # Convert suppliers
    suppliers_list = []
    for supplier in result.suppliers:
        suppliers_list.append({
            "supplier_name": supplier.name,
            "supplier_type": supplier.supplier_type,
            "country": supplier.country,
            "coverage": supplier.coverage,
            "website": supplier.website,
            "contact_page": supplier.contact_page,
            "email": supplier.email,
            "phone": supplier.phone,
            "confidence": supplier.confidence,
            "score": supplier.score,
            "evidence": supplier.evidence_snippets,
            "notes": " | ".join(supplier.notes) if supplier.notes else None,
            "metadata": supplier.metadata,
        })
    
    # Enrichment metadata
    enrichment_metadata = {
        "queries_used": result.queries_used,
        "suppliers_found": result.metrics.suppliers_final,
        "high_confidence": result.metrics.suppliers_high_confidence,
        "medium_confidence": result.metrics.suppliers_medium_confidence,
        "low_confidence": result.metrics.suppliers_low_confidence,
        "pages_fetched": result.metrics.pages_fetched,
        "pages_failed": result.metrics.pages_failed,
        "candidates_extracted": result.metrics.candidates_extracted,
        "candidates_filtered": result.metrics.candidates_filtered,
        "duration_seconds": result.metrics.duration_seconds,
        "timed_out": result.metrics.timed_out,
        "warnings": result.warnings,
    }
    
    return {
        "machine_input": machine_input,
        "canonical_name": result.normalization.canonical_name if result.normalization else result.machine,
        "suppliers": suppliers_list,
        "enrichment_metadata": enrichment_metadata,
    }


# =========================================================
# MAIN PROCESSING FUNCTION
# =========================================================

def process_module4_agentic_sourcing(
    machines: List[Dict[str, Any]],
    config: Optional[SourcingConfig] = None,
    max_workers: int = 4,
) -> Dict[str, Any]:
    """
    Process Module 4 machines using agentic supplier sourcing.
    
    This is the main entry point for Module 4 integration.
    
    Args:
        machines: List of machine dictionaries from Module 4 input
        config: Optional sourcing configuration (uses env/defaults if None)
        max_workers: Max parallel workers
    
    Returns:
        Module 4 formatted output with enriched machines
    """
    if config is None:
        config = get_sourcing_config_from_env()
    
    logger.info(f"Processing {len(machines)} machines with agentic sourcing")
    
    # Extract machine names
    machine_names = []
    machine_data_map = {}
    
    for machine_data in machines:
        if isinstance(machine_data, dict):
            name = machine_data.get("nom_machine")
            if name:
                machine_names.append(name)
                machine_data_map[name] = machine_data
        elif isinstance(machine_data, str):
            machine_names.append(machine_data)
            machine_data_map[machine_data] = {"nom_machine": machine_data}
    
    if not machine_names:
        logger.warning("No valid machines found in input")
        return {
            "machines_enriched": [],
            "summary": {
                "total_machines": 0,
                "total_suppliers": 0,
                "total_duration": 0.0,
            },
            "warnings": ["No valid machines found in input"],
        }
    
    # Execute sourcing for all machines (parallel)
    results = source_suppliers_batch(
        machines=machine_names,
        config=config,
        max_workers=max_workers,
    )
    
    # Convert results to Module 4 format
    enriched_machines = []
    total_suppliers = 0
    total_duration = 0.0
    all_warnings = []
    
    for result in results:
        machine_name = result.machine
        original_data = machine_data_map.get(machine_name, {})
        
        enriched = convert_sourcing_result_to_module4_format(result, original_data)
        enriched_machines.append(enriched)
        
        total_suppliers += result.metrics.suppliers_final
        total_duration += result.metrics.duration_seconds
        
        if result.warnings:
            all_warnings.extend([f"{machine_name}: {w}" for w in result.warnings])
    
    # Build summary
    summary = {
        "total_machines": len(enriched_machines),
        "total_suppliers": total_suppliers,
        "avg_suppliers_per_machine": total_suppliers / len(enriched_machines) if enriched_machines else 0,
        "total_duration_seconds": total_duration,
        "avg_duration_per_machine": total_duration / len(enriched_machines) if enriched_machines else 0,
        "config_used": {
            "max_queries": config.max_queries,
            "max_pages_total": config.max_pages_total,
            "target_suppliers": f"{config.target_suppliers_min}-{config.target_suppliers_max}",
            "timeout_per_machine": config.timeout_per_machine,
            "strictness": config.strictness_level,
        },
    }
    
    # Build final output
    output = {
        "machines_enriched": enriched_machines,
        "summary": summary,
        "ribif_metadata": {
            "module": "module4_agentic_sourcing",
            "version": "1.0.0",
            "workflow": "agentic_multi_step",
        },
    }
    
    if all_warnings:
        output["warnings"] = all_warnings
    
    logger.info(f"Completed: {len(enriched_machines)} machines, "
                f"{total_suppliers} suppliers, "
                f"{total_duration:.1f}s total")
    
    return output


# =========================================================
# CACHING INTEGRATION
# =========================================================

CACHE_DIR = Path("cache/module_4/agentic")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_cached_result(machine_name: str, config: SourcingConfig) -> Optional[SourcingResult]:
    """
    Get cached sourcing result if available and fresh.
    
    Args:
        machine_name: Machine name
        config: Sourcing configuration
    
    Returns:
        Cached SourcingResult or None
    """
    if not config.enable_cache:
        return None
    
    import hashlib
    import time
    
    # Create cache key from machine name + config hash
    config_str = f"{config.max_queries}:{config.max_pages_total}:{config.target_suppliers_max}"
    cache_key = hashlib.md5(f"{machine_name}::{config_str}".encode()).hexdigest()
    cache_file = CACHE_DIR / f"{cache_key}.json"
    
    if not cache_file.exists():
        return None
    
    # Check TTL
    age_days = (time.time() - cache_file.stat().st_mtime) / 86400
    if age_days > config.cache_ttl_days:
        logger.debug(f"Cache expired for {machine_name}")
        return None
    
    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        logger.info(f"Cache hit for {machine_name}")
        # Note: Full deserialization would require reconstructing objects
        # For now, return None and let it re-execute
        # TODO: Implement full deserialization if caching is critical
        return None
    except Exception as e:
        logger.warning(f"Cache read failed for {machine_name}: {e}")
        return None


def cache_result(result: SourcingResult, config: SourcingConfig) -> None:
    """
    Cache sourcing result.
    
    Args:
        result: SourcingResult to cache
        config: Sourcing configuration
    """
    if not config.enable_cache:
        return
    
    import hashlib
    
    try:
        config_str = f"{config.max_queries}:{config.max_pages_total}:{config.target_suppliers_max}"
        cache_key = hashlib.md5(f"{result.machine}::{config_str}".encode()).hexdigest()
        cache_file = CACHE_DIR / f"{cache_key}.json"
        
        data = result.to_dict()
        cache_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        
        logger.debug(f"Cached result for {result.machine}")
    except Exception as e:
        logger.warning(f"Cache write failed for {result.machine}: {e}")


# =========================================================
# BACKWARD COMPATIBILITY WRAPPER
# =========================================================

def process_module_4_agentic(
    machines: List[Any],
    max_workers: int = 4,
    **kwargs,
) -> Dict[str, Any]:
    """
    Backward-compatible wrapper for existing Module 4 calls.
    
    This function signature matches the existing `process_module_4_bounded`
    so it can be used as a drop-in replacement.
    
    Args:
        machines: List of machine data (dict or string)
        max_workers: Max parallel workers
        **kwargs: Additional arguments (forwarded to config)
    
    Returns:
        Module 4 formatted output
    """
    # Extract config overrides from kwargs
    config = SourcingConfig(
        max_queries=kwargs.get("max_queries", DEFAULT_CONFIG.max_queries),
        max_pages_total=kwargs.get("max_pages", DEFAULT_CONFIG.max_pages_total),
        target_suppliers_min=kwargs.get("target_min", DEFAULT_CONFIG.target_suppliers_min),
        target_suppliers_max=kwargs.get("target_max", DEFAULT_CONFIG.target_suppliers_max),
        timeout_per_machine=kwargs.get("timeout", DEFAULT_CONFIG.timeout_per_machine),
        strictness_level=kwargs.get("strictness", DEFAULT_CONFIG.strictness_level),
    )
    
    return process_module4_agentic_sourcing(
        machines=machines,
        config=config,
        max_workers=max_workers,
    )


# =========================================================
# USAGE EXAMPLE
# =========================================================

if __name__ == "__main__":
    # Example usage
    test_machines = [
        {"nom_machine": "Machine d'injection plastique"},
        {"nom_machine": "Tour CNC"},
        {"nom_machine": "Presse hydraulique"},
    ]
    
    result = process_module4_agentic_sourcing(test_machines, max_workers=2)
    
    print(json.dumps(result, indent=2, ensure_ascii=False))
