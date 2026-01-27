"""Web scraping utilities with trafilatura + structured data extraction.

Improvements over basic BeautifulSoup:
- trafilatura for intelligent main content extraction
- JSON-LD + Open Graph meta tag extraction
- Semantic relevance scoring
- Connection pooling with HTTP/2
- TTL caching + retry with exponential backoff
"""

from typing import List, Dict, Optional
import httpx
from bs4 import BeautifulSoup
import re
import logging
import asyncio
import time
from urllib.parse import urlparse

try:
    import trafilatura
    HAS_TRAFILATURA = True
except ImportError:
    HAS_TRAFILATURA = False

from .web_utils import ContentExtractor

logger = logging.getLogger(__name__)

# Module-level shared client and cache
_http_client: Optional[httpx.AsyncClient] = None
_client_lock = asyncio.Lock()

# Simple in-memory cache: url -> (timestamp, result)
_cache: Dict[str, tuple] = {}
CACHE_TTL = 60 * 60  # 1 hour


async def _get_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        async with _client_lock:
            if _http_client is None:
                limits = httpx.Limits(max_connections=100, max_keepalive_connections=20)
                _http_client = httpx.AsyncClient(timeout=10.0, follow_redirects=True, http2=True, limits=limits)
    return _http_client


async def aclose_client() -> None:
    """Close the shared HTTP client (call on app shutdown)."""
    global _http_client
    if _http_client is not None:
        try:
            await _http_client.aclose()
        except Exception:
            pass
        _http_client = None


def _get_from_cache(url: str) -> Optional[Dict[str, Optional[str]]]:
    entry = _cache.get(url)
    if not entry:
        return None
    ts, value = entry
    if time.time() - ts > CACHE_TTL:
        del _cache[url]
        return None
    return value


def _set_cache(url: str, value: Dict[str, Optional[str]]) -> None:
    _cache[url] = (time.time(), value)


async def scrape_supplier_info(url: str, max_retries: int = 2) -> Dict[str, Optional[str]]:
    """Scrape supplier website with trafilatura + structured extraction.

    Uses shared HTTP client, retries, and caching for better performance.
    Extracts both content and structured data (JSON-LD, OG tags).
    """
    # Cache lookup
    cached = _get_from_cache(url)
    if cached:
        return cached

    client = await _get_client()
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    content_extractor = ContentExtractor()

    last_exc = None
    for attempt in range(1, max_retries + 2):
        try:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            html_text = resp.text

            # Extract main content with trafilatura if available
            main_content = None
            if HAS_TRAFILATURA:
                try:
                    main_content = trafilatura.extract(html_text, include_comments=False, favor_precision=True)
                except Exception as e:
                    logger.debug(f"Trafilatura extraction failed for {url}: {e}")

            # Fallback to BeautifulSoup if trafilatura unavailable or fails
            if not main_content:
                soup = BeautifulSoup(html_text, "lxml")
                # Extract body content
                body = soup.find("body") or soup
                main_content = body.get_text(separator=" ", strip=True) if body else html_text

            soup = BeautifulSoup(html_text, "lxml")

            # Extract company name
            company_name = None
            for selector in ["h1", ".company-name", "[class*='company']", "title"]:
                el = soup.select_one(selector)
                if el:
                    company_name = el.get_text(strip=True)
                    break
            if not company_name:
                domain = urlparse(url).netloc
                company_name = domain.replace("www.", "").split(".")[0].title()

            # Extract structured data (JSON-LD, meta tags, etc.)
            structured_data = content_extractor.extract_structured_fields(html_text)
            cleaned_content, semantic_score, _ = content_extractor.extract_relevant_sections(
                main_content, html_text, query=company_name
            )

            # Extract email
            email = structured_data.get("email")
            if not email:
                email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
                emails = re.findall(email_pattern, html_text)
                if emails:
                    contact_emails = [e for e in emails if not any(skip in e.lower() for skip in ["noreply", "no-reply", "privacy", "legal"])]
                    email = contact_emails[0] if contact_emails else emails[0]

            # Extract phone
            phone = structured_data.get("contact")
            if not phone:
                phone_patterns = [r"\+?[\d\s\-\(\)]{10,}", r"\+?\d{1,3}[\s\-]?\d{1,4}[\s\-]?\d{1,4}[\s\-]?\d{1,9}"]
                for pattern in phone_patterns:
                    phones = re.findall(pattern, html_text)
                    if phones:
                        phone = phones[0].strip()
                        break

            # Extract location
            location = structured_data.get("address") or structured_data.get("city")
            if not location:
                for keyword in ["address", "location", "headquarters", "office"]:
                    el = soup.find(string=re.compile(keyword, re.I))
                    if el:
                        parent = el.find_parent()
                        if parent:
                            location = parent.get_text(strip=True)[:200]
                            break

            # Price info
            price_info = structured_data.get("price")
            if not price_info:
                price_pattern = r"[\$€£¥]\s?[\d,]+\.?\d*"
                prices = re.findall(price_pattern, html_text)
                if prices:
                    price_info = prices[0]

            result = {
                "company_name": company_name,
                "email": email,
                "phone": phone,
                "location": location,
                "price_info": price_info,
                "url": url,
                "semantic_score": semantic_score,  # New field
                "description": structured_data.get("description"),  # From JSON-LD
            }

            # Cache and return
            _set_cache(url, result)
            return result

        except Exception as e:
            last_exc = e
            logger.debug(f"Attempt {attempt} failed for {url}: {e}")
            # Exponential backoff
            await asyncio.sleep(0.5 * (2 ** (attempt - 1)))
            continue

    logger.error(f"Error scraping {url}: {last_exc}")
    return {
        "company_name": None,
        "email": None,
        "phone": None,
        "location": None,
        "price_info": None,
        "url": url,
        "semantic_score": 0.0,
        "description": None,
    }


async def scrape_multiple_urls(urls: List[str], max_concurrent: Optional[int] = None) -> List[Dict[str, Optional[str]]]:
    """Scrape multiple URLs with concurrency control and efficient client reuse.

    max_concurrent defaults to min(10, len(urls)).
    """
    if not urls:
        return []

    if max_concurrent is None:
        max_concurrent = min(10, max(2, len(urls)))

    semaphore = asyncio.Semaphore(max_concurrent)

    async def _scrape(url: str):
        async with semaphore:
            return await scrape_supplier_info(url)

    tasks = [asyncio.create_task(_scrape(u)) for u in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    out: List[Dict[str, Optional[str]]] = []
    for r in results:
        if isinstance(r, Exception):
            logger.error(f"Scraping error: {r}")
        else:
            out.append(r)

    return out

