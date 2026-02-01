"""
Supplier Quality Filtering & Scoring
=====================================

Filters out irrelevant sources and scores real suppliers.
Ensures only legitimate industrial suppliers are retained.
"""

from typing import Dict, List, Tuple
import re
from utils.logger import get_logger

logger = get_logger(__name__)

# =========================================================
# REJECTION PATTERNS (sources to exclude)
# =========================================================

# Government/regulatory sites (not suppliers)
GOVERNMENT_PATTERNS = [
    r'\.gov(\.|$)',
    r'\.mil(\.|$)',
    r'\.edu(\.|$)',
    r'\.ac\.',
    r'government',
    r'ministry',
    r'regulation',
    r'standard',
    r'iso\.org',
    r'iec\.ch',
    r'customs',
    r'trade\.gov',
]

# Generic marketplaces/aggregators (not real suppliers)
MARKETPLACE_PATTERNS = [
    r'alibaba\.com',
    r'aliexpress',
    r'amazon\.',
    r'ebay\.',
    r'alibaba',  # catch variations
    r'made-in-china',
    r'indiamart',
    r'thomasnet',
    r'globalspec',
    r'youtube\.',
    r'wikipedia',
]

# News/blog/generic articles (not suppliers)
CONTENT_PATTERNS = [
    r'blog\.',
    r'/blog/',
    r'news\.',
    r'/news/',
    r'article',
    r'press-release',
    r'wiki',
    r'forum',
    r'reddit\.',
    r'quora\.',
    r'linkedin\.com/pulse',
]

# PDFs without company context (likely whitepapers/reports)
GENERIC_PDF_PATTERNS = [
    r'whitepaper',
    r'report\.pdf',
    r'guide\.pdf',
    r'overview\.pdf',
    r'market-analysis',
]

# Materials, consumables, and services (not machine suppliers)
MATERIALS_CONSUMABLES_PATTERNS = [
    r'\b(plastic film|foil|wrap|sheet|roll)\b',
    r'\b(resin|polymer|granule|pellet|powder)\b',
    r'\b(adhesive|glue|tape|coating|ink|paint)\b',
    r'\b(consumable|spare part|component|accessory)\b',
    r'\b(raw material|chemical|solvent|cleaner)\b',
    r'\b(packaging material|label|bag|box)\b',
    r'\b(lubricant|oil|grease|fluid)\b',
    r'\b(maintenance service|repair service|cleaning service)\b',
    r'\b(training|consulting|consultancy)\b',
    r'\bmaterial supplier\b',
    r'\bchemical supplier\b',
]

ALL_REJECTION_PATTERNS = (
    GOVERNMENT_PATTERNS +
    MARKETPLACE_PATTERNS +
    CONTENT_PATTERNS +
    GENERIC_PDF_PATTERNS +
    MATERIALS_CONSUMABLES_PATTERNS
)

# =========================================================
# STRONG SIGNAL PATTERNS (indicators of real supplier)
# =========================================================

# Supplier type classification patterns
SUPPLIER_TYPE_PATTERNS = {
    'oem': [
        r'\b(manufacturer|factory|oem|original equipment)\b',
        r'\b(made by|produced by|fabricated by)\b',
        r'\bmanufacturing facility\b',
    ],
    'distributor': [
        r'\b(distributor|authorized dealer|official dealer)\b',
        r'\b(distribution|supply chain)\b',
        r'\bexclusive distributor\b',
    ],
    'integrator': [
        r'\b(system integrator|integration|turnkey)\b',
        r'\b(installation|commissioning|setup)\b',
        r'\b(engineering solution|complete line)\b',
    ],
}

