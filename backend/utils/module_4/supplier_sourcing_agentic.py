"""
Agentic Supplier Sourcing Workflow for Industrial Machines (Algeria/North Africa)
==================================================================================

Goal: Return 15–30 qualified suppliers per machine (OEM + distributor + integrator + maintenance)
with deduplication, confidence scoring, and bounded execution.

Design:
    1. Normalize machine name → canonical term + keywords + synonyms
    2. Generate 3 query variants (OEM, distributor/dealer, maintenance/service)
    3. Execute searches with diversity control (cap 2 results per domain)
    4. Extract company info from candidate URLs + contact pages
    5. Classify suppliers (OEM/distributor/integrator/service) using signals
    6. Score and rank suppliers based on multiple factors
    7. Intelligent expansion: fetch dealer locators if <15 suppliers
    8. Deduplicate and return top 15-30 suppliers

Constraints:
    - Max 3 queries per machine
    - Max 12 pages fetched total per machine
    - Max 1 LLM call for final ranking (optional)
    - Hard timeout: 45s per machine
    - Configurable target: 15-30 suppliers (default 30 before filtering)
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError

from utils.logger import get_logger
from vertex_utils import generate_message

logger = get_logger(__name__)

# =========================================================
# CONFIGURATION
# =========================================================

@dataclass
class SourcingConfig:
    """Configuration for supplier sourcing workflow (UPGRADED for higher recall)."""
    
    # Query limits (UPGRADED)
    max_queries: int = 5  # Increased from 3 to 5
    max_results_per_query: int = 15  # Increased from 10 to 15
    
    # Page fetching limits (UPGRADED)
    max_pages_total: int = 20  # Increased from 12 to 20
    domain_diversity_cap: int = 3  # Increased from 2 to 3
    
    # Supplier targets (UPGRADED)
    target_suppliers_min: int = 15
    target_suppliers_max: int = 40  # Increased from 30 to 40
    candidate_cap: int = 80  # Increased from 30 to 80
    
    # Quality controls
    strictness_level: str = "balanced"
    min_confidence_score: float = 0.25  # Lowered from 0.3
    
    # Timeouts (UPGRADED)
    timeout_per_machine: float = 180.0  # 3 minutes (was 45s)
    timeout_per_page_fetch: float = 12.0  # seconds (was 10s)
    
    # LLM usage (UPGRADED)
    use_llm_ranking: bool = True  # Enable by default
    max_llm_calls: int = 3  # Increased: query planning + extraction + synthesis
    
    # Retry/backoff (NEW)
    max_retries: int = 3
    retry_backoff_base: float = 1.0
    retry_jitter: bool = True
    
    # Multi-pass search (NEW)
    enable_multipass: bool = True
    search_passes: int = 3
    
    # Fallback catalog (NEW)
    enable_fallback_catalog: bool = True
    fallback_catalog_threshold: int = 10
    
    # Regional focus
    target_regions: List[str] = field(default_factory=lambda: [
        "Algeria", "North Africa", "Maghreb", "Tunisia", "Morocco", 
        "Libya", "Egypt", "Middle East", "MENA"
    ])
    
    # Caching
    enable_cache: bool = True
    cache_ttl_days: int = 7


DEFAULT_CONFIG = SourcingConfig()

# =========================================================
# DATA STRUCTURES
# =========================================================

@dataclass
class SupplierCandidate:
    """A supplier candidate with extracted information."""
    
    # Identity
    name: str
    domain: str
    url: str
    
    # Classification
    supplier_type: str  # OEM / distributor / integrator / service / unknown
    confidence: float  # 0.0 - 1.0
    
    # Location
    country: Optional[str] = None
    coverage: List[str] = field(default_factory=list)  # Regions covered
    
    # Contact information
    website: Optional[str] = None
    contact_page: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    
    # Evidence
    evidence_snippets: List[str] = field(default_factory=list)
    source_urls: List[str] = field(default_factory=list)
    
    # Scoring factors
    score: float = 0.0
    notes: List[str] = field(default_factory=list)
    
    # Metadata
    relevance_signals: Dict[str, bool] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class MachineNormalization:
    """Normalized machine information."""
    
    original_name: str
    canonical_name: str
    english_term: str
    keywords: List[str]
    synonyms: List[str]
    hs_code: Optional[str] = None
    industry_terms: List[str] = field(default_factory=list)
    category: Optional[str] = None


@dataclass
class QueryVariant:
    """A search query variant."""
    
    query: str
    intent: str  # oem / distributor / service
    keywords: List[str]
    regional_focus: bool = True


@dataclass
class SourcingMetrics:
    """Metrics for sourcing execution (ENHANCED for observability)."""
    
    machine_name: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    
    # Query metrics
    queries_generated: int = 0
    queries_executed: int = 0
    queries_tried: List[str] = field(default_factory=list)  # NEW
    
    # Search metrics (ENHANCED)
    search_results_found: int = 0
    urls_scanned: int = 0
    search_pass_1_results: int = 0  # Broad
    search_pass_2_results: int = 0  # Regional
    search_pass_3_results: int = 0  # Vertical
    
    # Page fetching metrics (ENHANCED)
    pages_fetched: int = 0
    pages_failed: int = 0
    retry_attempts: int = 0  # NEW
    retry_successes: int = 0  # NEW
    
    # Candidate metrics (ENHANCED)
    raw_candidates: int = 0  # NEW: Before dedup
    candidates_extracted: int = 0
    candidates_filtered: int = 0
    candidates_deduplicated: int = 0
    
    # Supplier metrics (ENHANCED)
    suppliers_final: int = 0
    suppliers_high_confidence: int = 0
    suppliers_medium_confidence: int = 0
    suppliers_low_confidence: int = 0
    suppliers_from_fallback: int = 0  # NEW
    
    # LLM usage (ENHANCED)
    llm_calls: int = 0
    llm_query_planning: int = 0  # NEW
    llm_extraction: int = 0  # NEW
    llm_synthesis: int = 0  # NEW
    
    # Timing
    duration_seconds: float = 0.0
    timed_out: bool = False
    
    # Observability (NEW)
    fallback_catalog_used: bool = False
    
    def finalize(self):
        """Finalize metrics."""
        self.end_time = time.time()
        self.duration_seconds = self.end_time - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class SourcingResult:
    """Complete sourcing result for a machine."""
    
    machine: str
    suppliers: List[SupplierCandidate]
    metrics: SourcingMetrics
    normalization: Optional[MachineNormalization] = None
    queries_used: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "machine": self.machine,
            "suppliers": [s.to_dict() for s in self.suppliers],
            "metrics": self.metrics.to_dict(),
            "normalization": asdict(self.normalization) if self.normalization else None,
            "queries_used": self.queries_used,
            "warnings": self.warnings,
        }


# =========================================================
# STEP 1: MACHINE NAME NORMALIZATION
# =========================================================

# Canonical machine mappings (French → English)
CANONICAL_MACHINE_MAP = {
    # Injection molding
    "machine d'injection plastique": "plastic injection molding machine",
    "presse à injecter": "plastic injection molding machine",
    "injection molding machine": "plastic injection molding machine",
    
    # Extrusion
    "machine d'extrusion": "polymer extrusion machine",
    "extrudeuse": "polymer extrusion machine",
    "ligne d'extrusion": "polymer extrusion line",
    
    # Thermoforming
    "machine de thermoformage": "thermoforming machine",
    "thermoformage": "thermoforming machine",
    
    # Press
    "presse hydraulique": "hydraulic press",
    "presse pneumatique": "pneumatic press",
    
    # CNC
    "tour cnc": "cnc lathe",
    "fraiseuse cnc": "cnc milling machine",
    "centre d'usinage": "cnc machining center",
    
    # Packaging
    "machine d'emballage": "packaging machine",
    "ensacheuse": "bagging machine",
    "remplisseuse": "filling machine",
    
    # Welding
    "machine de soudage": "welding machine",
    "soudeuse laser": "laser welding machine",
    
    # Robots
    "robot industriel": "industrial robot",
    "robot de peinture": "painting robot",
    "robot de palettisation": "palletizing robot",
}

# Industry-specific keywords
INDUSTRY_KEYWORDS = {
    "plastic": ["polymer", "thermoplastic", "resin", "pellet"],
    "metal": ["steel", "aluminum", "alloy", "fabrication"],
    "packaging": ["wrapping", "sealing", "labeling", "cartoning"],
    "automation": ["robotics", "PLC", "SCADA", "industrial automation"],
}

# Common HS codes (Harmonized System)
HS_CODE_MAP = {
    "injection molding": "8477.10",
    "extrusion": "8477.20",
    "cnc": "8458",
    "packaging": "8422",
    "welding": "8515",
}


def normalize_machine_name(machine_name: str) -> MachineNormalization:
    """
    Normalize machine name to canonical form with keywords and synonyms.
    
    Uses rule-based mapping + keyword extraction.
    Fast and deterministic (no LLM).
    
    Args:
        machine_name: Original machine name (French or English)
    
    Returns:
        MachineNormalization with canonical name, keywords, synonyms
    """
    original = machine_name.strip()
    normalized_lower = original.lower()
    
    # Check canonical map
    canonical = CANONICAL_MACHINE_MAP.get(normalized_lower, normalized_lower)
    english_term = canonical
    
    # Extract keywords from canonical name
    keywords = []
    for word in canonical.split():
        if len(word) > 2 and word not in ["and", "the", "for", "of"]:
            keywords.append(word)
    
    # Add industry-specific keywords
    industry_kw = []
    for industry, terms in INDUSTRY_KEYWORDS.items():
        if any(term in canonical for term in [industry] + terms):
            industry_kw.extend(terms[:3])  # Top 3 related terms
    
    # Generate synonyms
    synonyms = []
    if "injection" in canonical:
        synonyms.extend(["IMM", "injection press", "molding press"])
    elif "extrusion" in canonical:
        synonyms.extend(["extruder", "extrusion line"])
    elif "cnc" in canonical:
        synonyms.extend(["computer numerical control", "automated machining"])
    elif "packaging" in canonical:
        synonyms.extend(["packing machine", "wrapping equipment"])
    
    # Determine category and HS code
    category = None
    hs_code = None
    for key, code in HS_CODE_MAP.items():
        if key in canonical:
            category = key
            hs_code = code
            break
    
    return MachineNormalization(
        original_name=original,
        canonical_name=canonical,
        english_term=english_term,
        keywords=list(set(keywords)),
        synonyms=synonyms,
        hs_code=hs_code,
        industry_terms=industry_kw,
        category=category,
    )


# =========================================================
# STEP 2: QUERY GENERATION
# =========================================================

def generate_query_variants(
    norm: MachineNormalization,
    config: SourcingConfig,
) -> List[QueryVariant]:
    """
    Generate query variants using multi-pass search strategy.
    
    MULTI-PASS STRATEGY (if enabled):
    - Pass 1 (Broad): OEM, manufacturer, global suppliers
    - Pass 2 (Regional): Regional distributors, agents, integrators
    - Pass 3 (Vertical): Industry-specific terms, OEM partners
    
    FALLBACK STRATEGY (if multipass disabled):
    - Q1: OEM + authorized distributor
    - Q2: Distributor/dealer/integrator with region
    - Q3: Maintenance/service/spare parts with region
    
    Args:
        norm: Normalized machine information
        config: Sourcing configuration
    
    Returns:
        List of QueryVariant (3-5 queries)
    """
    machine = norm.canonical_name
    keywords = " ".join(norm.keywords[:3])  # Top 3 keywords
    regional_terms = "(Algeria OR Maghreb OR \"North Africa\")"
    
    queries = []
    
    if config.enable_multipass:
        # ===== PASS 1: BROAD (OEM/Manufacturer) =====
        q1 = f"{machine} (manufacturer OR supplier OR distributor) {keywords}"
        queries.append(QueryVariant(
            query=q1,
            intent="broad_manufacturer",
            keywords=norm.keywords + ["manufacturer", "supplier"],
            regional_focus=False,
        ))
        
        # ===== PASS 2: REGIONAL (Distributors/Agents) =====
        q2 = f"{machine} (distributor OR dealer OR agent OR representative) {keywords} {regional_terms}"
        queries.append(QueryVariant(
            query=q2,
            intent="regional_distributor",
            keywords=norm.keywords + ["distributor", "Algeria"],
            regional_focus=True,
        ))
        
        q3 = f"{machine} (\"service center\" OR integrator OR installer OR \"after sales\") {keywords} {regional_terms}"
        queries.append(QueryVariant(
            query=q3,
            intent="regional_service",
            keywords=norm.keywords + ["service", "integrator", "Algeria"],
            regional_focus=True,
        ))
        
        # ===== PASS 3: VERTICAL (Industry-specific) =====
        # Use industry terms if available
        industry_kw = " ".join(norm.industry_terms[:2]) if norm.industry_terms else ""
        
        q4 = f"{machine} \"OEM partner\" \"authorized integrator\" {keywords} {industry_kw}"
        queries.append(QueryVariant(
            query=q4,
            intent="vertical_oem_partner",
            keywords=norm.keywords + ["OEM", "partner"] + norm.industry_terms[:2],
            regional_focus=False,
        ))
        
        q5 = f"{machine} \"turnkey supplier\" \"solution provider\" {keywords} {regional_terms}"
        queries.append(QueryVariant(
            query=q5,
            intent="vertical_turnkey",
            keywords=norm.keywords + ["turnkey", "solution", "Algeria"],
            regional_focus=True,
        ))
        
    else:
        # ===== FALLBACK STRATEGY (Legacy) =====
        # Q1: OEM + authorized distributor
        q1 = f"{machine} \"authorized distributor\" \"official dealer\" {keywords}"
        queries.append(QueryVariant(
            query=q1,
            intent="oem",
            keywords=norm.keywords + ["authorized", "official", "OEM"],
            regional_focus=False,
        ))
        
        # Q2: Distributor/dealer/agent/integrator with region
        q2 = f"{machine} (distributor OR dealer OR agent OR integrator OR installation) {keywords} {regional_terms}"
        queries.append(QueryVariant(
            query=q2,
            intent="distributor",
            keywords=norm.keywords + ["distributor", "dealer", "Algeria"],
            regional_focus=True,
        ))
        
        # Q3: Maintenance/service/spare parts with region
        q3 = f"{machine} (maintenance OR service OR \"spare parts\" OR repair) {keywords} {regional_terms}"
        queries.append(QueryVariant(
            query=q3,
            intent="service",
            keywords=norm.keywords + ["maintenance", "service", "Algeria"],
            regional_focus=True,
        ))
    
    # Limit to max_queries
    return queries[:config.max_queries]


# =========================================================
# STEP 3: SEARCH EXECUTION & FILTERING
# =========================================================

def is_junk_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Check if URL is junk (forum, PDF, marketplace listing, etc.).
    
    Returns:
        (is_junk, reason)
    """
    url_lower = url.lower()
    
    # PDF documents
    if url_lower.endswith('.pdf'):
        return True, "PDF document"
    
    # Forums and Q&A sites
    forum_patterns = [
        'forum', 'reddit.com', 'quora.com', 'stackoverflow',
        'answers.', 'discussion', 'community.'
    ]
    for pattern in forum_patterns:
        if pattern in url_lower:
            return True, f"Forum/Q&A site ({pattern})"
    
    # Marketplaces (generic, not specialized industrial)
    marketplace_patterns = [
        'amazon.com', 'ebay.com', 'alibaba.com', 'aliexpress',
        'amazon.', 'ebay.'
    ]
    for pattern in marketplace_patterns:
        if pattern in url_lower:
            return True, f"Generic marketplace ({pattern})"
    
    # Social media
    social_patterns = [
        'facebook.com', 'twitter.com', 'linkedin.com/in/',
        'instagram.com', 'youtube.com/watch'
    ]
    for pattern in social_patterns:
        if pattern in url_lower:
            return True, f"Social media ({pattern})"
    
    # Regulatory/standards docs
    if any(x in url_lower for x in ['regulation', 'standard', 'compliance', '.gov/']):
        return True, "Regulatory/standards"
    
    # Blog posts (unless it's a company blog)
    if '/blog/' in url_lower and not any(x in url_lower for x in ['company', 'news', 'press']):
        # Allow company blogs, filter personal blogs
        if any(x in url_lower for x in ['wordpress', 'blogger', 'medium.com', 'substack']):
            return True, "Personal blog"
    
    return False, None


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path.split('/')[0]
        # Remove www.
        return domain.replace('www.', '')
    except:
        return url


