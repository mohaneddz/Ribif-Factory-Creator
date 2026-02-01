"""
Quick Start Example: Agentic Supplier Sourcing
===============================================

This script demonstrates the agentic supplier sourcing workflow
with practical examples.

Run with:
    python backend/utils/module_4/example_agentic_sourcing.py
"""

import json
import time
from pathlib import Path

# Import the agentic sourcing modules
from utils.module_4.supplier_sourcing_agentic import (
    source_suppliers_for_machine,
    source_suppliers_batch,
    SourcingConfig,
)
from utils.module_4.agentic_integration import (
    process_module4_agentic_sourcing,
    get_sourcing_config_from_env,
)


def example_1_single_machine():
    """Example 1: Source suppliers for a single machine."""
    print("=" * 70)
    print("EXAMPLE 1: Single Machine Sourcing")
    print("=" * 70)
    
    machine_name = "plastic injection molding machine"
    print(f"\nMachine: {machine_name}")
    print(f"Starting sourcing workflow...\n")
    
    start = time.time()
    result = source_suppliers_for_machine(machine_name)
    duration = time.time() - start
    
    print(f"✓ Completed in {duration:.1f}s")
    print(f"\nResults:")
    print(f"  - Suppliers found: {len(result.suppliers)}")
    print(f"  - High confidence: {result.metrics.suppliers_high_confidence}")
    print(f"  - Medium confidence: {result.metrics.suppliers_medium_confidence}")
    print(f"  - Low confidence: {result.metrics.suppliers_low_confidence}")
    print(f"  - Pages fetched: {result.metrics.pages_fetched}")
    print(f"  - Queries executed: {result.metrics.queries_executed}")
    
    print(f"\nTop 5 Suppliers:")
    for i, supplier in enumerate(result.suppliers[:5], 1):
        print(f"  {i}. {supplier.name}")
        print(f"     Type: {supplier.supplier_type}, Score: {supplier.score:.2f}")
        print(f"     Location: {supplier.country or 'Unknown'}")
        if supplier.email:
            print(f"     Email: {supplier.email}")
        if supplier.phone:
            print(f"     Phone: {supplier.phone}")
        print()
    
    if result.warnings:
        print(f"⚠️  Warnings: {len(result.warnings)}")
        for warning in result.warnings[:3]:
            print(f"  - {warning}")
    
    return result


def example_2_batch_processing():
    """Example 2: Process multiple machines in parallel."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Batch Processing (Parallel)")
    print("=" * 70)
    
    machines = [
        "plastic injection molding machine",
        "cnc lathe machine",
        "packaging machine",
    ]
    
    print(f"\nMachines: {len(machines)}")
    for i, machine in enumerate(machines, 1):
        print(f"  {i}. {machine}")
    
    print(f"\nProcessing in parallel (max_workers=3)...\n")
    
    start = time.time()
    results = source_suppliers_batch(machines, max_workers=3)
    duration = time.time() - start
    
    print(f"✓ All completed in {duration:.1f}s")
    
    print(f"\nPer-Machine Results:")
    for result in results:
        print(f"\n  {result.machine}:")
        print(f"    Suppliers: {len(result.suppliers)}")
        print(f"    Duration: {result.metrics.duration_seconds:.1f}s")
        print(f"    Confidence: H:{result.metrics.suppliers_high_confidence} "
              f"M:{result.metrics.suppliers_medium_confidence} "
              f"L:{result.metrics.suppliers_low_confidence}")
    
    total_suppliers = sum(len(r.suppliers) for r in results)
    print(f"\n  Total suppliers found: {total_suppliers}")
    print(f"  Average per machine: {total_suppliers / len(results):.1f}")
    
    return results


def example_3_custom_config():
    """Example 3: Custom configuration for specific needs."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Custom Configuration")
    print("=" * 70)
    
    # High-quality configuration (fewer but better results)
    config = SourcingConfig(
        max_queries=3,
        max_pages_total=15,  # More pages for thorough search
        target_suppliers_min=10,
        target_suppliers_max=20,
        strictness_level="strict",
        min_confidence_score=0.6,  # Higher threshold
        domain_diversity_cap=1,  # Strict diversity (1 per domain)
        timeout_per_machine=60.0,  # Longer timeout
    )
    
    print(f"\nConfiguration:")
    print(f"  - Max queries: {config.max_queries}")
    print(f"  - Max pages: {config.max_pages_total}")
    print(f"  - Target: {config.target_suppliers_min}-{config.target_suppliers_max}")
    print(f"  - Strictness: {config.strictness_level}")
    print(f"  - Min confidence: {config.min_confidence_score}")
    print(f"  - Timeout: {config.timeout_per_machine}s")
    
    machine = "cnc machining center"
    print(f"\nMachine: {machine}")
    print(f"Starting sourcing with custom config...\n")
    
    result = source_suppliers_for_machine(machine, config=config)
    
    print(f"✓ Completed in {result.metrics.duration_seconds:.1f}s")
    print(f"\nResults with strict filtering:")
    print(f"  - Suppliers: {len(result.suppliers)}")
    print(f"  - All have score ≥ {config.min_confidence_score}")
    print(f"  - Pages fetched: {result.metrics.pages_fetched}")
    
    print(f"\nSupplier Quality:")
    for supplier in result.suppliers[:5]:
        print(f"  - {supplier.name}: {supplier.score:.2f}")
    
    return result


