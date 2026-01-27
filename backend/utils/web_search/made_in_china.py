"""
Made-in-China.com product scraper.

Specialized in industrial machinery exports from China.
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
    rate_limit,
)

MADE_IN_CHINA_SEARCH_URL = "https://www.made-in-china.com/multi-search"


@rate_limit(min_gap_s=3.0)
def search_machines(query: str, max_results: int = 10) -> List[ProductResult]:
    """Search Made-in-China for industrial machines."""
    try:
        search_url = f"{MADE_IN_CHINA_SEARCH_URL}/{quote_plus(query)}/p1.html"
        response = safe_request(url=search_url, timeout=20)
        results = _parse_search_results(response.text, max_results)
        return results
    except Exception as e:
        raise SearchError(f"Made-in-China search failed: {e}")


def _parse_search_results(html: str, max_results: int) -> List[ProductResult]:
    """Parse Made-in-China search results."""
    results = []
    
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        
        # Product cards
        product_items = soup.select(".product-item, .pro-item, [class*='product-box']")
        
        for item in product_items[:max_results]:
            try:
                # Product name
                title_elem = item.select_one("h2 a, .product-item-title a, [class*='title'] a")
                name = title_elem.get_text(strip=True) if title_elem else ""
                
                # URL
                url = ""
                if title_elem:
                    href = title_elem.get("href", "")
                    if href.startswith("//"):
                        href = "https:" + href
                    elif href.startswith("/"):
                        href = "https://www.made-in-china.com" + href
                    url = href
                
                # Price
                price_elem = item.select_one("[class*='price'], .product-price")
                price_text = price_elem.get_text(strip=True) if price_elem else ""
                price_min, price_max = _parse_price(price_text)
                
                # Supplier
                supplier_elem = item.select_one("[class*='company'], [class*='supplier']")
                supplier_name = supplier_elem.get_text(strip=True) if supplier_elem else ""
                
                # Image
                img_elem = item.select_one("img")
                image_url = ""
                if img_elem:
                    image_url = img_elem.get("src") or img_elem.get("data-src", "")
                    if image_url.startswith("//"):
                        image_url = "https:" + image_url
                
                # MOQ
                moq_elem = item.select_one("[class*='moq'], [class*='min-order']")
                moq = moq_elem.get_text(strip=True) if moq_elem else ""
                
                if name and url:
                    results.append(ProductResult(
                        name=name,
                        url=url,
                        price=price_text,
                        price_min=price_min,
                        price_max=price_max,
                        currency="USD",
                        supplier_name=supplier_name,
                        image_url=image_url,
                        moq=moq,
                        source="made_in_china",
                    ))
            except Exception:
                continue
    except ImportError:
        pass
    except Exception:
        pass
    
    return results


def _parse_price(price_text: str) -> tuple[float, float]:
    """Parse price range from text."""
    try:
        numbers = re.findall(r'[\d,]+\.?\d*', price_text.replace(',', ''))
        if len(numbers) >= 2:
            return float(numbers[0]), float(numbers[1])
        elif len(numbers) == 1:
            val = float(numbers[0])
            return val, val
    except Exception:
        pass
    return 0.0, 0.0


@rate_limit(min_gap_s=3.0)
def get_manufacturer_info(url: str) -> Optional[SupplierResult]:
    """Get manufacturer information from product/supplier page."""
    try:
        response = safe_request(url=url, timeout=20)
        result = _parse_manufacturer_page(response.text, url)
        return result
    except Exception:
        return None


def _parse_manufacturer_page(html: str, url: str) -> Optional[SupplierResult]:
    """Parse manufacturer details from page."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        
        name_elem = soup.select_one("[class*='company-name'], .companyname, h1")
        name = name_elem.get_text(strip=True) if name_elem else ""
        
        region_elem = soup.select_one("[class*='location'], [class*='address']")
        region = region_elem.get_text(strip=True) if region_elem else "China"
        
        # Contact info
        email = ""
        phone = ""
        
        email_match = re.search(r'[\w.-]+@[\w.-]+\.\w+', html)
        if email_match:
            email = email_match.group(0)
        
        phone_match = re.search(r'\+86[\d\s\-]{8,}', html)
        if phone_match:
            phone = phone_match.group(0).strip()
        
        if name:
            return SupplierResult(
                supplier_name=name,
                website=url,
                region=region,
                email_address=email,
                phone_number=phone,
                source="made_in_china",
                source_url=url,
                customs_algeria_info="Standard import from China. HS code required. Typical lead time 4-8 weeks.",
                relevance_score=0.7,
            )
    except Exception:
        pass
    return None