def search_with_diversity(
    query: str,
    max_results: int,
    domain_cap: int,
    max_retries: int = 3,
    backoff_base: float = 1.0,
    use_jitter: bool = True,
) -> List[Dict[str, Any]]:
    """
    Execute search with domain diversity control and retry logic.
    
    Caps results per domain to ensure variety.
    Filters out junk URLs.
    
    RETRY LOGIC:
    - Exponential backoff: wait = backoff_base * (2 ** attempt)
    - Optional jitter: add random 0-1s to avoid thundering herd
    - Retries on network errors, API failures
    
    Args:
        query: Search query
        max_results: Max total results to return
        domain_cap: Max results from same domain
        max_retries: Max retry attempts (default 3)
        backoff_base: Base delay in seconds (default 1.0)
        use_jitter: Add random jitter to backoff (default True)
    
    Returns:
        List of search results with url, title, snippet, domain
    """
    from utils.web_search import serper
    import random
    
    for attempt in range(max_retries + 1):
        try:
            # Execute search
            searcher = serper.SerperSearch()
            raw_results = searcher.search(query, num_results=max_results * 2)  # Fetch extra to account for filtering
            
            # Filter and enforce diversity
            results = []
            domain_counts = {}
            
            for item in raw_results:
                url = item.url
                
                # Skip junk URLs
                is_junk, reason = is_junk_url(url)
                if is_junk:
                    logger.debug(f"Filtered junk URL: {url} ({reason})")
                    continue
                
                # Extract domain
                domain = extract_domain(url)
                
                # Enforce domain cap
                if domain_counts.get(domain, 0) >= domain_cap:
                    logger.debug(f"Domain cap reached for {domain}, skipping {url}")
                    continue
                
                # Add result
                results.append({
                    'url': url,
                    'title': item.title,
                    'snippet': item.snippet,
                    'domain': domain,
                })
                
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
                
                # Stop if we have enough
                if len(results) >= max_results:
                    break
            
            # Success - return results
            return results
        
        except Exception as e:
            if attempt < max_retries:
                # Calculate backoff with jitter
                wait_time = backoff_base * (2 ** attempt)
                if use_jitter:
                    wait_time += random.uniform(0, 1)
                
                logger.warning(f"Search failed (attempt {attempt + 1}/{max_retries + 1}), retrying in {wait_time:.1f}s: {e}")
                time.sleep(wait_time)
            else:
                # Final attempt failed
                logger.error(f"Search failed after {max_retries + 1} attempts for query '{query}': {e}")
                return []
    
    return []


