"""Test if Serper API is working after configuration"""

import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

print("=== Verifying Serper API Configuration ===\n")

# Check if API key is set
serper_key = os.getenv("SERPER_API_KEY")
if not serper_key:
    print("❌ SERPER_API_KEY not found in environment")
    print("\nMake sure you:")
    print("1. Added SERPER_API_KEY=your_key to the .env file")
    print("2. Restart your terminal/IDE to reload environment")
    sys.exit(1)

print(f"✓ SERPER_API_KEY is set (length: {len(serper_key)})")

# Test Serper API
print("\n=== Testing Serper API ===")
try:
    from utils.web_search import serper
    results = serper.search_google("CNC milling machine manufacturers", num_results=5)
    print(f"✓ Serper API works! Found {len(results)} results:\n")
    
    for i, r in enumerate(results, 1):
        print(f"{i}. {r.title[:70]}")
        print(f"   {r.url[:80]}")
        print(f"   {r.snippet[:100]}...\n")
    
except Exception as e:
    print(f"❌ Serper API failed: {e}")
    sys.exit(1)

# Test aggregator with Serper
print("\n=== Testing Full Aggregator (should use Serper now) ===")
try:
    from utils.web_search import aggregator
    suppliers = aggregator.search_machine_suppliers(
        machine_name="CNC Milling Machine",
        machine_type="industrial",
        max_total_results=5
    )
    
    print(f"✓ Aggregator works! Found {len(suppliers)} suppliers:\n")
    
    for i, s in enumerate(suppliers, 1):
        print(f"{i}. {s.supplier_name}")
        print(f"   Region: {s.region}")
        print(f"   Website: {s.website[:60]}")
        print(f"   Source: {s.source}")
        print(f"   Relevance: {s.relevance_score}\n")
    
    if len(suppliers) == 0:
        print("⚠ No suppliers found - check aggregator logic")
    
except Exception as e:
    print(f"❌ Aggregator failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*60)
print("✅ SUCCESS! Web search is now working properly!")
print("="*60)
print("\nYour searches should now return real results instead of 0.")
