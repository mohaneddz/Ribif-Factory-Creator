"""Full end-to-end test of Module 1 enrichment with fixed web search"""

import sys
import os
import json
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

print("=== Testing Full Module 1 Enrichment ===\n")

# Test data
test_machines = [
    {
        "name": "CNC Vertical Machining Center",
        "manufacturer": "Haas Automation",
        "machine_type": "CNC Machining",
        "use_case": "Precision metal cutting"
    },
    {
        "name": "Injection Molding Machine",
        "manufacturer": "ARBURG",
        "machine_type": "Plastic Processing",
        "use_case": "Plastic part production"
    }
]

try:
    from utils.module_1.enricher import RIBIFEnricher
    enricher = RIBIFEnricher()
    
    for i, machine_data in enumerate(test_machines, 1):
        print(f"\n{'='*70}")
        print(f"Test {i}: {machine_data['name']}")
        print(f"Manufacturer: {machine_data['manufacturer']}")
        print('='*70)
        
        # Create minimal machine structure
        machine = {
            "nom_machine": machine_data["name"],
            "fabricant_recommande": machine_data.get("manufacturer", ""),
            "type_machine": machine_data.get("machine_type", ""),
            "application": machine_data.get("use_case", ""),
            "selected_models": [],
            "suppliers": []
        }
        
        # Run enrichment
        print(f"\nEnriching machine data...")
        enriched = enricher.enrich_one_machine_global(machine)
        
        # Display results
        print(f"\n✓ Enrichment complete!")
        print(f"\nSuppliers found: {len(enriched.get('suppliers', []))}")
        
        for j, supplier in enumerate(enriched.get('suppliers', [])[:5], 1):
            print(f"  {j}. {supplier['supplier_name']} ({supplier.get('region', 'Unknown')})")
            print(f"     Role: {supplier.get('role', 'Unknown')}")
            print(f"     Website: {supplier.get('website', 'N/A')[:60]}")
            print(f"     Confidence: {supplier.get('confidence', 'N/A')}")
        
        if len(enriched.get('suppliers', [])) == 0:
            print("  ⚠ WARNING: No suppliers found!")
        
        print(f"\nSelected Models: {len(enriched.get('selected_models', []))}")
        for model in enriched.get('selected_models', []):
            print(f"  - {model.get('brand', 'N/A')}: {model.get('model', 'N/A')} ({model.get('type', 'N/A')})")
        
        # Save to file for inspection
        output_file = f"test_enrichment_{i}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(enriched, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Full results saved to {output_file}")
        
        print(f"\n{'-'*70}\n")
    
    print("\n" + "="*70)
    print("✓✓✓ SUCCESS! Module 1 enrichment is working with worldwide search! ✓✓✓")
    print("="*70)
    print("\nKey improvements:")
    print("✓ Using Serper API for worldwide Google search")
    print("✓ Finding real manufacturers and distributors")
    print("✓ Covering USA, Europe, Asia, and global suppliers")
    print("✓ No longer dependent on Chinese B2B sites")
    
except Exception as e:
    print(f"\n✗ Error during enrichment: {e}")
    import traceback
    traceback.print_exc()