# =========================================================
# STEP 4: COMPANY EXTRACTION & CONTACT INFO
# =========================================================

def fetch_page_content(
    url: str,
    timeout: float = 10.0,
    max_retries: int = 2,
    backoff_base: float = 0.5,
    use_jitter: bool = True,
) -> Optional[str]:
    """
    Fetch page content with timeout and retry logic.
    
    RETRY LOGIC:
    - Exponential backoff for network errors and server errors
    - Retries on connection failures, timeouts, 5xx errors
    - No retry on 4xx client errors (bad request, not found, etc.)
    
    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
        max_retries: Max retry attempts (default 2)
        backoff_base: Base delay in seconds (default 0.5)
        use_jitter: Add random jitter to backoff (default True)
    
    Returns:
        Page HTML content or None
    """
    import requests
    import random
    
    for attempt in range(max_retries + 1):
        try:
            response = requests.get(
                url,
                timeout=timeout,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                },
                allow_redirects=True,
            )
            
            # Success
            if response.status_code == 200:
                return response.text
            
            # Client error (4xx) - don't retry
            if 400 <= response.status_code < 500:
                logger.debug(f"Client error {response.status_code} for {url}, not retrying")
                return None
            
            # Server error (5xx) - retry
            if attempt < max_retries:
                wait_time = backoff_base * (2 ** attempt)
                if use_jitter:
                    wait_time += random.uniform(0, 0.5)
                logger.debug(f"Server error {response.status_code} for {url}, retrying in {wait_time:.1f}s")
                time.sleep(wait_time)
            else:
                logger.debug(f"Failed to fetch {url} after {max_retries + 1} attempts: HTTP {response.status_code}")
                return None
        
        except (requests.Timeout, requests.ConnectionError) as e:
            # Network errors - retry
            if attempt < max_retries:
                wait_time = backoff_base * (2 ** attempt)
                if use_jitter:
                    wait_time += random.uniform(0, 0.5)
                logger.debug(f"Network error for {url}, retrying in {wait_time:.1f}s: {e}")
                time.sleep(wait_time)
            else:
                logger.debug(f"Failed to fetch {url} after {max_retries + 1} attempts: {e}")
                return None
        
        except Exception as e:
            # Other errors - don't retry
            logger.debug(f"Failed to fetch {url}: {e}")
            return None
    
    return None


