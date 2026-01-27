"""
Alibaba.com product and supplier scraper.

Scrapes industrial machinery listings from Alibaba for real supplier data.
No API key required, but rate limiting is important to avoid blocks.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus, urljoin

from .base import (
    SearchProvider,
    ProductResult,
    SupplierResult,
    SearchError,
    safe_request,
    rate_limit,
    HEADERS,
)

ALIBABA_SEARCH_URL = "https://www.alibaba.com/trade/search"


class AlibabaSearch(SearchProvider):
    """Alibaba.com product/supplier scraper."""

    name = "alibaba"
    requires_api_key = False

    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """Implement abstract search method (delegates to search_products)."""
        products = self.search_products(query, max_results)
        # Convert ProductResult to SearchResult for compatibility
        return [
            SearchResult(
                title=p.name,
                url=p.url,
                snippet=f"Price: {p.price} | Supplier: {p.supplier_name}",
                source="alibaba"
            )
            for p in products
        ]

    @rate_limit(min_gap_s=3.0)  # Be polite to Alibaba
    def search_products(self, query: str, max_results: int = 10) -> List[ProductResult]:
        """Search Alibaba for products."""
        try:
            response = safe_request(
                url=f"{ALIBABA_SEARCH_URL}?SearchText={quote_plus(query)}",
                timeout=20,
            )
            return self._parse_search_results(response.text, max_results)
        except Exception as e:
            raise SearchError(f"Alibaba search failed: {e}")

    def _parse_search_results(self, html: str, max_results: int) -> List[ProductResult]:
        """Parse Alibaba search results HTML."""
        results = []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            
            # Alibaba uses various class names, try common patterns
            product_cards = soup.select("[class*='organic-offer-wrapper'], [class*='J-offer-wrapper'], .list-no-v2-item")
            
            for card in product_cards[:max_results]:
                try:
                    # Extract product name
                    title_elem = card.select_one("[class*='title'], h2 a, .elements-title-normal")
                    name = title_elem.get_text(strip=True) if title_elem else ""
                    
                    # Extract URL
                    link_elem = card.select_one("a[href*='alibaba.com']") or title_elem
                    url = ""
                    if link_elem:
                        href = link_elem.get("href", "")
                        if href.startswith("//"):
                            href = "https:" + href
                        elif href.startswith("/"):
                            href = "https://www.alibaba.com" + href
                        url = href
                    
                    # Extract price
                    price_elem = card.select_one("[class*='price'], .elements-offer-price-normal")
                    price_text = price_elem.get_text(strip=True) if price_elem else ""
                    price_min, price_max = self._parse_price_range(price_text)
                    
                    # Extract supplier
                    supplier_elem = card.select_one("[class*='company'], [class*='supplier'], .seller-name")
                    supplier_name = supplier_elem.get_text(strip=True) if supplier_elem else ""
                    
                    # Extract image
                    img_elem = card.select_one("img[src*='alicdn']")
                    image_url = ""
                    if img_elem:
                        image_url = img_elem.get("src") or img_elem.get("data-src", "")
                        if image_url.startswith("//"):
                            image_url = "https:" + image_url
                    
                    # Extract MOQ
                    moq_elem = card.select_one("[class*='moq'], [class*='min-order']")
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
                            source="alibaba",
                        ))
                except Exception:
                    continue
        except ImportError:
            pass
        except Exception:
            pass
        
        return results

    def _parse_price_range(self, price_text: str) -> tuple[float, float]:
        """Parse price range from text like '$100.00 - $500.00'."""
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
    def get_supplier_details(self, supplier_url: str) -> Optional[SupplierResult]:
        """Get detailed supplier information from their Alibaba page."""
        try:
            response = safe_request(url=supplier_url, timeout=20)
            return self._parse_supplier_page(response.text, supplier_url)
        except Exception:
            return None

    def _parse_supplier_page(self, html: str, url: str) -> Optional[SupplierResult]:
        """Parse supplier profile page."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            
            name_elem = soup.select_one("[class*='company-name'], .company-name-txt")
            name = name_elem.get_text(strip=True) if name_elem else ""
            
            region_elem = soup.select_one("[class*='location'], .region-txt")
            region = region_elem.get_text(strip=True) if region_elem else ""
            
            # Try to find contact info (often hidden, but sometimes visible)
            email = ""
            phone = ""
            
            email_match = re.search(r'[\w.-]+@[\w.-]+\.\w+', html)
            if email_match:
                email = email_match.group(0)
            
            phone_match = re.search(r'\+?\d[\d\s\-()]{8,}', html)
            if phone_match:
                phone = phone_match.group(0).strip()
            
            if name:
                return SupplierResult(
                    supplier_name=name,
                    website=url,
                    region=region,
                    email_address=email,
                    phone_number=phone,
                    source="alibaba",
                    source_url=url,
                    relevance_score=0.7,
                )
        except Exception:
            pass
        return None


# Convenience functions
_default_alibaba: Optional[AlibabaSearch] = None


def _get_alibaba() -> AlibabaSearch:
    global _default_alibaba
    if _default_alibaba is None:
        _default_alibaba = AlibabaSearch()
    return _default_alibaba


def search_products(query: str, max_results: int = 10) -> List[ProductResult]:
    """Search Alibaba products."""
    return _get_alibaba().search_products(query, max_results)


def get_supplier_details(supplier_url: str) -> Optional[SupplierResult]:
    """Get supplier details from Alibaba URL."""
    return _get_alibaba().get_supplier_details(supplier_url)
