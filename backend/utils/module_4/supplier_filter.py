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

ALL_REJECTION_PATTERNS = (
    GOVERNMENT_PATTERNS +
    MARKETPLACE_PATTERNS +
    CONTENT_PATTERNS +
    GENERIC_PDF_PATTERNS
)

# =========================================================
# STRONG SIGNAL PATTERNS (indicators of real supplier)
# =========================================================

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
    description: str = ""
) -> Tuple[float, Dict[str, int]]:
    """
    Score a supplier based on strong signals.
    
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
    
    # Calculate weighted score
    weights = {
        'company_identity': 0.4,
        'commercial': 0.3,
        'product_service': 0.2,
        'business_presence': 0.1,
    }
    
    total_score = 0.0
    for signal_type, count in signal_counts.items():
        # Cap individual contributions to avoid over-weighting
        capped_count = min(count, 3)
        total_score += weights[signal_type] * (capped_count / 3.0)
    
    return total_score, signal_counts


def filter_and_score_supplier(
    supplier: Dict,
    min_score: float = 0.3
) -> Tuple[bool, float, str]:
    """
    Filter and score a single supplier.
    
    Returns:
        (keep: bool, score: float, reason: str)
    """
    supplier_name = supplier.get('supplier_name', '')
    url = supplier.get('website', '') or supplier.get('source_url', '')
    title = supplier.get('title', '')
    snippet = supplier.get('snippet', '')
    notes = supplier.get('notes', '')
    
    # Check rejection patterns
    should_reject, reject_reason = should_reject_source(url, title, snippet)
    if should_reject:
        return False, 0.0, f"REJECTED: {reject_reason}"
    
    # Score based on signals
    score, signal_breakdown = score_supplier_signals(
        supplier_name, url, title, snippet, notes
    )
    
    # Require at least one signal from each of two categories
    categories_with_signals = sum(1 for count in signal_breakdown.values() if count > 0)
    
    if categories_with_signals < 2:
        reason = f"REJECTED: Insufficient signals (only {categories_with_signals}/4 categories). Breakdown: {signal_breakdown}"
        return False, score, reason
    
    if score < min_score:
        reason = f"REJECTED: Score too low ({score:.2f} < {min_score}). Breakdown: {signal_breakdown}"
        return False, score, reason
    
    reason = f"ACCEPTED: Score {score:.2f}, signals: {signal_breakdown}"
    return True, score, reason


def filter_suppliers(
    suppliers: List[Dict],
    min_score: float = 0.3,
    log_decisions: bool = True
) -> List[Dict]:
    """
    Filter a list of suppliers, keeping only high-quality ones.
    
    Args:
        suppliers: List of supplier dictionaries
        min_score: Minimum score threshold
        log_decisions: Whether to log keep/reject decisions
    
    Returns:
        Filtered list of suppliers with added 'quality_score' field
    """
    filtered = []
    
    for supplier in suppliers:
        keep, score, reason = filter_and_score_supplier(supplier, min_score)
        
        if log_decisions:
            supplier_name = supplier.get('supplier_name', 'Unknown')
            logger.info(f"Supplier '{supplier_name}': {reason}")
        
        if keep:
            supplier['quality_score'] = round(score, 3)
            supplier['quality_signals'] = reason
            filtered.append(supplier)
    
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
