
import json
import logging
from pathlib import Path
import sys

# Add current dir to path
sys.path.append(str(Path(__file__).parent))

from utils.module_1.enrichment_agent import RibifEnrichmentAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("enrichment_runner")

def main():
    target_file = Path("data/module_1/module_1.json")
    output_file = Path("data/module_1/module_1_enriched.json")
    
    if not target_file.exists():
        logger.error(f"File not found: {target_file}")
        return

    logger.info(f"Reading {target_file}...")
    data = json.loads(target_file.read_text(encoding="utf-8"))
    
    agent = RibifEnrichmentAgent()
    logger.info("Starting enrichment agent...")
    enriched_data = agent.enrich_json(data)
    
    logger.info(f"Saving enriched data to {output_file}...")
    output_file.write_text(json.dumps(enriched_data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Enrichment complete.")

if __name__ == "__main__":
    main()
