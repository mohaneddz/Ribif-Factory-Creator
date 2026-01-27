"""
Bing Web Search API integration.

Bing provides a generous free tier (1,000 transactions/month).
API Key required: https://www.microsoft.com/en-us/bing/apis/bing-web-search-api

Environment variable: BING_API_KEY
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .base import (
    SearchProvider,
    SearchResult,
    ImageResult,
    SearchError,
    safe_request,
)

BING_API_URL = "https://api.bing.microsoft.com/v7.0"


class BingSearch(SearchProvider):
    """Bing Web Search API provider."""

    name = "bing"
    requires_api_key = True

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key or os.getenv("BING_API_KEY"))

    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make authenticated request to Bing API."""
        self._check_api_key()
        
        response = safe_request(
            url=f"{BING_API_URL}/{endpoint}",
            headers={"Ocp-Apim-Subscription-Key": self.api_key},
            params=params,
        )
        return response.json()

    def search(self, query: str, count: int = 10, **kwargs) -> List[SearchResult]:
        """Search Bing Web."""
        try:
            data = self._make_request("search", {
                "q": query,
                "count": min(count, 50),
                "mkt": kwargs.get("market", "en-US"),
                "safeSearch": kwargs.get("safe_search", "Moderate"),
            })
            
            results = []
            for item in data.get("webPages", {}).get("value", []):
                results.append(SearchResult(
                    title=item.get("name", ""),
                    url=item.get("url", ""),
                    snippet=item.get("snippet", ""),
                    source="bing",
                    metadata={
                        "dateLastCrawled": item.get("dateLastCrawled"),
                        "language": item.get("language"),
                    }
                ))
            
            return results
        except Exception as e:
            raise SearchError(f"Bing search failed: {e}")

    def search_images(self, query: str, count: int = 10) -> List[ImageResult]:
        """Search Bing Images."""
        try:
            data = self._make_request("images/search", {
                "q": query,
                "count": min(count, 50),
            })
            
            results = []
            for item in data.get("value", []):
                results.append(ImageResult(
                    url=item.get("contentUrl", ""),
                    thumbnail_url=item.get("thumbnailUrl", ""),
                    title=item.get("name", ""),
                    source_url=item.get("hostPageUrl", ""),
                    width=item.get("width", 0),
                    height=item.get("height", 0),
                    source="bing",
                ))
            
            return results
        except Exception as e:
            raise SearchError(f"Bing image search failed: {e}")

    def search_entities(self, query: str) -> Optional[Dict[str, Any]]:
        """Search Bing Entity Search for company/product info."""
        try:
            data = self._make_request("entities", {"q": query, "mkt": "en-US"})
            
            entities = data.get("entities", {}).get("value", [])
            if entities:
                entity = entities[0]
                return {
                    "name": entity.get("name"),
                    "description": entity.get("description"),
                    "url": entity.get("url"),
                    "image": entity.get("image", {}).get("hostPageUrl"),
                    "entity_type": entity.get("entityPresentationInfo", {}).get("entityTypeHints", []),
                }
            return None
        except Exception:
            return None


# Convenience functions
_default_bing: Optional[BingSearch] = None


def _get_bing() -> BingSearch:
    global _default_bing
    if _default_bing is None:
        _default_bing = BingSearch()
    return _default_bing


def search_web(query: str, count: int = 10) -> List[SearchResult]:
    """Search Bing Web."""
    return _get_bing().search(query, count)


def search_images(query: str, count: int = 10) -> List[ImageResult]:
    """Search Bing Images."""
    return _get_bing().search_images(query, count)


def search_entities(query: str) -> Optional[Dict[str, Any]]:
    """Search Bing Entity Search."""
    return _get_bing().search_entities(query)