STRONG_SIGNALS = {
    # Company identity signals
    'company_identity': [
        r'\b(company|corporation|corp|ltd|limited|inc|gmbh|sarl|spa)\b',
        r'\b(manufacturer|factory|plant)\b',
        r'\b(industrial|automation|engineering)\b',
    ],
    
    # Contact/commercial signals
    'commercial': [
        r'\b(contact|quote|request|inquiry|sales)\b',
        r'\b(price|pricing|cost)\b',
        r'\b(buy|purchase|order)\b',
        r'\b(catalogue|catalog|brochure)\b',
    ],
    
    # Product/service signals
    'product_service': [
        r'\b(machine|equipment|system|line)\b',
        r'\b(installation|commissioning|service)\b',
        r'\b(spare parts|maintenance|support)\b',
        r'\b(technical|specification|datasheet)\b',
    ],
    
    # Business presence signals
    'business_presence': [
        r'\b(distributor|dealer|agent|representative)\b',
        r'\b(certified|authorized|official)\b',
        r'\b(warranty|guarantee)\b',
    ]
}

# =========================================================
# SUPPLIER FILTERING
# =========================================================

def classify_supplier_type(supplier_name: str, description: str = "", url: str = "") -> str:
    """
    Classify supplier as OEM, distributor, or integrator based on text signals.
    
    Returns:
        'oem', 'distributor', 'integrator', or 'unknown'
    """
    combined_text = f"{supplier_name} {description} {url}".lower()
    
    # Score each type
    scores = {}
    for supplier_type, patterns in SUPPLIER_TYPE_PATTERNS.items():
        score = 0
        for pattern in patterns:
            matches = len(re.findall(pattern, combined_text, re.IGNORECASE))
            score += matches
        scores[supplier_type] = score
    
    # Return highest scoring type (if any)
    max_score = max(scores.values())
    if max_score > 0:
        return max(scores.items(), key=lambda x: x[1])[0]
    
    return 'unknown'

def should_reject_source(url: str, title: str = "", snippet: str = "") -> Tuple[bool, str]:
    """
    Check if a source should be rejected.
    
    Returns:
        (should_reject: bool, reason: str)
    """
    combined_text = f"{url} {title} {snippet}".lower()
    
    for pattern in ALL_REJECTION_PATTERNS:
        if re.search(pattern, combined_text, re.IGNORECASE):
            reason = f"Matched rejection pattern: {pattern}"
            return True, reason
    
    return False, ""


def score_supplier_signals(
    supplier_name: str,
    url: str,
    title: str = "",
    snippet: str = "",
    description: str = "",
    supplier_type: str = "unknown"
) -> Tuple[float, Dict[str, int]]:
    """
    Score a supplier based on strong signals with calibrated evidence-based scoring.
    
    Scoring philosophy:
    - OEM manufacturers: highest scores (0.8-0.95) due to direct source
    - Verified integrators: high scores (0.7-0.85) for turnkey solutions
    - Distributors: medium-high scores (0.6-0.75) for availability
    - Unknown type: lower scores (0.4-0.6) pending verification
    - Scores calibrated by evidence strength, not flat percentages
    
    Returns:
        (total_score: float, signal_breakdown: Dict[signal_type, count])
    """
    combined_text = f"{supplier_name} {url} {title} {snippet} {description}".lower()
    
    signal_counts = {
        'company_identity': 0,
        'commercial': 0,
        'product_service': 0,
        'business_presence': 0,
    }
    
    for signal_type, patterns in STRONG_SIGNALS.items():
        for pattern in patterns:
            matches = len(re.findall(pattern, combined_text, re.IGNORECASE))
            signal_counts[signal_type] += matches
    
    # Evidence-based weights (NOT flat percentages)
    # business_presence lowered to 0.05 to avoid penalizing OEMs
    weights = {
        'company_identity': 0.45,
        'commercial': 0.30,
        'product_service': 0.20,
        'business_presence': 0.05,  # Lowered - distributor signals shouldn't penalize OEMs
    }
    
    # Calculate base score from signals
    base_score = 0.0
    for signal_type, count in signal_counts.items():
        # Cap individual contributions to avoid over-weighting
        capped_count = min(count, 3)
        base_score += weights[signal_type] * (capped_count / 3.0)
    
    # Calibrate by supplier type (evidence-based, not arbitrary)
    type_multipliers = {
        'oem': 1.3,         # OEMs get highest scores (0.8-0.95 range)
        'integrator': 1.15, # Integrators get high scores (0.7-0.85 range)
        'distributor': 1.0, # Distributors get medium-high (0.6-0.75 range)
        'unknown': 0.85,    # Unknown types get lower scores (0.4-0.6 range)
    }
    
    multiplier = type_multipliers.get(supplier_type, 0.85)
    calibrated_score = min(0.95, base_score * multiplier)  # Cap at 0.95 (never 100%)
    
    return calibrated_score, signal_counts


