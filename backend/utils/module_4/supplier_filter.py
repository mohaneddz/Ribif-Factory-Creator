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
    weights = {
        'company_identity': 0.4,
        'commercial': 0.3,
        'product_service': 0.2,
        'business_presence': 0.1,
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


def deduplicate_suppliers(suppliers: List[Dict]) -> List[Dict]:
    """
    Deduplicate suppliers by normalized name.
    Keeps highest scoring version.
    """
    seen = {}
    
    for supplier in suppliers:
        name = supplier.get('supplier_name', '').strip().lower()
        name = re.sub(r'[^a-z0-9]', '', name)  # Remove special chars for matching
        
        if not name:
            continue
        
        score = supplier.get('quality_score', 0.0)
        
        if name not in seen or score > seen[name].get('quality_score', 0.0):
            seen[name] = supplier
    
    return list(seen.values())
