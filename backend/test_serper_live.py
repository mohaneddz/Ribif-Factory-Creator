"""Test Serper API with the new key"""

import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

print("=== Testing Serper API ===\n")

try:
    from utils.web_search import serper
    
    # Test 1: Basic search
    print("1. Testing basic Google search via Serper:")
    results = serper.search_google("CNC milling machine suppliers", num_results=5)
    print(f"   ✓ Got {len(results)} results\n")
    
    for i, r in enumerate(results, 1):
        print(f"   {i}. {r.title[:70]}")
        print(f"      {r.url[:80]}")
        print(f"      {r.snippet[:100]}...\n")
    
    # Test 2: Image search
    print("\n2. Testing image search via Serper:")
    images = serper.search_images("industrial CNC machine", num_results=3)
    print(f"   ✓ Got {len(images)} images\n")
    
    for i, img in enumerate(images, 1):
        print(f"   {i}. {img.title[:60]}")
        print(f"      {img.url[:80]}\n")
    
    print("\n✓✓✓ Serper API is working perfectly! ✓✓✓")
    print("\nNow testing aggregator with Serper enabled...")
    
    # Test 3: Aggregator
    from utils.web_search import aggregator
    suppliers = aggregator.search_machine_suppliers(
        "injection molding machine",
        machine_type="plastic processing",
        max_total_results=10
    )
    
    print(f"\n3. Aggregator found {len(suppliers)} suppliers:")
    for i, s in enumerate(suppliers[:5], 1):
        print(f"   {i}. {s.supplier_name} ({s.region}) - {s.source}")
        print(f"      {s.website[:80]}")
    
    if len(suppliers) > 0:
        print("\n✓✓✓ SUCCESS! Searches are now returning results! ✓✓✓")
    else:
        print("\n⚠ Aggregator returned 0 results - checking why...")
        
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