def filter_and_score_supplier(
    supplier: Dict,
    min_score: float = 0.3,
    machine_name: str = ""
) -> Tuple[bool, float, str, str]:
    """
    Filter and score a single supplier with supplier type classification.
    
    Returns:
        (keep: bool, score: float, reason: str, supplier_type: str)
    """
    supplier_name = supplier.get('supplier_name', '')
    url = supplier.get('website', '') or supplier.get('source_url', '')
    title = supplier.get('title', '')
    snippet = supplier.get('snippet', '')
    notes = supplier.get('notes', '')
    
    # Check rejection patterns (including materials/consumables)
    should_reject, reject_reason = should_reject_source(url, title, snippet)
    if should_reject:
        return False, 0.0, f"REJECTED: {reject_reason}", 'rejected'
    
    # Classify supplier type
    supplier_type = classify_supplier_type(supplier_name, notes, url)
    
    # Score based on signals with calibrated scoring
    score, signal_breakdown = score_supplier_signals(
        supplier_name, url, title, snippet, notes, supplier_type
    )
    
    # Require at least one signal from each of two categories
    categories_with_signals = sum(1 for count in signal_breakdown.values() if count > 0)
    
    if categories_with_signals < 2:
        reason = f"REJECTED: Insufficient signals (only {categories_with_signals}/4 categories). Breakdown: {signal_breakdown}"
        return False, score, reason, supplier_type
    
    if score < min_score:
        reason = f"REJECTED: Score too low ({score:.2f} < {min_score}). Breakdown: {signal_breakdown}"
        return False, score, reason, supplier_type
    
    reason = f"ACCEPTED: Score {score:.2f} ({supplier_type}), signals: {signal_breakdown}"
    return True, score, reason, supplier_type


def filter_suppliers(
    suppliers: List[Dict],
    machine_name: str = "",
    machine_type: str = "",
    min_score: float = 0.3,
    log_decisions: bool = True
) -> List[Dict]:
    """
    Filter suppliers with hard requirements:
    - Machine suppliers only (OEM, distributor, integrator)
    - Exclude materials/consumables
    - Require ≥1 OEM OR ≥2 verified integrators when possible
    - Calibrate scores by evidence strength
    
    Args:
        suppliers: List of supplier dictionaries
        machine_name: Original machine name (for logging)
        machine_type: Canonical machine type (for logging)
        min_score: Minimum score threshold
        log_decisions: Whether to log keep/reject decisions
    
    Returns:
        Filtered list of suppliers with added 'quality_score' and 'supplier_type' fields
    """
    filtered = []
    supplier_type_counts = {'oem': 0, 'integrator': 0, 'distributor': 0, 'unknown': 0}
    
    for supplier in suppliers:
        keep, score, reason, supplier_type = filter_and_score_supplier(
            supplier, min_score, machine_name
        )
        
        if log_decisions:
            supplier_name = supplier.get('supplier_name', 'Unknown')
            logger.info(f"Supplier '{supplier_name}': {reason}")
        
        if keep:
            supplier['quality_score'] = round(score, 3)
            supplier['quality_signals'] = reason
            supplier['supplier_type'] = supplier_type
            filtered.append(supplier)
            supplier_type_counts[supplier_type] += 1
    
    # Log supplier type distribution
    if log_decisions:
        logger.info(
            f"Supplier types for '{machine_name}': "
            f"OEM={supplier_type_counts['oem']}, "
            f"Integrators={supplier_type_counts['integrator']}, "
            f"Distributors={supplier_type_counts['distributor']}, "
            f"Unknown={supplier_type_counts['unknown']}"
        )
        
        # Warn if requirements not met
        if supplier_type_counts['oem'] == 0 and supplier_type_counts['integrator'] < 2:
            logger.warning(
                f"Machine '{machine_name}' lacks ideal supplier mix: "
                f"No OEMs and fewer than 2 integrators. Consider additional searches."
            )
    
    return filtered


