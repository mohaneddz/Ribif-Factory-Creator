"""
Europages B2B directory search.

European B2B business directory with company profiles.
No API key required, uses HTML scraping.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

from .base import (
    SearchResult,
    SupplierResult,
    SearchError,
    safe_request,
    get_cache,
    rate_limit,
)

EUROPAGES_SEARCH_URL = "https://www.europages.com/search"


@rate_limit(min_gap_s=2.0)
def search_companies(query: str, country: Optional[str] = None, max_results: int = 10) -> List[SupplierResult]:
    """Search Europages for companies/suppliers."""
    cache_key = f"{query}:{country or 'all'}"
    cache = get_cache()
    cached = cache.get(cache_key, "europages_companies")
    if cached:
        return [SupplierResult(**r) if isinstance(r, dict) else r for r in cached]
    
    try:
        params = f"?q={quote_plus(query)}"
        if country:
            params += f"&country={quote_plus(country)}"
        
        response = safe_request(url=f"{EUROPAGES_SEARCH_URL}{params}", timeout=20)
        results = _parse_search_results(response.text, max_results)
        cache.set(cache_key, "europages_companies", [r.to_dict() for r in results])
        return results
    except Exception as e:
        raise SearchError(f"Europages search failed: {e}")


def _parse_search_results(html: str, max_results: int) -> List[SupplierResult]:
    """Parse Europages search results."""
    results = []
    
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        
        # Company cards
        company_items = soup.select("[class*='company-card'], .search-company-item, .company-item")
        
        for item in company_items[:max_results]:
            try:
                # Company name
                name_elem = item.select_one("h2, h3, [class*='company-name']")
                name = name_elem.get_text(strip=True) if name_elem else ""
                
                # URL
                link_elem = item.select_one("a[href*='europages.com']")
                url = ""
                if link_elem:
                    url = link_elem.get("href", "")
                    if url.startswith("/"):
                        url = "https://www.europages.com" + url
                
                # Region/Location
                location_elem = item.select_one("[class*='location'], [class*='country']")
                region = location_elem.get_text(strip=True) if location_elem else ""
                
                # Description/Activity
                desc_elem = item.select_one("[class*='activity'], [class*='description']")
                notes = desc_elem.get_text(strip=True) if desc_elem else ""
                
                if name and url:
                    results.append(SupplierResult(
                        supplier_name=name,
                        website=url,
                        region=region,
                        notes=notes,
                        source="europages",
                        source_url=url,
                        customs_algeria_info="EU supplier. Standard export documentation available. EURO1 certificate may apply.",
                        relevance_score=0.75,
                    ))
            except Exception:
                continue
    except ImportError:
        pass
    except Exception:
        pass
    
    return results


@rate_limit(min_gap_s=2.0)
def get_company_details(company_url: str) -> Optional[SupplierResult]:
    """Get detailed company information from Europages profile."""
    cache = get_cache()
    cached = cache.get(company_url, "europages_company")
    if cached:
        return SupplierResult(**cached) if isinstance(cached, dict) else cached
    
    try:
        response = safe_request(url=company_url, timeout=20)
        result = _parse_company_page(response.text, company_url)
        if result:
            cache.set(company_url, "europages_company", result.to_dict())
        return result
    except Exception:
        return None


def _parse_company_page(html: str, url: str) -> Optional[SupplierResult]:
    """Parse company profile page."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        
        # Company name
        name_elem = soup.select_one("h1, [class*='company-name']")
        name = name_elem.get_text(strip=True) if name_elem else ""
        
        # Official website
        website = url
        site_elem = soup.select_one("a[href*='http'][rel='nofollow']")
        if site_elem:
            external_url = site_elem.get("href", "")
            if external_url and "europages" not in external_url:
                website = external_url
        
        # Location
        location_elem = soup.select_one("[class*='address'], [class*='location']")
        region = location_elem.get_text(strip=True) if location_elem else ""
        
        # Contact info
        email = ""
        phone = ""
        
        email_match = re.search(r'[\w.-]+@[\w.-]+\.\w+', html)
        if email_match:
            email = email_match.group(0)
        
        # European phone patterns
        phone_match = re.search(r'\+\d{2}[\d\s\-()]{8,}', html)
        if phone_match:
            phone = phone_match.group(0).strip()
        
        # Activity/Description
        desc_elem = soup.select_one("[class*='activity'], [class*='description'], .company-presentation")
        notes = ""
        if desc_elem:
            notes = desc_elem.get_text(strip=True)[:300]
        
        if name:
            return SupplierResult(
                supplier_name=name,
                website=website,
                region=region,
                email_address=email,
                phone_number=phone,
                notes=notes,
                source="europages",
                source_url=url,
                customs_algeria_info="EU supplier. Standard export documentation. May qualify for preferential tariffs under EU-Algeria agreements.",
                relevance_score=0.8,
                verified=True,  # Europages verifies company registrations
            )
    except Exception:
        pass
    return None
