"""
Serper.dev API integration for Google SERP results.

Serper provides fast, affordable Google Search API access.
API Key required: https://serper.dev/

Environment variable: SERPER_API_KEY
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .base import (
    SearchProvider,
    SearchResult,
    ImageResult,
    SearchError,
    APIKeyError,
    safe_request,
)

SERPER_API_URL = "https://google.serper.dev"


class SerperSearch(SearchProvider):
    """Serper.dev Google Search API provider."""

    name = "serper"
    requires_api_key = True

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key or os.getenv("SERPER_API_KEY"))

    def _make_request(self, endpoint: str, query: str, num_results: int = 10, **kwargs) -> Dict[str, Any]:
        """Make authenticated request to Serper API."""
        self._check_api_key()
        
        payload = {
            "q": query,
            "num": min(num_results, 100),
            **kwargs
        }
        
        response = safe_request(
            url=f"{SERPER_API_URL}/{endpoint}",
            method="POST",
            headers={
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json",
            },
            json=payload,
        )
        return response.json()

    def search(self, query: str, num_results: int = 10, **kwargs) -> List[SearchResult]:
        """Search Google via Serper API."""
        try:
            data = self._make_request("search", query, num_results, **kwargs)
            results = []
            
            for item in data.get("organic", []):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    source="serper",
                    metadata={
                        "position": item.get("position"),
                        "domain": item.get("domain"),
                    }
                ))
            
            return results
        except Exception as e:
            raise SearchError(f"Serper search failed: {e}")

    def search_images(self, query: str, num_results: int = 10) -> List[ImageResult]:
        """Search Google Images via Serper API."""
        try:
            data = self._make_request("images", query, num_results)
            results = []
            
            for item in data.get("images", []):
                results.append(ImageResult(
                    url=item.get("imageUrl", ""),
                    thumbnail_url=item.get("thumbnailUrl", ""),
                    title=item.get("title", ""),
                    source_url=item.get("link", ""),
                    width=item.get("imageWidth", 0),
                    height=item.get("imageHeight", 0),
                    source="serper",
                ))
            
            return results
        except Exception as e:
            raise SearchError(f"Serper image search failed: {e}")

    def search_news(self, query: str, num_results: int = 10) -> List[SearchResult]:
        """Search Google News via Serper API."""
        try:
            data = self._make_request("news", query, num_results)
            results = []
            
            for item in data.get("news", []):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    source="serper_news",
                    metadata={
                        "date": item.get("date"),
                        "source": item.get("source"),
                    }
                ))
            
            return results
        except Exception as e:
            raise SearchError(f"Serper news search failed: {e}")


# Convenience functions using default instance
_default_serper: Optional[SerperSearch] = None


def _get_serper() -> SerperSearch:
    global _default_serper
    if _default_serper is None:
        _default_serper = SerperSearch()
    return _default_serper


def search_google(query: str, num_results: int = 10) -> List[SearchResult]:
    """Search Google using Serper API."""
    return _get_serper().search(query, num_results)


def search_images(query: str, num_results: int = 10) -> List[ImageResult]:
    """Search Google Images using Serper API."""
    return _get_serper().search_images(query, num_results)


def search_news(query: str, num_results: int = 10) -> List[SearchResult]:
    """Search Google News using Serper API."""
    return _get_serper().search_news(query, num_results)
