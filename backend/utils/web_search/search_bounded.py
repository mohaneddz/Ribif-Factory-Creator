# backend/utils/web_search/search_bounded.py
"""
Single-shot search helper for Module 4
NO agentic step loops - bounded web search only
"""

from typing import List, Dict, Any
from . import aggregator
from .base import SupplierResult
from utils.logger import get_logger

logger = get_logger(__name__)

def search_suppliers_once(
    machine: str,
    max_results: int = 3,
) -> List[Dict[str, str]]:
    """
    Single-shot supplier search.
    
    NO agentic loops.
    Returns up to max_results suppliers with name and domain only.
    
    Args:
        machine: Machine name to search for
        max_results: Maximum suppliers to return (default 3)
    
    Returns:
        List of dicts with keys: name, domain
    """
    try:
        query = f"{machine} manufacturer supplier distributor"
        
        # Single aggregated search
        results = aggregator.search_machine_suppliers(
            query=query,
            max_search_results=5,  # Search widely
            max_total_results=max_results  # But only return top N
        )
        
        # Extract names and domains only
        suppliers = []
        for result in results[:max_results]:
            suppliers.append({
                "name": result.supplier_name,
                "domain": result.website if result.website else None,
            })
        
        return suppliers
    
    except Exception as e:
        logger.error(f"Single-shot search failed for {machine}: {e}")
        return []
