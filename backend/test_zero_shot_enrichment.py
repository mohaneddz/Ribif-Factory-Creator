"""
Test Zero-Shot Intelligent Machine Enrichment
==============================================

This script demonstrates the zero-shot enrichment system with:
- Vague input: "Injection plastique (100T → 5000T)"
- LLM-generated smart search queries
- Query budget tracking (max 2 queries per machine)
- Gap analysis and intelligent re-querying
- Educated estimations for missing data
- DZD pricing with tariffs
"""

import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.module_1.zero_shot_enricher import ZeroShotEnricher
from utils.logger import get_logger

logger = get_logger(__name__)

# =========================================================
# Test Cases
# =========================================================

TEST_MACHINES = [
    {
        "nom_machine": "Machine d'injection plastique",
        "description": "Injection plastique (100T → 5000T)",
        "type": "Injection molding machine",
        "utilisation": "Moulage de pièces polymères par injection, de 100T à 5000T de force de fermeture",
        "specifications": {}
    },
    {
        "nom_machine": "Extrudeuse bi-vis",
        "description": "Extrudeuse bi-vis pour composites (D=65mm, L/D=40)",
        "type": "Twin-screw extruder",
        "specifications": {
            "screw_diameter": "65mm",
            "l_d_ratio": "40"
        }
    },
    {
        "nom_machine": "Presse hydraulique",
        "description": "Presse hydraulique 500 tonnes pour formage à froid",
        "type": "Hydraulic press",
        "specifications": {
            "capacity": "500 tons"
        }
    }
]


def test_single_machine():
    """Test enrichment of a single machine with vague description."""
    print("\n" + "=" * 80)
    print("TEST 1: Single Machine Enrichment (Vague Input)")
    print("=" * 80 + "\n")
    
    machine = TEST_MACHINES[0]
    print(f"Input: {machine['nom_machine']}")
    print(f"Description: {machine['description']}")
    print(f"\nStarting enrichment with max 2 queries...\n")
    
    enricher = ZeroShotEnricher(max_queries_per_machine=2)
    result = enricher.enrich_machine(machine)
    
    print("\n" + "-" * 80)
    print("ENRICHMENT RESULTS")
    print("-" * 80)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Verify key fields
    metadata = result.get("enrichment_metadata", {})
    print("\n" + "-" * 80)
    print("SUMMARY")
    print("-" * 80)
    print(f"Queries used: {metadata.get('queries_used')}/{enricher.max_queries_per_machine}")
    print(f"Query history: {metadata.get('queries_history')}")
    print(f"Processing time: {metadata.get('processing_time_s')}s")
    print(f"Final confidence: {metadata.get('final_confidence')}")
    print(f"Gaps remaining: {result.get('gaps', [])}")
    
    # Check pricing in DZD
    if result.get("pricing"):
        print(f"\nPricing (DZD):")
        print(f"  Amount: {result['pricing'].get('amount_dzd', 'N/A')}")
        print(f"  Range: {result['pricing'].get('price_range_dzd', 'N/A')}")
        print(f"  Includes tariff: {result['pricing'].get('includes_tariff')}")
        print(f"  Tariff rate: {result['pricing'].get('tariff_rate')}")
    
    # Check suppliers
    suppliers = result.get("suppliers", [])
    print(f"\nSuppliers found: {len(suppliers)}")
    for i, s in enumerate(suppliers[:3], 1):
        print(f"  {i}. {s.get('name', 'N/A')} ({s.get('location', 'N/A')})")
    
    return result


