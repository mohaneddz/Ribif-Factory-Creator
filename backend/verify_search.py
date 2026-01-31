
"""
Verification script for RIBIF web search utilities.
Tests individual providers and the aggregation logic.
"""

import sys
import os
import time
from pprint import pprint

# Add backend to path
sys.path.append(os.path.abspath("d:/Programming/AI/Hackathons/.Competitions/EliteHack/ribif/backend"))

from config import WEB_SEARCH_ENABLED
try:
    from utils.web_search import aggregator
    from utils.web_search import duckduckgo
    from utils.web_search import alibaba
except ImportError as e:
    print(f"Failed to import web search modules: {e}")
    sys.exit(1)

def test_duckduckgo():
    print("\n=== Testing DuckDuckGo ===")
    try:
        results = duckduckgo.web_search("CNC milling machine suppliers", max_results=3)
        print(f"Found {len(results)} results")
        for r in results:
            print(f"- {r.title} ({r.url})")
            
        instant = duckduckgo.instant_answer("python programming")
        if instant:
            print(f"Instant Answer: {instant.get('heading')} - {instant.get('answer')[:100]}...")
    except Exception as e:
        print(f"DuckDuckGo test failed: {e}")

def test_alibaba():
    print("\n=== Testing Alibaba Scraper ===")
    try:
        products = alibaba.search_products("industrial mixer", max_results=3)
        print(f"Found {len(products)} products")
        for p in products:
            print(f"- {p.name[:50]}... | Price: {p.price} | Supplier: {p.supplier_name}")
            
        if products and products[0].supplier_url:
            print(f"Fetching details for supplier: {products[0].supplier_name}")
            details = alibaba.get_supplier_details(products[0].supplier_url)
            if details:
                print(f"Supplier Region: {details.region}")
    except Exception as e:
        print(f"Alibaba test failed: {e}")

def test_aggregator_suppliers():
    print("\n=== Testing Aggregator: Supplier Search ===")
    try:
        suppliers = aggregator.search_machine_suppliers("injection molding machine", "plastic", max_total_results=5)
        print(f"Found {len(suppliers)} aggregated suppliers")
        for s in suppliers:
            print(f"- {s.supplier_name} ({s.source}) | Region: {s.region} | relevance: {s.relevance_score}")
    except Exception as e:
        print(f"Aggregator supplier test failed: {e}")

def test_aggregator_specs():
    print("\n=== Testing Aggregator: Specs Search ===")
    try:
        specs = aggregator.search_machine_specs("Haas VF-2", "Haas Automation")
        print(f"Manufacturer: {specs.manufacturer}")
        print(f"Website: {specs.manufacturer_website}")
        print(f"Datasheets: {len(specs.datasheet_urls)}")
        for ds in specs.datasheet_urls:
            print(f"- {ds}")
    except Exception as e:
        print(f"Aggregator specs test failed: {e}")

if __name__ == "__main__":
    if not WEB_SEARCH_ENABLED:
        print("WARNING: WEB_SEARCH_ENABLED is False in config")
    
    test_duckduckgo()
    test_alibaba()
    # Add delays to avoid rate limits during test sequence
    time.sleep(2)
    test_aggregator_suppliers()
    time.sleep(2)
    test_aggregator_specs()