def extract_domain(url: str) -> str:
    """Extract normalized domain from URL."""
    if not url:
        return ""
    # Remove protocol and www
    domain = re.sub(r'^https?://(www\.)?', '', url.lower())
    # Take only domain part (before first /)
    domain = domain.split('/')[0]
    # Remove port if present
    domain = domain.split(':')[0]
    return domain


def normalize_supplier_key(supplier: Dict) -> str:
    """
    Generate normalized key for supplier deduplication.
    Combines domain + canonical name for better matching.
    """
    name = supplier.get('supplier_name', '').strip().lower()
    name = re.sub(r'[^a-z0-9]', '', name)  # Remove special chars
    
    # Extract domain from URL/website
    url = supplier.get('website', '') or supplier.get('source_url', '')
    domain = extract_domain(url)
    
    # Combine for unique key
    if domain and name:
        return f"{domain}::{name}"
    elif domain:
        return f"{domain}::"
    elif name:
        return f"::{name}"
    else:
        return ""


def deduplicate_suppliers(suppliers: List[Dict]) -> List[Dict]:
    """
    Deduplicate suppliers by normalized domain + name.
    Keeps highest scoring version and merges evidence.
    """
    seen = {}
    dedup_count = 0
    
    for supplier in suppliers:
        key = normalize_supplier_key(supplier)
        
        if not key:
            continue
        
        score = supplier.get('quality_score', 0.0)
        
        if key not in seen:
            seen[key] = supplier
        else:
            dedup_count += 1
            # Keep higher scoring version, but merge notes
            existing = seen[key]
            if score > existing.get('quality_score', 0.0):
                # Merge notes from lower-scored duplicate
                existing_notes = existing.get('notes', '')
                if existing_notes and existing_notes not in supplier.get('notes', ''):
                    supplier['notes'] = f"{supplier.get('notes', '')} | {existing_notes}".strip(' |')
                seen[key] = supplier
            else:
                # Merge notes into existing
                new_notes = supplier.get('notes', '')
                if new_notes and new_notes not in existing.get('notes', ''):
                    existing['notes'] = f"{existing.get('notes', '')} | {new_notes}".strip(' |')
    
    if dedup_count > 0:
        logger.info(f"Deduplicated {dedup_count} duplicate suppliers")
    
    return list(seen.values())


# =========================================================
# ENHANCED QUALITY SCORING WITH EVIDENCE SIGNALS
# =========================================================

# Known manufacturer/OEM domains (expandable)
KNOWN_OEM_DOMAINS = [
    # Glass machinery
    'glaston.net', 'bystronic-glass.com', 'hegla.com', 'lisec.com',
    'bottero.com', 'intermac.com', 'neptune-glass.com',
    # Plastic machinery  
    'engel.at', 'arburg.com', 'krauss-maffei.com', 'sumitomo-shi-demag.eu',
    'battenfeld-cincinnati.com', 'milacron.com', 'haitian.com',
    'husky.com', 'boy.de', 'netstal.com', 'fanuc.com',
    # Packaging/thermoforming
    'illig.de', 'kiefel.com', 'geiss-ag.de', 'multivac.com', 
    'cfs-group.com', 'gabler-thermoform.de',
    # Recycling/granulation
    'erema.at', 'starlinger.com', 'pallmann.de', 'vecoplan.com',
    'rapid-granulator.com', 'wittmann-group.com', 'zerma.com',
    # Automation/robotics
    'kuka.com', 'abb.com', 'staubli.com', 'yaskawa.com',
    'comau.com', 'duerr.com', 'eisenmann.com',
    # Edge banding/woodworking
    'ima.it', 'homag.com', 'biesse.com', 'scm-group.com',
]