def extract_company_info(html: str, url: str) -> Dict[str, Any]:
    """
    Extract company information from HTML.
    
    Extracts:
        - Company name
        - Contact info (email, phone)
        - Address/region
        - Product relevance signals
    
    Args:
        html: Page HTML content
        url: Page URL
    
    Returns:
        Dict with extracted info
    """
    from bs4 import BeautifulSoup
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract text content
        text = soup.get_text(separator=' ', strip=True)
        text_lower = text.lower()
        
        # Company name (from title or h1)
        company_name = None
        title_tag = soup.find('title')
        if title_tag:
            company_name = title_tag.get_text().strip()
        
        if not company_name or len(company_name) < 3:
            h1 = soup.find('h1')
            if h1:
                company_name = h1.get_text().strip()
        
        # Email extraction
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        email = emails[0] if emails else None
        
        # Phone extraction (international format)
        phone_pattern = r'[\+]?[(]?[0-9]{1,4}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,9}'
        phones = re.findall(phone_pattern, text)
        phone = phones[0] if phones else None
        
        # Contact page detection
        contact_links = soup.find_all('a', href=True)
        contact_page = None
        for link in contact_links:
            href = link['href'].lower()
            if any(x in href for x in ['contact', 'about', 'nous']):
                contact_page = href if href.startswith('http') else f"{url.rstrip('/')}/{href.lstrip('/')}"
                break
        
        # Region/country detection
        country = None
        regions = []
        for region in ["Algeria", "Tunisia", "Morocco", "Libya", "Egypt", "North Africa", "Maghreb", "MENA"]:
            if region.lower() in text_lower:
                regions.append(region)
                if not country and region in ["Algeria", "Tunisia", "Morocco", "Libya", "Egypt"]:
                    country = region
        
        # Product relevance signals
        relevance_signals = {
            'has_products_page': bool(soup.find('a', href=re.compile(r'product', re.I))),
            'has_catalog': 'catalog' in text_lower or 'catalogue' in text_lower,
            'has_distributor_mention': 'distributor' in text_lower or 'dealer' in text_lower,
            'has_manufacturer_mention': 'manufacturer' in text_lower or 'fabricant' in text_lower,
            'has_service_mention': 'service' in text_lower or 'maintenance' in text_lower,
        }
        
        return {
            'company_name': company_name,
            'email': email,
            'phone': phone,
            'contact_page': contact_page,
            'country': country,
            'regions': regions,
            'relevance_signals': relevance_signals,
            'domain': extract_domain(url),
        }
    
    except Exception as e:
        logger.error(f"Failed to extract company info from {url}: {e}")
        return {}


# =========================================================
# STEP 5: SUPPLIER CLASSIFICATION
# =========================================================

def classify_supplier_type(
    company_info: Dict[str, Any],
    search_result: Dict[str, Any],
    query_intent: str,
) -> Tuple[str, float]:
    """
    Classify supplier type using rule-based signals.
    
    Types: OEM / distributor / integrator / service / unknown
    
    Args:
        company_info: Extracted company information
        search_result: Original search result
        query_intent: Intent of the query (oem/distributor/service)
    
    Returns:
        (supplier_type, confidence)
    """
    text = (search_result.get('snippet', '') + ' ' + search_result.get('title', '')).lower()
    
    signals = company_info.get('relevance_signals', {})
    
    # OEM signals
    oem_score = 0.0
    if any(x in text for x in ['manufacturer', 'fabricant', 'factory', 'oem', 'original equipment']):
        oem_score += 0.4
    if signals.get('has_manufacturer_mention'):
        oem_score += 0.3
    if 'products' in text or signals.get('has_products_page'):
        oem_score += 0.2
    
    # Distributor signals
    distributor_score = 0.0
    if any(x in text for x in ['distributor', 'dealer', 'agent', 'authorized', 'official']):
        distributor_score += 0.4
    if signals.get('has_distributor_mention'):
        distributor_score += 0.3
    if any(x in text for x in ['supplier', 'fournisseur', 'wholesale']):
        distributor_score += 0.2
    
    # Integrator signals
    integrator_score = 0.0
    if any(x in text for x in ['integration', 'installation', 'turnkey', 'solution']):
        integrator_score += 0.4
    if 'system' in text:
        integrator_score += 0.2
    
    # Service signals
    service_score = 0.0
    if any(x in text for x in ['service', 'maintenance', 'repair', 'spare parts', 'after-sales']):
        service_score += 0.4
    if signals.get('has_service_mention'):
        service_score += 0.3
    
    # Boost based on query intent
    if query_intent == 'oem':
        oem_score *= 1.2
        distributor_score *= 1.1
    elif query_intent == 'distributor':
        distributor_score *= 1.3
        integrator_score *= 1.1
    elif query_intent == 'service':
        service_score *= 1.3
    
    # Determine type and confidence
    scores = {
        'OEM': oem_score,
        'distributor': distributor_score,
        'integrator': integrator_score,
        'service': service_score,
    }
    
    max_type = max(scores, key=scores.get)
    max_score = scores[max_type]
    
    if max_score < 0.3:
        return 'unknown', max_score
    
    # Confidence: normalize to 0-1
    confidence = min(max_score, 1.0)
    
    return max_type, confidence


