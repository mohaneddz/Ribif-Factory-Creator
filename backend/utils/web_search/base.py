"""
Base classes and shared utilities for web search providers.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar
from urllib.parse import urlparse

import requests

# Rate limiting state per domain
_domain_last_request: Dict[str, float] = {}
_RATE_LIMIT_LOCK = None  # Will use threading.Lock if needed

# Default settings
DEFAULT_TIMEOUT_S = 15
DEFAULT_RATE_LIMIT_GAP_S = 1.0
DEFAULT_CACHE_TTL_HOURS = 24

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


class SearchError(Exception):
    """Base exception for search-related errors."""
    pass


class RateLimitError(SearchError):
    """Raised when rate limit is exceeded."""
    pass


class APIKeyError(SearchError):
    """Raised when API key is missing or invalid."""
    pass


@dataclass
class SearchResult:
    """Generic web search result."""
    title: str
    url: str
    snippet: str = ""
    source: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ImageResult:
    """Image search result."""
    url: str
    thumbnail_url: str = ""
    title: str = ""
    source_url: str = ""
    width: int = 0
    height: int = 0
    source: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SupplierResult:
    """Supplier information from web search."""
    supplier_name: str
    website: str
    region: str = ""
    price_estimate: str = ""
    price_type: str = "Indicative"
    price_currency: str = "USD"
    phone_number: str = ""
    email_address: str = ""
    customs_algeria_info: str = ""
    source: str = ""
    source_url: str = ""
    notes: str = ""
    relevance_score: float = 0.5
    verified: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProductResult:
    """Product listing from B2B marketplace."""
    name: str
    url: str
    price: str = ""
    price_min: float = 0.0
    price_max: float = 0.0
    currency: str = "USD"
    supplier_name: str = ""
    supplier_url: str = ""
    image_url: str = ""
    moq: str = ""  # Minimum Order Quantity
    specifications: Dict[str, str] = field(default_factory=dict)
    source: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MachineSpecsResult:
    """Machine specifications from web search."""
    manufacturer: str = ""
    manufacturer_website: str = ""
    model: str = ""
    specifications: Dict[str, str] = field(default_factory=dict)
    datasheet_urls: List[str] = field(default_factory=list)
    image_urls: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def get_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def rate_limit(min_gap_s: float = DEFAULT_RATE_LIMIT_GAP_S):
    """Decorator to enforce rate limiting per domain."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract URL from args/kwargs for domain-based limiting
            url = kwargs.get("url") or (args[0] if args else "")
            if isinstance(url, str) and url.startswith("http"):
                domain = get_domain(url)
                now = time.time()
                last = _domain_last_request.get(domain, 0.0)
                gap = now - last
                if gap < min_gap_s:
                    time.sleep(min_gap_s - gap)
                _domain_last_request[domain] = time.time()
            return func(*args, **kwargs)
        return wrapper
    return decorator


class SearchCache:
    """Simple file-based cache for search results."""

    def __init__(self, cache_dir: Optional[Path] = None, ttl_hours: int = DEFAULT_CACHE_TTL_HOURS):
        if cache_dir is None:
            # Default to backend/cache/search
            backend_dir = Path(__file__).resolve().parent.parent.parent
            cache_dir = backend_dir / "cache" / "search"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_hours * 3600

    def _cache_key(self, query: str, provider: str) -> str:
        """Generate cache key from query and provider."""
        key = f"{provider}:{query}".lower()
        return hashlib.md5(key.encode()).hexdigest()

    def _cache_path(self, cache_key: str) -> Path:
        return self.cache_dir / f"{cache_key}.json"

    def get(self, query: str, provider: str) -> Optional[Any]:
        """Get cached result if valid."""
        cache_key = self._cache_key(query, provider)
        path = self._cache_path(cache_key)
        
        if not path.exists():
            return None
        
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            cached_at = data.get("cached_at", 0)
            if time.time() - cached_at > self.ttl_seconds:
                path.unlink(missing_ok=True)
                return None
            return data.get("results")
        except Exception:
            return None

    def set(self, query: str, provider: str, results: Any) -> None:
        """Cache search results."""
        cache_key = self._cache_key(query, provider)
        path = self._cache_path(cache_key)
        
        try:
            data = {
                "query": query,
                "provider": provider,
                "cached_at": time.time(),
                "results": results,
            }
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass  # Silently fail caching


# Global cache instance
_cache: Optional[SearchCache] = None


def get_cache() -> SearchCache:
    """Get or create the global cache instance."""
    global _cache
    if _cache is None:
        _cache = SearchCache()
    return _cache


class SearchProvider(ABC):
    """Abstract base class for search providers."""

    name: str = "base"
    requires_api_key: bool = False

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.cache = get_cache()

    @abstractmethod
    def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Perform a search query."""
        pass

    def _check_api_key(self) -> None:
        """Raise error if API key is required but missing."""
        if self.requires_api_key and not self.api_key:
            raise APIKeyError(f"{self.name} requires an API key")

    def _cached_search(self, query: str, search_func: Callable, **kwargs) -> Any:
        """Search with caching."""
        cached = self.cache.get(query, self.name)
        if cached is not None:
            return cached
        
        results = search_func(query, **kwargs)
        self.cache.set(query, self.name, results)
        return results


def safe_request(
    url: str,
    method: str = "GET",
    timeout: int = DEFAULT_TIMEOUT_S,
    headers: Optional[Dict[str, str]] = None,
    **kwargs
) -> requests.Response:
    """Make a safe HTTP request with error handling."""
    final_headers = HEADERS.copy()
    if headers:
        final_headers.update(headers)
    
    try:
        response = requests.request(
            method=method,
            url=url,
            headers=final_headers,
            timeout=timeout,
            **kwargs
        )
        response.raise_for_status()
        return response
    except requests.exceptions.Timeout:
        raise SearchError(f"Request timed out: {url}")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            raise RateLimitError(f"Rate limit exceeded for {get_domain(url)}")
        raise SearchError(f"HTTP error {e.response.status_code}: {url}")
    except requests.exceptions.RequestException as e:
        raise SearchError(f"Request failed: {e}")