def example_4_module4_integration():
    """Example 4: Module 4 integration format."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Module 4 Integration Format")
    print("=" * 70)
    
    # Simulated Module 4 input
    machines_input = [
        {"nom_machine": "Machine d'injection plastique", "quantite": 2},
        {"nom_machine": "Tour CNC", "quantite": 1},
    ]
    
    print(f"\nInput (Module 4 format):")
    print(json.dumps(machines_input, indent=2, ensure_ascii=False))
    
    print(f"\nProcessing...\n")
    
    output = process_module4_agentic_sourcing(machines_input, max_workers=2)
    
    print(f"✓ Completed")
    print(f"\nSummary:")
    print(json.dumps(output["summary"], indent=2, ensure_ascii=False))
    
    print(f"\nFirst machine enriched:")
    first_machine = output["machines_enriched"][0]
    print(f"  Original: {first_machine['machine_input']['nom_machine']}")
    print(f"  Canonical: {first_machine['canonical_name']}")
    print(f"  Suppliers: {len(first_machine['suppliers'])}")
    
    print(f"\n  Top 3 suppliers:")
    for i, supplier in enumerate(first_machine['suppliers'][:3], 1):
        print(f"    {i}. {supplier['supplier_name']}")
        print(f"       Type: {supplier['supplier_type']}, Score: {supplier['score']:.2f}")
    
    return output


def example_5_monitoring_and_logging():
    """Example 5: Monitoring metrics and logging."""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Monitoring & Logging")
    print("=" * 70)
    
    machine = "thermoforming machine"
    
    print(f"\nMachine: {machine}")
    print(f"Sourcing with full metrics tracking...\n")
    
    result = source_suppliers_for_machine(machine)
    
    # Access detailed metrics
    metrics = result.metrics
    
    print(f"Detailed Metrics:")
    print(f"  Query Generation:")
    print(f"    - Queries generated: {metrics.queries_generated}")
    print(f"    - Queries executed: {metrics.queries_executed}")
    
    print(f"\n  Search Phase:")
    print(f"    - Search results found: {metrics.search_results_found}")
    print(f"    - URLs scanned: {metrics.urls_scanned}")
    
    print(f"\n  Extraction Phase:")
    print(f"    - Pages fetched: {metrics.pages_fetched}")
    print(f"    - Pages failed: {metrics.pages_failed}")
    print(f"    - Success rate: {(metrics.pages_fetched - metrics.pages_failed) / max(metrics.pages_fetched, 1) * 100:.1f}%")
    
    print(f"\n  Candidate Processing:")
    print(f"    - Candidates extracted: {metrics.candidates_extracted}")
    print(f"    - Candidates filtered: {metrics.candidates_filtered}")
    print(f"    - Candidates deduplicated: {metrics.candidates_deduplicated}")
    
    print(f"\n  Final Results:")
    print(f"    - Suppliers final: {metrics.suppliers_final}")
    print(f"    - High confidence: {metrics.suppliers_high_confidence}")
    print(f"    - Medium confidence: {metrics.suppliers_medium_confidence}")
    print(f"    - Low confidence: {metrics.suppliers_low_confidence}")
    
    print(f"\n  Performance:")
    print(f"    - Duration: {metrics.duration_seconds:.2f}s")
    print(f"    - Timed out: {'Yes' if metrics.timed_out else 'No'}")
    
    # Check quality metrics
    print(f"\n  Quality Indicators:")
    avg_confidence = sum(s.confidence for s in result.suppliers) / len(result.suppliers) if result.suppliers else 0
    avg_score = sum(s.score for s in result.suppliers) / len(result.suppliers) if result.suppliers else 0
    has_contact = sum(1 for s in result.suppliers if s.email or s.phone)
    
    print(f"    - Average confidence: {avg_confidence:.2f}")
    print(f"    - Average score: {avg_score:.2f}")
    print(f"    - Suppliers with contact: {has_contact}/{len(result.suppliers)}")
    
    return result


def save_results_to_file(results, filename="sourcing_results.json"):
    """Save results to JSON file."""
    output_dir = Path("data/module_4/agentic_results")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / filename
    
    # Convert results to dict
    if isinstance(results, list):
        data = [r.to_dict() for r in results]
    else:
        data = results.to_dict()
    
    output_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n💾 Results saved to: {output_file}")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print(" AGENTIC SUPPLIER SOURCING - QUICK START EXAMPLES")
    print("=" * 70)
    print("\nThis script demonstrates the agentic supplier sourcing workflow")
    print("with various use cases and configurations.\n")
    
    try:
        # Example 1: Single machine
        result1 = example_1_single_machine()
        
        # Example 2: Batch processing
        results2 = example_2_batch_processing()
        
        # Example 3: Custom configuration
        result3 = example_3_custom_config()
        
        # Example 4: Module 4 integration
        output4 = example_4_module4_integration()
        
        # Example 5: Monitoring and logging
        result5 = example_5_monitoring_and_logging()
        
        # Save results
        print("\n" + "=" * 70)
        save_results_to_file(result1, "example_single_machine.json")
        save_results_to_file(results2, "example_batch_processing.json")
        
        print("\n" + "=" * 70)
        print("✓ All examples completed successfully!")
        print("=" * 70)
        print("\nNext steps:")
        print("  1. Review the results in data/module_4/agentic_results/")
        print("  2. Adjust configuration based on your needs")
        print("  3. Integrate into Module 4 route")
        print("  4. Run tests: python backend/utils/module_4/test_supplier_sourcing_agentic.py")
        print("\nDocumentation: backend/utils/module_4/AGENTIC_SOURCING_README.md")
        print("=" * 70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