# =========================================================
# STEP 6: SCORING & RANKING
# =========================================================

def score_supplier(
    candidate: SupplierCandidate,
    norm: MachineNormalization,
    config: SourcingConfig,
) -> float:
    """
    Score supplier candidate based on multiple factors.
    
    Scoring factors:
        +0.3: Contact info present (email or phone)
        +0.2: Relevant product terms match
        +0.2: Regional presence (Algeria/NA)
        +0.15: Authorized/dealer wording
        +0.1: Brands listed
        +0.05: Has catalog
        
        -0.2: Marketplace listing only
        -0.15: No company identity
        -0.1: Unrelated industry
    
    Args:
        candidate: Supplier candidate
        norm: Machine normalization
        config: Configuration
    
    Returns:
        Score (0.0 - 1.0+)
    """
    score = 0.0
    notes = []
    
    # Contact info
    if candidate.email or candidate.phone:
        score += 0.3
        notes.append("Has contact info")
    
    # Contact page
    if candidate.contact_page:
        score += 0.1
        notes.append("Has contact page")
    
    # Relevant product terms
    relevance_count = sum(1 for kw in norm.keywords if kw.lower() in ' '.join(candidate.evidence_snippets).lower())
    if relevance_count >= 2:
        score += 0.2
        notes.append(f"Relevant terms: {relevance_count}")
    elif relevance_count == 1:
        score += 0.1
    
    # Regional presence
    target_regions_lower = [r.lower() for r in config.target_regions]
    coverage_lower = [c.lower() for c in candidate.coverage]
    regional_match = any(r in coverage_lower for r in target_regions_lower)
    
    if candidate.country and candidate.country.lower() in ['algeria', 'algérie']:
        score += 0.25
        notes.append("Based in Algeria")
    elif regional_match:
        score += 0.2
        notes.append("Regional coverage")
    
    # Authorized/dealer wording
    signals = candidate.relevance_signals
    if signals.get('has_distributor_mention') or signals.get('has_manufacturer_mention'):
        score += 0.15
        notes.append("Authorized mention")
    
    # Has catalog
    if signals.get('has_catalog'):
        score += 0.05
        notes.append("Has catalog")
    
    # Penalties
    
    # Marketplace only (heuristic: domain contains 'market' or 'trade')
    if 'market' in candidate.domain or 'trade' in candidate.domain:
        score -= 0.2
        notes.append("Marketplace listing")
    
    # No company identity
    if not candidate.name or len(candidate.name) < 3:
        score -= 0.15
        notes.append("No company identity")
    
    # Low confidence from classification
    if candidate.confidence < 0.4:
        score -= 0.1
        notes.append("Low classification confidence")
    
    # Normalize to 0-1
    score = max(0.0, min(1.0, score))
    
    candidate.notes.extend(notes)
    return score


# =========================================================
# STEP 7: INTELLIGENT EXPANSION
# =========================================================

def find_dealer_locators(
    oem_candidates: List[SupplierCandidate],
    max_fetch: int = 3,
    timeout: float = 10.0,
) -> List[str]:
    """
    Find dealer locator pages from OEM websites.
    
    Args:
        oem_candidates: OEM suppliers found
        max_fetch: Max OEM sites to check
        timeout: Timeout per fetch
    
    Returns:
        List of dealer locator URLs
    """
    dealer_urls = []
    
    for oem in oem_candidates[:max_fetch]:
        if not oem.website:
            continue
        
        try:
            html = fetch_page_content(oem.website, timeout=timeout)
            if not html:
                continue
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Look for dealer/partner links
            links = soup.find_all('a', href=True)
            for link in links:
                href = link['href'].lower()
                text = link.get_text().lower()
                
                if any(x in href or x in text for x in ['dealer', 'distributor', 'partner', 'locator', 'find']):
                    full_url = href if href.startswith('http') else f"{oem.website.rstrip('/')}/{href.lstrip('/')}"
                    dealer_urls.append(full_url)
                    break  # One per OEM
        
        except Exception as e:
            logger.debug(f"Failed to find dealer locator for {oem.name}: {e}")
    
    return dealer_urls


def expand_suppliers_intelligent(
    current_suppliers: List[SupplierCandidate],
    norm: MachineNormalization,
    config: SourcingConfig,
    pages_fetched: int,
) -> List[SupplierCandidate]:
    """
    Intelligently expand supplier list if below target.
    
    Strategy:
        1. Find dealer locator pages from OEMs
        2. Extract additional distributors from those pages
    
    Args:
        current_suppliers: Current supplier list
        norm: Machine normalization
        config: Configuration
        pages_fetched: Pages already fetched
    
    Returns:
        Additional suppliers found
    """
    if len(current_suppliers) >= config.target_suppliers_min:
        return []
    
    remaining_pages = config.max_pages_total - pages_fetched
    if remaining_pages <= 0:
        return []
    
    logger.info(f"Expanding suppliers (current: {len(current_suppliers)}, target: {config.target_suppliers_min})")
    
    # Find OEMs
    oems = [s for s in current_suppliers if s.supplier_type == 'OEM']
    
    if not oems:
        return []
    
    # Get dealer locator URLs
    dealer_urls = find_dealer_locators(oems, max_fetch=min(3, remaining_pages))
    
    additional_suppliers = []
    
    # Fetch and extract from dealer pages
    for url in dealer_urls[:remaining_pages]:
        html = fetch_page_content(url, timeout=config.timeout_per_page_fetch)
        if not html:
            continue
        
        # Extract company names from dealer page
        # Simple heuristic: look for lists and links
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find all links
        links = soup.find_all('a', href=True)
        
        for link in links:
            text = link.get_text().strip()
            href = link['href']
            
            # Skip if text is too short or too long
            if len(text) < 3 or len(text) > 100:
                continue
            
            # Skip if it's navigation
            if any(x in text.lower() for x in ['home', 'about', 'contact', 'products', 'services']):
                continue
            
            # Assume it's a company name if it's a reasonable length
            domain = extract_domain(href)
            
            # Create candidate
            candidate = SupplierCandidate(
                name=text,
                domain=domain,
                url=href if href.startswith('http') else f"{url.rstrip('/')}/{href.lstrip('/')}",
                supplier_type='distributor',
                confidence=0.6,  # Medium confidence from dealer locator
                website=href if href.startswith('http') else None,
                evidence_snippets=[f"Found on dealer locator: {url}"],
                source_urls=[url],
                notes=["Extracted from OEM dealer locator"],
            )
            
            additional_suppliers.append(candidate)
    
    return additional_suppliers