def test_multiple_machines():
    """Test enrichment of multiple machines in parallel."""
    print("\n" + "=" * 80)
    print("TEST 2: Multiple Machines Enrichment")
    print("=" * 80 + "\n")
    
    enricher = ZeroShotEnricher(max_queries_per_machine=2)
    
    results = []
    for machine in TEST_MACHINES:
        print(f"\nEnriching: {machine['nom_machine']}")
        result = enricher.enrich_machine(machine)
        results.append(result)
        
        metadata = result.get("enrichment_metadata", {})
        print(f"  ✓ Completed in {metadata.get('processing_time_s')}s")
        print(f"  ✓ Queries used: {metadata.get('queries_used')}")
        print(f"  ✓ Confidence: {metadata.get('final_confidence')}")
    
    print("\n" + "-" * 80)
    print("BATCH SUMMARY")
    print("-" * 80)
    
    total_time = sum(r.get("enrichment_metadata", {}).get("processing_time_s", 0) for r in results)
    total_queries = sum(r.get("enrichment_metadata", {}).get("queries_used", 0) for r in results)
    
    print(f"Total machines: {len(results)}")
    print(f"Total queries used: {total_queries}")
    print(f"Total processing time: {total_time:.2f}s")
    print(f"Average time per machine: {total_time / len(results):.2f}s")
    
    return results


def test_query_budget_limits():
    """Test that query budget limits are enforced."""
    print("\n" + "=" * 80)
    print("TEST 3: Query Budget Enforcement")
    print("=" * 80 + "\n")
    
    machine = TEST_MACHINES[0]
    
    # Test with different query limits
    for max_queries in [1, 2, 3]:
        print(f"\nTest with max_queries = {max_queries}")
        enricher = ZeroShotEnricher(max_queries_per_machine=max_queries)
        result = enricher.enrich_machine(machine)
        
        queries_used = result.get("enrichment_metadata", {}).get("queries_used", 0)
        print(f"  Budget: {max_queries} queries")
        print(f"  Used: {queries_used} queries")
        print(f"  Compliance: {'✓ PASS' if queries_used <= max_queries else '✗ FAIL'}")
        
        if queries_used > max_queries:
            print(f"  ERROR: Query budget exceeded!")
    
    print("\n✓ Query budget enforcement test complete")


def test_dzd_conversion():
    """Test DZD currency conversion with tariffs."""
    print("\n" + "=" * 80)
    print("TEST 4: DZD Currency Conversion")
    print("=" * 80 + "\n")
    
    # Mock machine with USD pricing
    machine = {
        "nom_machine": "Test Machine",
        "description": "Test machine for pricing conversion",
        "type": "Test",
        "specifications": {}
    }
    
    enricher = ZeroShotEnricher(max_queries_per_machine=1)
    result = enricher.enrich_machine(machine)
    
    pricing = result.get("pricing", {})
    print("Pricing Conversion Test:")
    print(f"  USD amount: {pricing.get('amount', 'N/A')}")
    print(f"  DZD amount: {pricing.get('amount_dzd', 'N/A')}")
    print(f"  Conversion rate: 1 USD = 160 DZD")
    print(f"  Import tariff: 15%")
    print(f"  Includes tariff: {pricing.get('includes_tariff', False)}")
    
    # Verify calculation if pricing exists
    if pricing.get("amount") and pricing.get("amount_dzd"):
        expected_dzd = int(pricing["amount"] * 160 * 1.15)
        actual_dzd = pricing["amount_dzd"]
        print(f"\n  Expected DZD: {expected_dzd}")
        print(f"  Actual DZD: {actual_dzd}")
        print(f"  Match: {'✓ PASS' if abs(expected_dzd - actual_dzd) < 100 else '✗ FAIL'}")


def main():
    """Run all tests."""
    print("\n" + "█" * 80)
    print("ZERO-SHOT INTELLIGENT MACHINE ENRICHMENT TEST SUITE")
    print("█" * 80)
    
    try:
        # Test 1: Single machine
        result1 = test_single_machine()
        
        # Test 2: Multiple machines
        # results2 = test_multiple_machines()
        
        # Test 3: Query budget limits
        test_query_budget_limits()
        
        # Test 4: DZD conversion
        test_dzd_conversion()
        
        print("\n" + "█" * 80)
        print("ALL TESTS COMPLETED")
        print("█" * 80 + "\n")
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
