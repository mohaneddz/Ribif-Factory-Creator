"""Quick test to diagnose web search issues"""

import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Test 1: Direct HTTP requests
print("=== Test 1: Basic HTTP Request ===")
try:
    import requests
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    response = requests.get("https://www.alibaba.com", headers=headers, timeout=10)
    print(f"✓ Alibaba: Status {response.status_code}, Content Length: {len(response.text)}")
except Exception as e:
    print(f"✗ Alibaba failed: {e}")

# Test 2: DuckDuckGo API (no scraping)
print("\n=== Test 2: DuckDuckGo Instant Answer API ===")
try:
    response = requests.get("https://api.duckduckgo.com/?q=Python+programming&format=json", timeout=10)
    data = response.json()
    if data.get("Abstract"):
        print(f"✓ DuckDuckGo API works: {data['Heading']}")
    else:
        print(f"✓ DuckDuckGo API responded but no instant answer for this query")
except Exception as e:
    print(f"✗ DuckDuckGo API failed: {e}")

# Test 3: Check if BeautifulSoup works
print("\n=== Test 3: BeautifulSoup Parsing ===")
try:
    from bs4 import BeautifulSoup
    html = "<html><body><div class='test'>Hello</div></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    print(f"✓ BeautifulSoup works: {soup.select_one('.test').text}")
except Exception as e:
    print(f"✗ BeautifulSoup failed: {e}")

# Test 4: Check aggregator imports
print("\n=== Test 4: Import Web Search Modules ===")
try:
    from utils.web_search import aggregator
    from utils.web_search import alibaba
    from utils.web_search import duckduckgo
    print("✓ All web search modules imported successfully")
except Exception as e:
    print(f"✗ Import failed: {e}")

# Test 5: Try a simple Alibaba search with debugging
print("\n=== Test 5: Alibaba Search (with details) ===")
try:
    from utils.web_search import alibaba
    print("Searching Alibaba for 'CNC machine'...")
    results = alibaba.search_products("CNC machine", max_results=3)
    print(f"Results found: {len(results)}")
    if results:
        for i, r in enumerate(results, 1):
            print(f"  {i}. {r.name[:60]} - {r.url[:50]}")
    else:
        print("  ⚠ No results returned (possible scraping issue)")
except Exception as e:
    print(f"✗ Alibaba search failed: {e}")

# Test 6: Check if Serper API key is set
print("\n=== Test 6: API Keys Check ===")
serper_key = os.getenv("SERPER_API_KEY")
bing_key = os.getenv("BING_API_KEY")
print(f"SERPER_API_KEY: {'✓ SET' if serper_key else '✗ NOT SET'}")
print(f"BING_API_KEY: {'✓ SET' if bing_key else '✗ NOT SET'}")

if serper_key:
    print("\n=== Test 7: Serper API Test ===")
    try:
        from utils.web_search import serper
        results = serper.search_google("industrial machinery", num_results=3)
        print(f"✓ Serper API works: {len(results)} results")
        for i, r in enumerate(results, 1):
            print(f"  {i}. {r.title[:60]}")
    except Exception as e:
        print(f"✗ Serper API failed: {e}")

print("\n=== Summary ===")
print("If all tests pass but results are 0, the issue is:")
print("1. Website HTML structure changed (selectors outdated)")
print("2. Websites blocking scrapers (need API keys)")
print("3. Network/firewall issues")
print("\nRecommendation: Use Serper API (set SERPER_API_KEY) for reliable results")