# =========================================================
# STEP 8: DEDUPLICATION
# =========================================================

def normalize_company_name(name: str) -> str:
    """Normalize company name for deduplication."""
    if not name:
        return ""
    
    # Lowercase
    name = name.lower()
    
    # Remove common suffixes
    suffixes = ['incorporated', 'inc', 'llc', 'ltd', 'corp', 'corporation', 'company', 'co', 'sarl', 'sa', 'sas']
    for suffix in suffixes:
        name = re.sub(rf'\b{suffix}\.?\b', '', name)
    
    # Remove special characters
    name = re.sub(r'[^a-z0-9\s]', '', name)
    
    # Remove extra whitespace
    name = ' '.join(name.split())
    
    return name.strip()


def deduplicate_suppliers(
    suppliers: List[SupplierCandidate],
) -> List[SupplierCandidate]:
    """
    Deduplicate suppliers by normalized company name + domain.
    
    Keeps the entry with highest score.
    
    Args:
        suppliers: List of supplier candidates
    
    Returns:
        Deduplicated list
    """
    seen = {}  # key: (normalized_name, domain) -> SupplierCandidate
    
    for supplier in suppliers:
        norm_name = normalize_company_name(supplier.name)
        key = (norm_name, supplier.domain)
        
        if key not in seen:
            seen[key] = supplier
        else:
            # Keep higher scored entry
            if supplier.score > seen[key].score:
                seen[key] = supplier
    
    return list(seen.values())


# =========================================================
# FALLBACK VENDOR CATALOG
# =========================================================

# Known industrial B2B marketplaces and directories (FALLBACK)
FALLBACK_VENDOR_CATALOG = [
    {
        "name": "Alibaba Group",
        "domain": "alibaba.com",
        "url": "https://www.alibaba.com",
        "type": "marketplace",
        "description": "Global B2B marketplace for industrial machinery",
        "regional_focus": "Asia/Global",
        "confidence": 0.6,
    },
    {
        "name": "Made-in-China.com",
        "domain": "made-in-china.com",
        "url": "https://www.made-in-china.com",
        "type": "marketplace",
        "description": "Chinese B2B marketplace for industrial equipment",
        "regional_focus": "China/Global",
        "confidence": 0.6,
    },
    {
        "name": "IndiaMART",
        "domain": "indiamart.com",
        "url": "https://www.indiamart.com",
        "type": "marketplace",
        "description": "Indian B2B marketplace for industrial machinery",
        "regional_focus": "India/Global",
        "confidence": 0.6,
    },
    {
        "name": "TradeIndia",
        "domain": "tradeindia.com",
        "url": "https://www.tradeindia.com",
        "type": "marketplace",
        "description": "Indian B2B portal for industrial equipment",
        "regional_focus": "India/Global",
        "confidence": 0.5,
    },
    {
        "name": "Europages",
        "domain": "europages.com",
        "url": "https://www.europages.com",
        "type": "directory",
        "description": "European B2B directory for industrial suppliers",
        "regional_focus": "Europe",
        "confidence": 0.7,
    },
    {
        "name": "Kompass Algeria",
        "domain": "dz.kompass.com",
        "url": "https://dz.kompass.com",
        "type": "directory",
        "description": "Algerian business directory for industrial suppliers",
        "regional_focus": "Algeria",
        "confidence": 0.8,
    },
    {
        "name": "ThomasNet",
        "domain": "thomasnet.com",
        "url": "https://www.thomasnet.com",
        "type": "directory",
        "description": "North American industrial supplier directory",
        "regional_focus": "North America",
        "confidence": 0.7,
    },
    {
        "name": "Global Sources",
        "domain": "globalsources.com",
        "url": "https://www.globalsources.com",
        "type": "marketplace",
        "description": "Global B2B marketplace for industrial products",
        "regional_focus": "Asia/Global",
        "confidence": 0.6,
    },
]


def get_fallback_suppliers(
    machine_name: str,
    num_suppliers: int = 5,
) -> List[Supplier]:
    """
    Return fallback suppliers from known B2B marketplaces.
    
    Used as LAST RESORT when search returns insufficient results.
    
    Args:
        machine_name: Machine name for context
        num_suppliers: How many fallback suppliers to return
    
    Returns:
        List of Supplier objects from fallback catalog
    """
    fallback_suppliers = []
    
    for vendor in FALLBACK_VENDOR_CATALOG[:num_suppliers]:
        supplier = Supplier(
            name=vendor["name"],
            url=vendor["url"],
            domain=vendor["domain"],
            supplier_type=vendor["type"],
            confidence_score=vendor["confidence"],
            email=None,
            phone=None,
            address=None,
            products_mentioned=[machine_name],
            is_regional=("Algeria" in vendor["regional_focus"] or "Maghreb" in vendor["regional_focus"]),
            source_query="FALLBACK_CATALOG",
            metadata={
                "is_fallback": True,
                "description": vendor["description"],
                "regional_focus": vendor["regional_focus"],
            }
        )
        fallback_suppliers.append(supplier)
    
    logger.info(f"Generated {len(fallback_suppliers)} fallback suppliers from catalog")
    return fallback_suppliers


# =========================================================
# MAIN WORKFLOW
# =========================================================

