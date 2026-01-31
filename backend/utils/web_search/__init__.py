"""
Web Search Utilities for RIBIF Backend

This module provides unified access to multiple search providers
for real-world data enrichment of industrial machinery and suppliers.
"""

from .base import SearchResult, ImageResult, SupplierResult, ProductResult, SearchError
from .aggregator import (
    search_machine_suppliers,
    search_machine_specs,
    search_machine_images,
    search_pricing_info,
)

__all__ = [
    "SearchResult",
    "ImageResult", 
    "SupplierResult",
    "ProductResult",
    "SearchError",
    "search_machine_suppliers",
    "search_machine_specs",
    "search_machine_images",
    "search_pricing_info",
]
