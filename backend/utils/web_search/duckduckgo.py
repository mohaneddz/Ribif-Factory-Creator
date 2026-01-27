"""
DuckDuckGo search integration (no API key required).

Uses DuckDuckGo Instant Answer API and HTML scraping as fallback.
Free and unlimited, but results may be less comprehensive than Google.
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

from .base import (
    SearchProvider,
    SearchResult,
    ImageResult,
    SearchError,
    safe_request,
    rate_limit,
)

DUCKDUCKGO_API_URL = "https://api.duckduckgo.com"
DUCKDUCKGO_HTML_URL = "https://html.duckduckgo.com/html"


class DuckDuckGoSearch(SearchProvider):
    """DuckDuckGo search provider (no API key required)."""

    name = "duckduckgo"
    requires_api_key = False

    def __init__(self):
        super().__init__()

    def instant_answer(self, query: str) -> Optional[Dict[str, Any]]:
        """Get instant answer from DuckDuckGo API."""
        try:
            response = safe_request(
                url=f"{DUCKDUCKGO_API_URL}/?q={quote_plus(query)}&format=json&no_html=1",
                timeout=10,
            )
            data = response.json()
            
            if data.get("Abstract"):
                return {
                    "answer": data.get("Abstract"),
                    "source": data.get("AbstractSource"),
                    "url": data.get("AbstractURL"),
                    "image": data.get("Image"),
                    "heading": data.get("Heading"),
                }
            
            # Try related topics
            if data.get("RelatedTopics"):
                topics = []
                for topic in data.get("RelatedTopics", [])[:5]:
                    if isinstance(topic, dict) and topic.get("Text"):
                        topics.append({
                            "text": topic.get("Text"),
                            "url": topic.get("FirstURL"),
                        })
                if topics:
                    return {"related_topics": topics}
            
            return None
        except Exception:
            return None

    @rate_limit(min_gap_s=2.0)  # Be polite to DuckDuckGo
    def search(self, query: str, max_results: int = 10, **kwargs) -> List[SearchResult]:
        """Search DuckDuckGo by scraping HTML results."""
        try:
            response = safe_request(
                url=DUCKDUCKGO_HTML_URL,
                method="POST",
                data={"q": query, "b": ""},
                timeout=15,
            )
            
            results = self._parse_html_results(response.text, max_results)
            return results
        except Exception as e:
            raise SearchError(f"DuckDuckGo search failed: {e}")

    def _parse_html_results(self, html: str, max_results: int) -> List[SearchResult]:
        """Parse DuckDuckGo HTML search results."""
        results = []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            
            for result in soup.select(".result"):
                if len(results) >= max_results:
                    break
                
                title_elem = result.select_one(".result__title a")
                snippet_elem = result.select_one(".result__snippet")
                
                if title_elem:
                    url = title_elem.get("href", "")
                    # DuckDuckGo uses redirect URLs, try to extract actual URL
                    if "uddg=" in url:
                        match = re.search(r"uddg=([^&]+)", url)
                        if match:
                            from urllib.parse import unquote
                            url = unquote(match.group(1))
                    
                    results.append(SearchResult(
                        title=title_elem.get_text(strip=True),
                        url=url,
                        snippet=snippet_elem.get_text(strip=True) if snippet_elem else "",
                        source="duckduckgo",
                    ))
        except Exception:
            pass
        
        return results


# Convenience functions
_default_ddg: Optional[DuckDuckGoSearch] = None


def _get_ddg() -> DuckDuckGoSearch:
    global _default_ddg
    if _default_ddg is None:
        _default_ddg = DuckDuckGoSearch()
    return _default_ddg


def instant_answer(query: str) -> Optional[Dict[str, Any]]:
    """Get DuckDuckGo instant answer."""
    return _get_ddg().instant_answer(query)


def web_search(query: str, max_results: int = 10) -> List[SearchResult]:
    """Search DuckDuckGo web."""
    return _get_ddg().search(query, max_results)