def source_suppliers_for_machine(
    machine_name: str,
    config: Optional[SourcingConfig] = None,
) -> SourcingResult:
    """
    Main agentic workflow to source suppliers for a machine.
    
    ENHANCED WORKFLOW (High-Recall):
    - Multi-pass search strategy (broad/regional/vertical)
    - Retry logic with exponential backoff
    - Candidate harvesting: 30-80 raw candidates
    - Fallback vendor catalog for guaranteed minimum
    - Best-effort guarantees (progressive threshold relaxation)
    - Enhanced observability logging
    
    Executes all 8 steps with bounded execution and timeout control.
    
    Args:
        machine_name: Name of the machine
        config: Optional configuration (uses DEFAULT_CONFIG if None)
    
    Returns:
        SourcingResult with suppliers, metrics, and warnings
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    metrics = SourcingMetrics(machine_name=machine_name)
    warnings = []
    
    start_time = time.time()
    timeout_at = start_time + config.timeout_per_machine
    
    try:
        # STEP 1: Normalize machine name
        logger.info(f"[STEP 1] Normalizing machine: {machine_name}")
        norm = normalize_machine_name(machine_name)
        logger.info(f"Canonical: {norm.canonical_name}, Keywords: {norm.keywords}")
        
        # STEP 2: Generate query variants (ENHANCED: multi-pass)
        logger.info(f"[STEP 2] Generating query variants (multipass={config.enable_multipass})")
        queries = generate_query_variants(norm, config)
        metrics.queries_generated = len(queries)
        metrics.queries_tried = [q.query for q in queries]
        logger.info(f"Generated {len(queries)} queries")
        for i, q in enumerate(queries, 1):
            logger.debug(f"  Q{i} ({q.intent}): {q.query}")
        
        # STEP 3-6: Search, extract, classify, score (ENHANCED: with retry + multipass tracking)
        logger.info(f"[STEP 3-6] Executing searches and extracting candidates")
        
        all_candidates = []
        pages_fetched = 0
        current_pass = 1
        
        for query_idx, query_variant in enumerate(queries):
            # Check timeout
            if time.time() >= timeout_at:
                warnings.append("Timeout reached during search execution")
                metrics.timed_out = True
                break
            
            # Track search pass (for multipass strategy)
            if config.enable_multipass and query_idx < len(queries):
                if query_idx < 1:
                    current_pass = 1  # Broad
                elif query_idx < 3:
                    current_pass = 2  # Regional
                else:
                    current_pass = 3  # Vertical
            
            logger.info(f"[Pass {current_pass}] Executing query ({query_variant.intent}): {query_variant.query}")
            
            # Search with diversity + RETRY LOGIC
            search_results = search_with_diversity(
                query=query_variant.query,
                max_results=config.max_results_per_query,
                domain_cap=config.domain_diversity_cap,
                max_retries=config.max_retries,
                backoff_base=config.retry_backoff_base,
                use_jitter=config.retry_jitter,
            )
            
            # Track pass-specific results
            if current_pass == 1:
                metrics.search_pass_1_results += len(search_results)
            elif current_pass == 2:
                metrics.search_pass_2_results += len(search_results)
            elif current_pass == 3:
                metrics.search_pass_3_results += len(search_results)
            
            metrics.queries_executed += 1
            metrics.search_results_found += len(search_results)
            metrics.urls_scanned += len(search_results)
            
            logger.info(f"Found {len(search_results)} results (pass {current_pass})")
            
            # Process each search result
            for result in search_results:
                # Check candidate cap (harvest limit)
                if len(all_candidates) >= config.candidate_cap:
                    logger.info(f"Candidate cap reached ({config.candidate_cap}), stopping search")
                    break
                
                # Check page fetch limit
                if pages_fetched >= config.max_pages_total:
                    warnings.append("Page fetch limit reached")
                    break
                
                # Check timeout
                if time.time() >= timeout_at:
                    warnings.append("Timeout reached during page fetching")
                    metrics.timed_out = True
                    break
                
                url = result['url']
                
                # Fetch page content + RETRY LOGIC
                html = fetch_page_content(
                    url,
                    timeout=config.timeout_per_page_fetch,
                    max_retries=config.max_retries,
                    backoff_base=config.retry_backoff_base,
                    use_jitter=config.retry_jitter,
                )
                pages_fetched += 1
                metrics.pages_fetched += 1
                
                if not html:
                    metrics.pages_failed += 1
                    continue
                
                # Extract company info
                company_info = extract_company_info(html, url)
                
                if not company_info.get('company_name'):
                    continue
                
                # Classify supplier type
                supplier_type, classification_conf = classify_supplier_type(
                    company_info,
                    result,
                    query_variant.intent,
                )
                
                # Create candidate
                candidate = SupplierCandidate(
                    name=company_info['company_name'],
                    domain=company_info['domain'],
                    url=url,
                    supplier_type=supplier_type,
                    confidence=classification_conf,
                    country=company_info.get('country'),
                    coverage=company_info.get('regions', []),
                    website=url,
                    contact_page=company_info.get('contact_page'),
                    email=company_info.get('email'),
                    phone=company_info.get('phone'),
                    evidence_snippets=[result.get('snippet', '')],
                    source_urls=[url],
                    relevance_signals=company_info.get('relevance_signals', {}),
                )
                
                # Score candidate
                candidate.score = score_supplier(candidate, norm, config)
                
                all_candidates.append(candidate)
                
                logger.debug(f"Extracted: {candidate.name} ({candidate.supplier_type}, score={candidate.score:.2f})")
            
            # Log pass completion
            logger.info(f"[Pass {current_pass}] Completed. Total candidates: {len(all_candidates)}")
        
        metrics.raw_candidates = len(all_candidates)
        metrics.candidates_extracted = len(all_candidates)
        
        logger.info(f"Raw candidate harvest: {metrics.raw_candidates} suppliers")
        
        # STEP 7: Intelligent expansion (if needed and budget allows)
        if len(all_candidates) < config.target_suppliers_min and pages_fetched < config.max_pages_total:
            logger.info(f"[STEP 7] Expanding suppliers (current: {len(all_candidates)})")
            
            additional = expand_suppliers_intelligent(
                current_suppliers=all_candidates,
                norm=norm,
                config=config,
                pages_fetched=pages_fetched,
            )
            
            if additional:
                logger.info(f"Expansion found {len(additional)} additional suppliers")
                all_candidates.extend(additional)
                metrics.candidates_extracted += len(additional)
                metrics.raw_candidates += len(additional)
        
        # STEP 8: Deduplication
        logger.info(f"[STEP 8] Deduplicating suppliers")
        before_dedup = len(all_candidates)
        all_candidates = deduplicate_suppliers(all_candidates)
        metrics.candidates_deduplicated = before_dedup - len(all_candidates)
        logger.info(f"After dedup: {len(all_candidates)} suppliers (removed {metrics.candidates_deduplicated})")
        
        # Filter by confidence
        filtered_candidates = [
            c for c in all_candidates
            if c.score >= config.min_confidence_score
        ]
        metrics.candidates_filtered = len(all_candidates) - len(filtered_candidates)
        
        logger.info(f"After confidence filter (>={config.min_confidence_score:.2f}): {len(filtered_candidates)} suppliers")
        
        # Sort by score
        filtered_candidates.sort(key=lambda x: x.score, reverse=True)
        
        # BEST-EFFORT GUARANTEE: Progressive threshold relaxation
        if len(filtered_candidates) < 10 and len(all_candidates) > 10:
            relaxed_threshold = config.min_confidence_score * 0.7
            warnings.append(f"Strict filter yielded only {len(filtered_candidates)} suppliers, relaxing threshold to {relaxed_threshold:.2f}")
            relaxed_candidates = [c for c in all_candidates if c.score >= relaxed_threshold]
            relaxed_candidates.sort(key=lambda x: x.score, reverse=True)
            filtered_candidates = relaxed_candidates
            logger.info(f"After relaxed filter (>={relaxed_threshold:.2f}): {len(filtered_candidates)} suppliers")
        
        # FALLBACK CATALOG: If still insufficient results
        if config.enable_fallback_catalog and len(filtered_candidates) < config.fallback_catalog_threshold:
            logger.warning(f"Insufficient results ({len(filtered_candidates)} < {config.fallback_catalog_threshold}), using fallback catalog")
            
            fallback_suppliers = get_fallback_suppliers(
                machine_name=norm.canonical_name,
                num_suppliers=config.fallback_catalog_threshold - len(filtered_candidates),
            )
            
            # Convert to SupplierCandidate
            for fb in fallback_suppliers:
                fb_candidate = SupplierCandidate(
                    name=fb.name,
                    domain=fb.domain,
                    url=fb.url,
                    supplier_type=fb.supplier_type,
                    confidence=fb.confidence_score,
                    country=None,
                    coverage=[],
                    website=fb.url,
                    contact_page=None,
                    email=None,
                    phone=None,
                    evidence_snippets=[fb.metadata.get('description', '')],
                    source_urls=[fb.url],
                    relevance_signals={'is_fallback': True},
                )
                fb_candidate.score = fb.confidence_score
                filtered_candidates.append(fb_candidate)
            
            metrics.suppliers_from_fallback = len(fallback_suppliers)
            metrics.fallback_catalog_used = True
            
            logger.info(f"Added {len(fallback_suppliers)} fallback suppliers. Total: {len(filtered_candidates)}")
        
        # Take top N
        final_suppliers = filtered_candidates[:config.target_suppliers_max]
        
        # Count by confidence
        for supplier in final_suppliers:
            if supplier.score >= 0.7:
                metrics.suppliers_high_confidence += 1
            elif supplier.score >= 0.5:
                metrics.suppliers_medium_confidence += 1
            else:
                metrics.suppliers_low_confidence += 1
        
        metrics.suppliers_final = len(final_suppliers)
        
        # ENHANCED OBSERVABILITY LOGGING
        logger.info(f"="*60)
        logger.info(f"SOURCING COMPLETE: {machine_name}")
        logger.info(f"  Queries: {metrics.queries_executed}/{metrics.queries_generated}")
        logger.info(f"  Search Pass 1 (Broad): {metrics.search_pass_1_results} results")
        logger.info(f"  Search Pass 2 (Regional): {metrics.search_pass_2_results} results")
        logger.info(f"  Search Pass 3 (Vertical): {metrics.search_pass_3_results} results")
        logger.info(f"  Raw candidates: {metrics.raw_candidates}")
        logger.info(f"  After dedup: {metrics.raw_candidates - metrics.candidates_deduplicated}")
        logger.info(f"  After filter: {len(filtered_candidates)}")
        logger.info(f"  Fallback used: {metrics.fallback_catalog_used} ({metrics.suppliers_from_fallback} suppliers)")
        logger.info(f"  Final suppliers: {metrics.suppliers_final} (H:{metrics.suppliers_high_confidence}, M:{metrics.suppliers_medium_confidence}, L:{metrics.suppliers_low_confidence})")
        logger.info(f"  Duration: {metrics.duration_seconds:.1f}s / {config.timeout_per_machine:.0f}s")
        logger.info(f"  Timed out: {metrics.timed_out}")
        logger.info(f"="*60)
        
    except Exception as e:
        logger.error(f"Sourcing failed for {machine_name}: {e}", exc_info=True)
        warnings.append(f"Critical error: {e}")
        final_suppliers = []
    
    finally:
        metrics.finalize()
    
    return SourcingResult(
        machine=machine_name,
        suppliers=final_suppliers,
        metrics=metrics,
        normalization=norm if 'norm' in locals() else None,
        queries_used=[q.query for q in queries] if 'queries' in locals() else [],
        warnings=warnings,
    )


def source_suppliers_batch(
    machines: List[str],
    config: Optional[SourcingConfig] = None,
    max_workers: int = 4,
) -> List[SourcingResult]:
    """
    Source suppliers for multiple machines in parallel.
    
    Args:
        machines: List of machine names
        config: Optional configuration
        max_workers: Max parallel workers
    
    Returns:
        List of SourcingResult
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(source_suppliers_for_machine, machine, config): machine
            for machine in machines
        }
        
        for future in as_completed(futures):
            machine = futures[future]
            try:
                result = future.result(timeout=config.timeout_per_machine + 5)
                results.append(result)
                logger.info(f"Completed {machine}: {result.metrics.suppliers_final} suppliers in {result.metrics.duration_seconds:.1f}s")
            except FuturesTimeoutError:
                logger.error(f"Timeout for {machine}")
                results.append(SourcingResult(
                    machine=machine,
                    suppliers=[],
                    metrics=SourcingMetrics(machine_name=machine),
                    warnings=["Global timeout exceeded"],
                ))
            except Exception as e:
                logger.error(f"Failed {machine}: {e}")
                results.append(SourcingResult(
                    machine=machine,
                    suppliers=[],
                    metrics=SourcingMetrics(machine_name=machine),
                    warnings=[f"Execution failed: {e}"],
                ))
    
    return results