def compute_quality_score(
    supplier: Dict,
    canonical_name: str = "",
    typical_manufacturers: List[str] = None
) -> Tuple[float, List[str]]:
    """
    Compute comprehensive quality score (0.0-1.0) based on evidence signals.
    
    Scoring Rules:
    - +0.35: Official manufacturer domain or brand-known domain
    - +0.20: Clear manufacturer/OEM/official product page indicators
    - +0.15: Contact information present (email or phone)
    - +0.10: Address or company imprint found
    - -0.30: Clearly unrelated page (materials-only, wrong category)
    - -0.20: Generic directory listing with no product relevance
    
    Args:
        supplier: Supplier dictionary with name, website, notes, etc.
        canonical_name: Canonical machine name for relevance checking
        typical_manufacturers: Known manufacturers for this machine type
        
    Returns:
        (quality_score: float, evidence: List[str])
    """
    score = 0.0
    evidence = []
    
    supplier_name = supplier.get('supplier_name', '').lower()
    website = supplier.get('website', '') or supplier.get('source_url', '')
    notes = supplier.get('notes', '').lower()
    domain = extract_domain(website)
    
    # OEM SIGNAL SEEDING: Force minimum signals for named manufacturers with websites
    # If supplier has real company name + website, ensure at least company_identity=1 and product_service=1
    has_real_company_name = bool(supplier_name and len(supplier_name) > 3 and supplier_name not in ['unknown', 'n/a', 'tbd'])
    has_website = bool(website and len(website) > 10)
    
    if has_real_company_name and has_website:
        # Seed signals to prevent 0/4 for real manufacturers
        if 'company_identity' not in str(evidence):
            score += 0.15
            evidence.append("OEM SEED: company_identity (real name + website)")
        if 'product_service' not in str(evidence):
            score += 0.10
            evidence.append("OEM SEED: product_service (real name + website)")
    
    # +0.35: Official manufacturer domain
    is_known_oem = any(oem_domain in domain for oem_domain in KNOWN_OEM_DOMAINS)
    if is_known_oem:
        score += 0.35
        evidence.append("Known OEM domain")
    
    # Check if supplier name matches typical manufacturers
    if typical_manufacturers:
        for mfr in typical_manufacturers:
            if mfr.lower() in supplier_name or mfr.lower() in domain:
                score += 0.35
                evidence.append(f"Matches known manufacturer: {mfr}")
                break
    
    # +0.20: Clear manufacturer/OEM indicators
    oem_patterns = [
        r'\bmanufacturer\b', r'\bfactory\b', r'\boem\b',
        r'\boriginal equipment\b', r'\bmade by\b', r'\bproduced by\b',
        r'\bofficial\b.*\b(page|site|website)\b',
        r'\b(official|authorized)\b.*\b(dealer|distributor)\b'
    ]
    oem_match = any(re.search(pattern, notes, re.IGNORECASE) for pattern in oem_patterns)
    if oem_match:
        score += 0.20
        evidence.append("Clear OEM/manufacturer indicators")
    
    # +0.15: Contact information present
    has_email = bool(supplier.get('emails'))
    has_phone = bool(supplier.get('phones'))
    has_contact_page = bool(supplier.get('contact_pages'))
    
    if has_email or has_phone:
        score += 0.15
        evidence.append(f"Contact info present (email: {has_email}, phone: {has_phone})")
    elif has_contact_page:
        score += 0.07  # Partial credit for contact page
        evidence.append("Contact page available")
    
    # +0.10: Address or company imprint
    address_patterns = [
        r'\baddress\b', r'\blocation\b', r'\bheadquarters\b',
        r'\bimprint\b', r'\bimpressum\b', r'\blegal\b',
        r'\d{4,5}\s+[A-Z][a-z]+',  # ZIP code + city pattern
    ]
    has_address = any(re.search(pattern, notes, re.IGNORECASE) for pattern in address_patterns)
    if has_address:
        score += 0.10
        evidence.append("Address/imprint found")
    
    # -0.30: Clearly unrelated (materials-only, wrong category)
    unrelated_patterns = [
        r'\bmaterial(s)?\s+only\b', r'\braw\s+material\b',
        r'\bconsumables?\s+supplier\b', r'\bspare\s+parts\s+only\b',
        r'\bchemical\s+supplier\b', r'\bresin\s+supplier\b',
        r'\b(not|no)\s+(machine|equipment)\b'
    ]
    is_unrelated = any(re.search(pattern, notes, re.IGNORECASE) for pattern in unrelated_patterns)
    if is_unrelated:
        score -= 0.30
        evidence.append("PENALTY: Clearly unrelated content")
    
    # -0.20: Generic directory listing
    directory_patterns = [
        r'\bdirectory\s+listing\b', r'\bgeneric\s+catalog\b',
        r'\baggregator\b', r'\b(list|listing)\s+of\s+suppliers\b'
    ]
    is_directory = any(re.search(pattern, notes, re.IGNORECASE) for pattern in directory_patterns)
    if is_directory:
        score -= 0.20
        evidence.append("PENALTY: Generic directory listing")
    
    # Additional bonus: Strong product relevance
    if canonical_name:
        name_in_supplier = canonical_name.lower() in supplier_name
        name_in_notes = canonical_name.lower() in notes
        if name_in_supplier or name_in_notes:
            score += 0.10
            evidence.append(f"Product name relevance: {canonical_name}")
    
    # Normalize score to [0.0, 1.0]
    final_score = max(0.0, min(1.0, score))
    
    return round(final_score, 3), evidence


