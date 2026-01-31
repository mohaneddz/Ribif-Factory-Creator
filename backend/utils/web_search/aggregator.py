"""
Unified search aggregator combining all search providers.

Provides high-level functions for machine/supplier search that
intelligently query multiple sources and merge results.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from .base import (
    SearchResult,
    ImageResult,
    SupplierResult,
    ProductResult,
    MachineSpecsResult,
    SearchError,
    get_cache,
)

# Import all providers
from . import duckduckgo
from . import alibaba
from . import made_in_china
from . import indiamart
from . import europages

# Conditional imports for API-key providers
_serper_available = False
_bing_available = False

try:
    from . import serper
    _serper_available = bool(os.getenv("SERPER_API_KEY"))
except ImportError:
    pass

try:
    from . import bing
    _bing_available = bool(os.getenv("BING_API_KEY"))
except ImportError:
    pass


def search_machine_suppliers(
    machine_name: str,
    machine_type: str = "",
    region: str = "Algeria",
    max_results_per_source: int = 5,
    max_total_results: int = 15,
) -> List[SupplierResult]:
    """
    Search for real suppliers of an industrial machine across multiple sources.
    
    Args:
        machine_name: Name of the machine (e.g., "CNC Milling Machine")
        machine_type: Optional type classification
        region: Target import region for customs info
        max_results_per_source: Max results to fetch from each source
        max_total_results: Max total results to return
    
    Returns:
        List of SupplierResult from real web sources
    """
    cache = get_cache()
    cache_key = f"suppliers:{machine_name}:{machine_type}:{region}"
    cached = cache.get(cache_key, "aggregator")
    if cached:
        return [SupplierResult(**r) if isinstance(r, dict) else r for r in cached]
    
    all_suppliers: List[SupplierResult] = []
    query = f"{machine_name} {machine_type}".strip()
    
    # Parallel search across B2B marketplaces
    def search_alibaba():
        try:
            products = alibaba.search_products(query, max_results_per_source)
            suppliers = []
            for p in products:
                if p.supplier_name:
                    suppliers.append(SupplierResult(
                        supplier_name=p.supplier_name,
                        website=p.supplier_url or p.url,
                        region="China",
                        price_estimate=p.price,
                        price_type="FOB" if p.price else "Contact supplier",
                        source="alibaba",
                        source_url=p.url,
                        customs_algeria_info=f"Import from China. FOB pricing. HS code classification required for {machine_name}.",
                        relevance_score=0.7,
                    ))
            return suppliers
        except Exception:
            return []
    
    def search_made_in_china():
        try:
            products = made_in_china.search_machines(query, max_results_per_source)
            suppliers = []
            for p in products:
                if p.supplier_name:
                    suppliers.append(SupplierResult(
                        supplier_name=p.supplier_name,
                        website=p.url,
                        region="China",
                        price_estimate=p.price,
                        price_type="FOB",
                        source="made_in_china",
                        source_url=p.url,
                        customs_algeria_info=f"Import from China. Typical delivery 4-8 weeks. Customs duties apply.",
                        relevance_score=0.7,
                    ))
            return suppliers
        except Exception:
            return []
    
    def search_indiamart():
        try:
            products = indiamart.search_products(query, max_results_per_source)
            suppliers = []
            for p in products:
                if p.supplier_name:
                    suppliers.append(SupplierResult(
                        supplier_name=p.supplier_name,
                        website=p.url,
                        region="India",
                        price_estimate=p.price,
                        price_currency="INR",
                        price_type="EXW",
                        source="indiamart",
                        source_url=p.url,
                        customs_algeria_info="Import from India. Competitive pricing. 3-6 week lead time typical.",
                        relevance_score=0.65,
                    ))
            return suppliers
        except Exception:
            return []
    
    def search_europages():
        try:
            return europages.search_companies(query, max_results=max_results_per_source)
        except Exception:
            return []
    
    # Execute searches in parallel
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(search_alibaba): "alibaba",
            executor.submit(search_made_in_china): "made_in_china",
            executor.submit(search_indiamart): "indiamart",
            executor.submit(search_europages): "europages",
        }
        
        for future in as_completed(futures):
            try:
                results = future.result(timeout=30)
                all_suppliers.extend(results)
            except Exception:
                continue
    
    # Deduplicate by supplier name (case-insensitive)
    seen_names = set()
    unique_suppliers = []
    for s in all_suppliers:
        name_key = s.supplier_name.lower().strip()
        if name_key not in seen_names:
            seen_names.add(name_key)
            unique_suppliers.append(s)
    
    # Sort by relevance score
    unique_suppliers.sort(key=lambda x: x.relevance_score, reverse=True)
    final_results = unique_suppliers[:max_total_results]
    
    # Cache results
    cache.set(cache_key, "aggregator", [r.to_dict() for r in final_results])
    
    return final_results


def search_machine_specs(
    machine_name: str,
    manufacturer: str = "",
    max_search_results: int = 10,
) -> MachineSpecsResult:
    """
    Search for machine specifications and documentation.
    
    Args:
        machine_name: Name of the machine
        manufacturer: Optional manufacturer name
        max_search_results: Max search results to analyze
    
    Returns:
        MachineSpecsResult with specifications, datasheets, images
    """
    cache = get_cache()
    cache_key = f"specs:{machine_name}:{manufacturer}"
    cached = cache.get(cache_key, "aggregator_specs")
    if cached:
        return MachineSpecsResult(**cached) if isinstance(cached, dict) else cached
    
    result = MachineSpecsResult(
        manufacturer=manufacturer,
        model=machine_name,
    )
    
    query = f"{manufacturer} {machine_name} specifications datasheet".strip()
    
    # Try web search for specifications
    search_results: List[SearchResult] = []
    
    # Try Serper first (best quality)
    if _serper_available:
        try:
            search_results = serper.search_google(query, max_search_results)
        except Exception:
            pass
    
    # Fall back to DuckDuckGo
    if not search_results:
        try:
            search_results = duckduckgo.web_search(query, max_search_results)
        except Exception:
            pass
    
    # Extract datasheet URLs and manufacturer website
    for sr in search_results:
        url_lower = sr.url.lower()
        
        # Datasheet PDFs
        if url_lower.endswith(".pdf") or "datasheet" in url_lower or "spec" in url_lower:
            if sr.url not in result.datasheet_urls:
                result.datasheet_urls.append(sr.url)
        
        # Manufacturer website (look for official domain)
        if manufacturer and manufacturer.lower().replace(" ", "") in url_lower.replace(" ", ""):
            if not result.manufacturer_website:
                result.manufacturer_website = sr.url
        
        result.sources.append(sr.url)
    
    # Limit datasheet URLs
    result.datasheet_urls = result.datasheet_urls[:5]
    result.sources = result.sources[:10]
    
    # Cache result
    cache.set(cache_key, "aggregator_specs", result.to_dict())
    
    return result


def search_machine_images(
    machine_name: str,
    manufacturer: str = "",
    max_results: int = 8,
) -> List[ImageResult]:
    """
    Search for real machine images from the web.
    
    Args:
        machine_name: Name of the machine
        manufacturer: Optional manufacturer name
        max_results: Maximum number of images to return
    
    Returns:
        List of ImageResult with real machine photos
    """
    cache = get_cache()
    cache_key = f"images:{machine_name}:{manufacturer}"
    cached = cache.get(cache_key, "aggregator_images")
    if cached:
        return [ImageResult(**r) if isinstance(r, dict) else r for r in cached]
    
    query = f"{manufacturer} {machine_name} industrial machine".strip()
    images: List[ImageResult] = []
    
    # Try Serper for Google Images
    if _serper_available:
        try:
            images = serper.search_images(query, max_results)
        except Exception:
            pass
    
    # Fall back to Bing Images
    if not images and _bing_available:
        try:
            images = bing.search_images(query, max_results)
        except Exception:
            pass
    
    # Also check Alibaba product images
    if len(images) < max_results:
        try:
            products = alibaba.search_products(f"{machine_name} {manufacturer}".strip(), 5)
            for p in products:
                if p.image_url and len(images) < max_results:
                    images.append(ImageResult(
                        url=p.image_url,
                        title=p.name,
                        source_url=p.url,
                        source="alibaba",
                    ))
        except Exception:
            pass
    
    # Cache results
    cache.set(cache_key, "aggregator_images", [r.to_dict() for r in images[:max_results]])
    
    return images[:max_results]


def search_pricing_info(
    machine_name: str,
    machine_type: str = "",
    region: str = "Algeria",
) -> Dict[str, Any]:
    """
    Search for pricing information across multiple sources.
    
    Returns aggregated pricing data with ranges and sources.
    """
    cache = get_cache()
    cache_key = f"pricing:{machine_name}:{machine_type}:{region}"
    cached = cache.get(cache_key, "aggregator_pricing")
    if cached:
        return cached
    
    query = f"{machine_name} {machine_type}".strip()
    prices: List[Dict[str, Any]] = []
    
    # Search Alibaba
    try:
        alibaba_products = alibaba.search_products(query, 10)
        for p in alibaba_products:
            if p.price_min > 0:
                prices.append({
                    "source": "alibaba",
                    "price_min": p.price_min,
                    "price_max": p.price_max,
                    "currency": p.currency,
                    "price_text": p.price,
                    "product_name": p.name,
                    "url": p.url,
                })
    except Exception:
        pass
    
    # Search Made-in-China
    try:
        mic_products = made_in_china.search_machines(query, 10)
        for p in mic_products:
            if p.price_min > 0:
                prices.append({
                    "source": "made_in_china",
                    "price_min": p.price_min,
                    "price_max": p.price_max,
                    "currency": p.currency,
                    "price_text": p.price,
                    "product_name": p.name,
                    "url": p.url,
                })
    except Exception:
        pass
    
    # Search IndiaMart
    try:
        india_products = indiamart.search_products(query, 10)
        for p in india_products:
            if p.price_min > 0:
                # Convert INR to USD approximately (rough conversion)
                usd_min = p.price_min / 83.0  # Approximate exchange rate
                usd_max = p.price_max / 83.0
                prices.append({
                    "source": "indiamart",
                    "price_min": usd_min,
                    "price_max": usd_max,
                    "currency": "USD",
                    "original_currency": "INR",
                    "original_price_min": p.price_min,
                    "original_price_max": p.price_max,
                    "price_text": p.price,
                    "product_name": p.name,
                    "url": p.url,
                })
    except Exception:
        pass
    
    # Calculate summary
    all_min = [p["price_min"] for p in prices if p.get("price_min", 0) > 0]
    all_max = [p["price_max"] for p in prices if p.get("price_max", 0) > 0]
    
    result = {
        "machine": machine_name,
        "prices": prices,
        "price_range": {
            "min": min(all_min) if all_min else 0,
            "max": max(all_max) if all_max else 0,
            "currency": "USD",
        },
        "median_price": sorted(all_min)[len(all_min)//2] if all_min else 0,
        "sources_count": len(set(p["source"] for p in prices)),
        "total_listings": len(prices),
    }
    
    cache.set(cache_key, "aggregator_pricing", result)
    return result


def find_manufacturer_website(manufacturer_name: str) -> Optional[str]:
    """
    Find the official website for a manufacturer.
    """
    if not manufacturer_name:
        return None
    
    cache = get_cache()
    cached = cache.get(manufacturer_name, "manufacturer_website")
    if cached:
        return cached
    
    query = f"{manufacturer_name} official website"
    
    # Try search engines
    results: List[SearchResult] = []
    
    if _serper_available:
        try:
            results = serper.search_google(query, 5)
        except Exception:
            pass
    
    if not results:
        try:
            results = duckduckgo.web_search(query, 5)
        except Exception:
            pass
    
    # Look for official domain
    manufacturer_clean = manufacturer_name.lower().replace(" ", "").replace("-", "")
    
    for sr in results:
        domain = sr.url.lower()
        # Check if domain contains manufacturer name
        if manufacturer_clean in domain.replace(".", "").replace("-", ""):
            cache.set(manufacturer_name, "manufacturer_website", sr.url)
            return sr.url
    
    # Return first result as fallback
    if results:
        cache.set(manufacturer_name, "manufacturer_website", results[0].url)
        return results[0].url
    
    return None
