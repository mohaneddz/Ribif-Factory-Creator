"""URL utilities for canonicalization, deduplication, and domain scoring."""

from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


def canonicalize_url(url: str) -> str:
    """Canonicalize URL by removing UTM params, sorting query params, lowercasing domain."""
    try:
        parsed = urlparse(url.strip())
        
        # Lowercase domain
        netloc = parsed.netloc.lower().replace("www.", "")
        
        # Remove UTM and tracking params
        params = parse_qs(parsed.query, keep_blank_values=False)
        utm_params = {"utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term", "fbclid", "gclid"}
        filtered_params = {k: v for k, v in params.items() if k.lower() not in utm_params}
        
        # Reconstruct query string (sorted for consistency)
        query = urlencode(sorted(filtered_params.items()), doseq=True) if filtered_params else ""
        
        # Reconstruct URL
        canonical = urlunparse((
            parsed.scheme.lower(),
            netloc,
            parsed.path.rstrip("/"),  # Remove trailing slash
            parsed.params,
            query,
            ""  # Remove fragment
        ))
        
        return canonical
    except Exception as e:
        logger.debug(f"Error canonicalizing {url}: {e}")
        return url.lower()


def get_domain(url: str) -> str:
    """Extract domain from URL (without www)."""
    try:
        parsed = urlparse(url.strip())
        domain = parsed.netloc.lower().replace("www.", "")
        return domain
    except Exception:
        return ""


def get_base_domain(url: str) -> str:
    """Extract base domain (e.g., 'example.com' from 'subdomain.example.com')."""
    domain = get_domain(url)
    parts = domain.split(".")
    # Return last 2 parts (domain.tld) for most cases
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return domain


def deduplicate_search_results(search_results: list[Dict]) -> list[Dict]:
    """Deduplicate search results by canonical URL and base domain.
    
    Keeps the first occurrence of each canonical URL.
    Returns list with duplicates removed.
    """
    seen_urls = set()
    seen_domains = {}  # domain -> first_result (for grouping)
    deduped = []
    
    for result in search_results:
        url = result.get("url", "")
        if not url:
            continue
        
        canonical = canonicalize_url(url)
        base_domain = get_base_domain(canonical)
        
        if canonical not in seen_urls:
            seen_urls.add(canonical)
            if base_domain not in seen_domains:
                seen_domains[base_domain] = result
            deduped.append(result)
    
    return deduped


def score_domain_trust(url: str, trusted_domains: set, low_trust_domains: set, marketplace_domains: set) -> float:
    """Score domain trustworthiness (0.0-1.0).
    
    Returns:
    - 1.0 for trusted OEM/manufacturer domains
    - 0.6 for neutral domains
    - 0.4 for low-trust domains
    - 0.1 for marketplace domains
    - 0.0 for skipped domains (returns 0 but can be filtered earlier)
    """
    domain = get_domain(url)
    base_domain = get_base_domain(url)
    
    # Check against domain lists (exact match or base domain)
    if domain in marketplace_domains or base_domain in marketplace_domains:
        return 0.1
    if domain in low_trust_domains or base_domain in low_trust_domains:
        return 0.4
    if domain in trusted_domains or base_domain in trusted_domains:
        return 1.0
    
    # Default neutral
    return 0.6


def should_skip_url(url: str, marketplace_domains: set, skip_extensions: set) -> bool:
    """Check if URL should be skipped (marketplace or unsupported file type)."""
    # Check file extension
    parsed = urlparse(url.lower())
    path = parsed.path
    for ext in skip_extensions:
        if path.endswith(ext):
            return True
    
    # Check marketplace
    domain = get_domain(url)
    base_domain = get_base_domain(url)
    if domain in marketplace_domains or base_domain in marketplace_domains:
        return False  # We keep it but downrank; can return True to skip entirely
    
    return False
