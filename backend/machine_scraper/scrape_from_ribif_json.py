"""
Machine scraper that extracts machines from RIBIF JSON document.

Reads a large RIBIF JSON document, extracts machines from stage_4_machines_equipements,
and scrapes them for specifications and images.
"""

import sys
import os
import json
import logging
from pathlib import Path

sys.path.append(os.getcwd())

# Set up logging and credentials
logging.basicConfig(level=logging.WARNING)
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.abspath("ribif-module4-key.json")

from app.machine_enrichment import MachineInputModule1, enrich_machine_module1
from app.output_formatter import format_enriched_output

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

def extract_machines_from_ribif(ribif_file: str) -> list:
    """
    Extract machines from RIBIF JSON document.
    
    Looks for: ribif_json["stage_4_machines_equipements"]["machines_production"]
    """
    
    if not os.path.exists(ribif_file):
        print(f"Error: RIBIF file '{ribif_file}' not found!")
        print(f"Expected at: {os.path.abspath(ribif_file)}")
        return []
    
    try:
        with open(ribif_file, encoding='utf-8') as f:
            ribif_data = json.load(f)
        
        # Extract machines from stage 4
        machines = ribif_data.get("stage_4_machines_equipements", {}).get("machines_production", [])
        
        if not machines:
            print("No machines found in stage_4_machines_equipements.machines_production!")
            return []
        
        print(f"✓ Extracted {len(machines)} machines from RIBIF document")
        return machines
        
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {ribif_file}: {e}")
        return []
    except Exception as e:
        print(f"Error reading {ribif_file}: {e}")
        return []

def scrape_ribif_machines(ribif_file: str = "FICHE_IDENTITE_INDUSTRIELLE_ribif_extracted_before_enrichment.json"):
    """
    Extract machines from RIBIF file and scrape them.
    """
    
    machines = extract_machines_from_ribif(ribif_file)
    if not machines:
        sys.exit(1)
    
    print(f"\n{'='*70}")
    print(f"MACHINE SCRAPER - RIBIF Document Input")
    print(f"{'='*70}")
    print(f"\nInput file: {ribif_file}")
    print(f"Machines to scrape: {len(machines)}\n")
    
    results = []
    
    for idx, machine_data in enumerate(machines, 1):
        nom_machine = machine_data.get('nom_machine', 'Unknown')
        machine_type = machine_data.get('type', '')
        
        print(f"\n[{idx}/{len(machines)}] Scraping: {nom_machine}")
        print(f"     Type: {machine_type}")
        
        try:
            # Convert to MachineInputModule1
            machine_input = MachineInputModule1(**machine_data)
            
            # Scrape
            print(f"     [*] Enriching...")
            enriched = enrich_machine_module1(machine_input, search_null_fields_only=True)
            
            # Format output - pass input_data to preserve all fields
            clean_output = format_enriched_output(enriched, input_data=machine_input)
            results.append(clean_output)
            
            # Summary
            print(f"     [+] Completeness: {enriched.completeness_score:.1%}")
            print(f"     [+] Images: {len(enriched.assets.image_urls)}")
            print(f"     [+] Datasheets: {len(enriched.assets.datasheet_urls)}")
            
        except Exception as e:
            print(f"     [-] Error: {str(e)[:100]}")
            results.append({
                "nom_machine": nom_machine,
                "error": str(e)
            })
    
    # Save all results
    output_file = OUTPUT_DIR / "ribif_scraping_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*70}")
    print(f"[+] All results saved to: {output_file}")
    print(f"{'='*70}\n")
    
    # Summary
    successful = sum(1 for r in results if 'error' not in r)
    print(f"\nSummary:")
    print(f"  Total: {len(machines)} machines")
    print(f"  Successful: {successful}")
    print(f"  Failed: {len(machines) - successful}")

if __name__ == "__main__":
    ribif_file = "FICHE_IDENTITE_INDUSTRIELLE_ribif_extracted_before_enrichment.json"
    if len(sys.argv) > 1:
        ribif_file = sys.argv[1]
    
    scrape_ribif_machines(ribif_file)
