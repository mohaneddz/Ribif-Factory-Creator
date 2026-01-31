"""
IndiaMart product scraper.

Large B2B marketplace with competitive pricing for industrial equipment.
No API key required, uses HTML scraping.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

from .base import (
    ProductResult,
    SupplierResult,
    SearchError,
    safe_request,
    get_cache,
    rate_limit,
)

INDIAMART_SEARCH_URL = "https://dir.indiamart.com/search.mp"


@rate_limit(min_gap_s=3.0)
def search_products(query: str, max_results: int = 10) -> List[ProductResult]:
    """Search IndiaMart for products."""
    cache = get_cache()
    cached = cache.get(query, "indiamart_products")
    if cached:
        return [ProductResult(**r) if isinstance(r, dict) else r for r in cached]
    
    try:
        search_url = f"{INDIAMART_SEARCH_URL}?ss={quote_plus(query)}"
        response = safe_request(url=search_url, timeout=20)
        results = _parse_search_results(response.text, max_results)
        cache.set(query, "indiamart_products", [r.to_dict() for r in results])
        return results
    except Exception as e:
        raise SearchError(f"IndiaMart search failed: {e}")


def _parse_search_results(html: str, max_results: int) -> List[ProductResult]:
    """Parse IndiaMart search results."""
    results = []
    
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        
        # Product cards
        product_items = soup.select(".prd-card, [class*='product-card'], .listing")
        
        for item in product_items[:max_results]:
            try:
                # Product name
                title_elem = item.select_one("h2, .prd-name, [class*='title']")
                name = title_elem.get_text(strip=True) if title_elem else ""
                
                # URL
                link_elem = item.select_one("a[href*='indiamart.com']")
                url = ""
                if link_elem:
                    url = link_elem.get("href", "")
                    if url.startswith("//"):
                        url = "https:" + url
                
                # Price
                price_elem = item.select_one("[class*='price'], .prd-price")
                price_text = price_elem.get_text(strip=True) if price_elem else ""
                price_min, price_max = _parse_price(price_text)
                
                # Supplier
                supplier_elem = item.select_one("[class*='company'], .cmpny-nm")
                supplier_name = supplier_elem.get_text(strip=True) if supplier_elem else ""
                
                # Image
                img_elem = item.select_one("img")
                image_url = ""
                if img_elem:
                    image_url = img_elem.get("src") or img_elem.get("data-src", "")
                    if image_url.startswith("//"):
                        image_url = "https:" + image_url
                
                if name and url:
                    results.append(ProductResult(
                        name=name,
                        url=url,
                        price=price_text,
                        price_min=price_min,
                        price_max=price_max,
                        currency="INR",
                        supplier_name=supplier_name,
                        image_url=image_url,
                        source="indiamart",
                    ))
            except Exception:
                continue
    except ImportError:
        pass
    except Exception:
        pass
    
    return results


def _parse_price(price_text: str) -> tuple[float, float]:
    """Parse price from text."""
    try:
        # Remove currency symbols and commas
        cleaned = re.sub(r'[₹,Rs.]', '', price_text)
        numbers = re.findall(r'[\d]+\.?\d*', cleaned)
        if len(numbers) >= 2:
            return float(numbers[0]), float(numbers[1])
        elif len(numbers) == 1:
            val = float(numbers[0])
            return val, val
    except Exception:
        pass
    return 0.0, 0.0


@rate_limit(min_gap_s=3.0)
def get_price_range(product_url: str) -> Optional[Dict[str, Any]]:
    """Get detailed price information from product page."""
    cache = get_cache()
    cached = cache.get(product_url, "indiamart_price")
    if cached:
        return cached
    
    try:
        response = safe_request(url=product_url, timeout=20)
        result = _parse_product_page(response.text)
        if result:
            cache.set(product_url, "indiamart_price", result)
        return result
    except Exception:
        return None


def _parse_product_page(html: str) -> Optional[Dict[str, Any]]:
    """Parse product page for pricing details."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        
        price_elem = soup.select_one("[class*='price']")
        price_text = price_elem.get_text(strip=True) if price_elem else ""
        
        min_order_elem = soup.select_one("[class*='min-order'], [class*='moq']")
        min_order = min_order_elem.get_text(strip=True) if min_order_elem else ""
        
        return {
            "price": price_text,
            "min_order": min_order,
            "currency": "INR",
            "source": "indiamart",
        }
    except Exception:
        pass
    return None


@rate_limit(min_gap_s=3.0)
def get_supplier_info(supplier_url: str) -> Optional[SupplierResult]:
    """Get supplier information from their IndiaMart profile."""
    cache = get_cache()
    cached = cache.get(supplier_url, "indiamart_supplier")
    if cached:
        return SupplierResult(**cached) if isinstance(cached, dict) else cached
    
    try:
        response = safe_request(url=supplier_url, timeout=20)
        result = _parse_supplier_page(response.text, supplier_url)
        if result:
            cache.set(supplier_url, "indiamart_supplier", result.to_dict())
        return result
    except Exception:
        return None


def _parse_supplier_page(html: str, url: str) -> Optional[SupplierResult]:
    """Parse supplier profile page."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        
        name_elem = soup.select_one("[class*='company-name'], h1")
        name = name_elem.get_text(strip=True) if name_elem else ""
        
        location_elem = soup.select_one("[class*='location'], [class*='address']")
        region = location_elem.get_text(strip=True) if location_elem else "India"
        
        # Contact
        email = ""
        phone = ""
        
        email_match = re.search(r'[\w.-]+@[\w.-]+\.\w+', html)
        if email_match:
            email = email_match.group(0)
        
        phone_match = re.search(r'\+91[\d\s\-]{8,}', html)
        if phone_match:
            phone = phone_match.group(0).strip()
        
        if name:
            return SupplierResult(
                supplier_name=name,
                website=url,
                region=region,
                email_address=email,
                phone_number=phone,
                price_currency="INR",
                source="indiamart",
                source_url=url,
                customs_algeria_info="Import from India. HS code classification required. Lead time typically 3-6 weeks.",
                relevance_score=0.65,
            )
    except Exception:
        pass
    return None
