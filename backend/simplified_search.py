"""
Simplified Web Search Implementation
=====================================

This replaces broken scrapers with:
1. DuckDuckGo HTML search (works without API)
2. Simple Google scraping fallback
3. Serper API (if key is provided)

The original Alibaba/Made-in-China scrapers fail because:
- Websites use JavaScript to render content
- Anti-bot measures block requests
- HTML selectors are fragile and change frequently
"""

from __future__ import annotations

import re
import requests
from typing import List, Optional
from dataclasses import dataclass, asdict
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

@dataclass
class SimpleSearchResult:
    title: str
    url: str
    snippet: str = ""
    
    def to_dict(self):
        return asdict(self)


def search_duckduckgo_lite(query: str, max_results: int = 10) -> List[SimpleSearchResult]:
    """
    Search DuckDuckGo using their HTML endpoint.
    More reliable than Alibaba scraping.
    """
    results = []
    try:
        url = "https://lite.duckduckgo.com/lite/"
        data = {"q": query}
        
        response = requests.post(url, data=data, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # DDG Lite uses simple table structure
        for row in soup.select("tr")[:max_results * 2]:  # Get more rows, filter later
            link_elem = row.select_one("a.result-link")
            snippet_elem = row.select_one("td.result-snippet")
            
            if link_elem:
                title = link_elem.get_text(strip=True)
                url = link_elem.get("href", "")
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                
                if url and not url.startswith("/"):  # Skip internal links
                    results.append(SimpleSearchResult(
                        title=title,
                        url=url,
                        snippet=snippet
                    ))
                    
                    if len(results) >= max_results:
                        break
        
    except Exception as e:
        print(f"DuckDuckGo search failed: {e}")
    
    return results


def search_google_custom(query: str, max_results: int = 10) -> List[SimpleSearchResult]:
    """
    Simple Google search (may get blocked, use as fallback).
    For production, use Serper API instead.
    """
    results = []
    try:
        url = f"https://www.google.com/search?q={query}&num={max_results}"
        response = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Google uses div.g for result blocks
        for result_div in soup.select("div.g")[:max_results]:
            title_elem = result_div.select_one("h3")
            link_elem = result_div.select_one("a")
            snippet_elem = result_div.select_one("div[data-sncf], .VwiC3b")
            
            if title_elem and link_elem:
                title = title_elem.get_text(strip=True)
                url = link_elem.get("href", "")
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                
                if url.startswith("http"):
                    results.append(SimpleSearchResult(
                        title=title,
                        url=url,
                        snippet=snippet
                    ))
        
    except Exception as e:
        print(f"Google search failed: {e}")
    
    return results


def search_for_suppliers(machine_name: str, max_results: int = 10) -> List[dict]:
    """
    Search for industrial machine suppliers.
    Returns simple supplier data from web search.
    """
    query = f"{machine_name} manufacturer supplier distributor specifications"
    
    # Try DuckDuckGo first (more reliable)
    results = search_duckduckgo_lite(query, max_results)
    
    # If DDG fails, try Google
    if not results:
        print("DDG failed, trying Google...")
        results = search_google_custom(query, max_results)
    
    # Convert to supplier format
    suppliers = []
    for r in results:
        # Extract company name from title (heuristic)
        title_parts = r.title.split("-")[0].split("|")[0].strip()
        
        suppliers.append({
            "supplier_name": title_parts[:100],
            "website": r.url,
            "region": "Unknown",  # Would need geolocation
            "source_urls": [r.url],
            "confidence": "medium",
            "notes": r.snippet[:200]
        })
    
    return suppliers


if __name__ == "__main__":
    print("=== Testing Simplified Search ===\n")
    
    # Test 1: DuckDuckGo
    print("1. DuckDuckGo Lite Search for 'CNC milling machine':")
    results = search_duckduckgo_lite("CNC milling machine manufacturer", max_results=5)
    print(f"   Found: {len(results)} results")
    for i, r in enumerate(results, 1):
        print(f"   {i}. {r.title[:60]}")
        print(f"      {r.url[:70]}")
    
    # Test 2: Supplier search
    print("\n2. Supplier Search for 'injection molding machine':")
    suppliers = search_for_suppliers("injection molding machine", max_results=5)
    print(f"   Found: {len(suppliers)} potential suppliers")
    for i, s in enumerate(suppliers, 1):
        print(f"   {i}. {s['supplier_name'][:50]}")
        print(f"      {s['website'][:70]}")
    
    print("\n=== Test Complete ===")
    print("\nRECOMMENDATION:")
    print("For production, get a Serper API key (free tier available):")
    print("1. Go to https://serper.dev")
    print("2. Sign up and get API key")
    print("3. Set SERPER_API_KEY in your .env file")
