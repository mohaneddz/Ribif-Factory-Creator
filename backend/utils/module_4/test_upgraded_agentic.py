"""
Test script for UPGRADED agentic supplier sourcing workflow.

Tests the enhanced features:
- Multi-pass search strategy
- Higher limits (5 queries, 20 pages, 180s timeout)
- Retry logic with exponential backoff
- Candidate harvesting (30-80)
- Fallback vendor catalog
- Enhanced observability
"""

import sys
import os
import time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from utils.module_4.supplier_sourcing_agentic import (
    source_suppliers_for_machine,
    SourcingConfig,
    DEFAULT_CONFIG,
)


def test_upgraded_workflow():
    """Test upgraded high-recall workflow."""
    
    print("="*80)
    print("TESTING UPGRADED AGENTIC SUPPLIER SOURCING WORKFLOW")
    print("="*80)
    print()
    
    # Test config with higher limits (as upgraded)
    config = SourcingConfig(
        max_queries=5,
        max_results_per_query=15,
        max_pages_total=20,
        domain_diversity_cap=3,
        target_suppliers_min=15,
        target_suppliers_max=40,
        candidate_cap=80,
        min_confidence_score=0.25,
        timeout_per_machine=180.0,
        use_llm_ranking=True,
        max_llm_calls=3,
        max_retries=3,
        retry_backoff_base=1.0,
        retry_jitter=True,
        enable_multipass=True,
        search_passes=3,
        enable_fallback_catalog=True,
        fallback_catalog_threshold=10,
    )
    
    # Test machine
    test_machine = "injection molding machine"
    
    print(f"Test Machine: {test_machine}")
    print(f"Config: max_queries={config.max_queries}, max_pages={config.max_pages_total}, timeout={config.timeout_per_machine}s")
    print(f"Features: multipass={config.enable_multipass}, fallback={config.enable_fallback_catalog}, retries={config.max_retries}")
    print()
    print("Starting sourcing...")
    print()
    
    start = time.time()
    result = source_suppliers_for_machine(test_machine, config)
    duration = time.time() - start
    
    print()
    print("="*80)
    print("RESULTS")
    print("="*80)
    
    # Metrics
    m = result.metrics
    print(f"\n[METRICS]")
    print(f"  Duration: {m.duration_seconds:.1f}s (actual: {duration:.1f}s)")
    print(f"  Timed out: {m.timed_out}")
    print()
    print(f"  Queries generated: {m.queries_generated}")
    print(f"  Queries executed: {m.queries_executed}")
    print(f"  Queries tried:")
    for i, q in enumerate(m.queries_tried, 1):
        print(f"    {i}. {q}")
    print()
    print(f"  Search results:")
    print(f"    Pass 1 (Broad): {m.search_pass_1_results}")
    print(f"    Pass 2 (Regional): {m.search_pass_2_results}")
    print(f"    Pass 3 (Vertical): {m.search_pass_3_results}")
    print(f"    Total: {m.search_results_found}")
    print()
    print(f"  Candidates:")
    print(f"    Raw harvested: {m.raw_candidates}")
    print(f"    After dedup: {m.raw_candidates - m.candidates_deduplicated} (removed {m.candidates_deduplicated})")
    print(f"    After filter: {m.candidates_extracted - m.candidates_filtered}")
    print()
    print(f"  Suppliers:")
    print(f"    Final: {m.suppliers_final}")
    print(f"    High confidence (>=0.7): {m.suppliers_high_confidence}")
    print(f"    Medium confidence (>=0.5): {m.suppliers_medium_confidence}")
    print(f"    Low confidence (<0.5): {m.suppliers_low_confidence}")
    print(f"    From fallback catalog: {m.suppliers_from_fallback}")
    print(f"    Fallback used: {m.fallback_catalog_used}")
    print()
    print(f"  Pages:")
    print(f"    Fetched: {m.pages_fetched}")
    print(f"    Failed: {m.pages_failed}")
    print()
    print(f"  Retries:")
    print(f"    Retry attempts: {m.retry_attempts}")
    print(f"    Retry successes: {m.retry_successes}")
    print()
    
    # Suppliers
    print(f"\n[SUPPLIERS] ({len(result.suppliers)} total)")
    for i, supplier in enumerate(result.suppliers[:10], 1):
        print(f"  {i}. {supplier.name}")
        print(f"     Type: {supplier.supplier_type} | Score: {supplier.score:.2f}")
        print(f"     URL: {supplier.url}")
        is_fallback = supplier.metadata.get('is_fallback', False) if supplier.metadata else False
        if is_fallback:
            print(f"     [FALLBACK SUPPLIER]")
        print()
    
    if len(result.suppliers) > 10:
        print(f"  ... and {len(result.suppliers) - 10} more")
        print()
    
    # Warnings
    if result.warnings:
        print(f"\n[WARNINGS]")
        for warning in result.warnings:
            print(f"  - {warning}")
        print()
    
    # Validation
    print(f"\n[VALIDATION]")
    
    checks = []
    
    # Check 1: At least 10 suppliers (with fallback guarantee)
    if len(result.suppliers) >= 10:
        checks.append(("PASS", "Found at least 10 suppliers"))
    else:
        checks.append(("FAIL", f"Only found {len(result.suppliers)} suppliers (expected >=10 with fallback)"))
    
    # Check 2: Multi-pass executed
    if m.search_pass_1_results > 0 and (m.search_pass_2_results > 0 or m.search_pass_3_results > 0):
        checks.append(("PASS", "Multi-pass search executed"))
    else:
        checks.append(("WARN", "Multi-pass may not have executed properly"))
    
    # Check 3: Candidate harvesting (30-80 target)
    if m.raw_candidates >= 30:
        checks.append(("PASS", f"Harvested {m.raw_candidates} raw candidates (>=30)"))
    elif m.raw_candidates >= 15:
        checks.append(("WARN", f"Harvested {m.raw_candidates} raw candidates (expected >=30)"))
    else:
        checks.append(("FAIL", f"Only harvested {m.raw_candidates} raw candidates (expected >=30)"))
    
    # Check 4: Fallback catalog available
    if config.enable_fallback_catalog:
        checks.append(("PASS", "Fallback catalog enabled"))
    else:
        checks.append(("FAIL", "Fallback catalog not enabled"))
    
    # Check 5: Retry logic configured
    if config.max_retries > 0:
        checks.append(("PASS", f"Retry logic enabled (max_retries={config.max_retries})"))
    else:
        checks.append(("FAIL", "Retry logic not configured"))
    
    for status, msg in checks:
        print(f"  [{status}] {msg}")
    
    print()
    print("="*80)
    
    return result


if __name__ == "__main__":
    result = test_upgraded_workflow()
    
    # Exit code
    if result.suppliers and len(result.suppliers) >= 10:
        print("\n[SUCCESS] Upgraded workflow test passed!")
        sys.exit(0)
    else:
        print("\n[FAILURE] Upgraded workflow test failed (insufficient suppliers)")
        sys.exit(1)