def apply_quality_threshold(
    suppliers: List[Dict],
    min_quality_score: float = 0.55,
    canonical_name: str = "",
    typical_manufacturers: List[str] = None,
    allow_fallback: bool = False
) -> List[Dict]:
    """
    Apply quality score threshold to suppliers.
    
    Computes quality_score for each supplier and filters by threshold.
    If allow_fallback=True and no suppliers pass, returns suppliers above 0.40.
    
    Args:
        suppliers: List of supplier dictionaries
        min_quality_score: Minimum quality score (default 0.55)
        canonical_name: Machine canonical name for relevance
        typical_manufacturers: Known manufacturers for bonus scoring
        allow_fallback: Allow lower threshold (0.40) if no suppliers pass
        
    Returns:
        Filtered suppliers with quality_score and evidence fields
    """
    scored_suppliers = []
    
    for supplier in suppliers:
        quality_score, evidence = compute_quality_score(
            supplier,
            canonical_name,
            typical_manufacturers
        )
        
        supplier['quality_score'] = quality_score
        supplier['evidence'] = evidence
        scored_suppliers.append(supplier)
    
    # Filter by threshold
    passing_suppliers = [s for s in scored_suppliers if s['quality_score'] >= min_quality_score]
    
    # Fallback to lower threshold if enabled and no suppliers pass
    if allow_fallback and not passing_suppliers:
        logger.warning(
            f"No suppliers passed quality threshold {min_quality_score}. "
            f"Using fallback threshold 0.40"
        )
        passing_suppliers = [s for s in scored_suppliers if s['quality_score'] >= 0.40]
    
    logger.info(
        f"Quality filtering: {len(passing_suppliers)}/{len(suppliers)} suppliers passed "
        f"(threshold: {min_quality_score}, fallback: {allow_fallback})"
    )
    
    return passing_suppliers
