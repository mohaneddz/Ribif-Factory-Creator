"""
Configuration for Zero-Shot Enrichment
======================================

Adjust these settings to control the behavior of the zero-shot enrichment system.
"""

# =========================================================
# Query Budget Settings
# =========================================================

# Maximum number of web search queries per machine
# Recommendation: 1 for fast processing, 2-3 for detailed enrichment
MAX_QUERIES_PER_MACHINE = 1

# Whether to enable zero-shot enrichment (vs legacy method)
ENABLE_ZERO_SHOT_ENRICHMENT = True

# =========================================================
# Currency & Pricing Settings
# =========================================================

# USD to DZD exchange rate
# Update this periodically based on current rates
USD_TO_DZD_RATE = 160

# Import tariff rate for industrial equipment in Algeria
# Typical range: 10-25% depending on equipment type
IMPORT_TARIFF_RATE = 0.15  # 15%

# Additional costs to consider (as percentage of FOB price)
ADDITIONAL_COSTS = {
    "shipping": 0.05,      # 5% shipping cost
    "insurance": 0.02,     # 2% insurance
    "customs_fees": 0.03,  # 3% customs processing
    "installation": 0.05,  # 5% installation (optional)
}

# =========================================================
# Regional Preferences
# =========================================================

# Priority order for supplier regions
SUPPLIER_REGION_PRIORITY = [
    "Algeria",
    "Tunisia",
    "Morocco",
    "Turkey",
    "UAE",
    "Egypt",
    "France",
    "Italy",
    "Germany",
    "China"
]

# Default location for projects
DEFAULT_COUNTRY = "Algeria"
DEFAULT_CITY = "Algiers"
DEFAULT_ZONE = "Zone industrielle (Rouiba/Reghaia)"

# =========================================================
# LLM Settings
# =========================================================

# Temperature for LLM calls (0.0 = deterministic, 1.0 = creative)
QUERY_GENERATION_TEMPERATURE = 0.3
GAP_ANALYSIS_TEMPERATURE = 0.2
ESTIMATION_TEMPERATURE = 0.4

# Model to use for enrichment
ENRICHMENT_MODEL = "gemini-2.5-flash-lite"  # Fast and cost-effective

# =========================================================
# Search Settings
# =========================================================

# Maximum search results per query
MAX_SEARCH_RESULTS_PER_QUERY = 5

# Web search timeout (seconds)
SEARCH_TIMEOUT = 15

# Delay between searches to respect rate limits (seconds)
SEARCH_DELAY = 0.2

# =========================================================
# Data Quality Settings
# =========================================================

# Minimum confidence threshold for using web data
MIN_CONFIDENCE_THRESHOLD = 0.5

# Required fields that must be filled (or estimated)
REQUIRED_FIELDS = [
    "manufacturer",
    "capacity",
    "power",
    "price"
]

# Fields that can remain empty if not found
OPTIONAL_FIELDS = [
    "weight",
    "dimensions",
    "lead_time",
    "warranty"
]

# =========================================================
# Estimation Defaults
# =========================================================

# Default values for common equipment types when no data is found
EQUIPMENT_DEFAULTS = {
    "injection_molding": {
        "power_per_ton": 1.5,  # kW per ton of clamping force
        "weight_per_ton": 25,  # kg per ton of clamping force
        "price_per_ton_usd": 2000,  # USD per ton (rough estimate)
    },
    "extruder": {
        "power_per_mm_diameter": 2.0,  # kW per mm of screw diameter
        "price_per_mm_usd": 3000,  # USD per mm
    },
    "press": {
        "power_per_ton": 0.8,  # kW per ton of press force
        "price_per_ton_usd": 500,  # USD per ton
    },
    "cnc_machine": {
        "power_kw": 15,  # Average power
        "price_range_usd": [50000, 200000],  # Typical range
    }
}

# =========================================================
# Timeout & Retry Settings
# =========================================================

# Maximum time for enriching a single machine (seconds)
MACHINE_ENRICHMENT_TIMEOUT = 90

# Number of retries for failed LLM calls
LLM_RETRY_COUNT = 2

# Number of retries for failed web searches
SEARCH_RETRY_COUNT = 1

# =========================================================
# Logging Settings
# =========================================================

# Log level for enrichment process
ENRICHMENT_LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR

# Whether to log full LLM responses
LOG_FULL_LLM_RESPONSES = False

# Whether to log all search results
LOG_ALL_SEARCH_RESULTS = False

# =========================================================
# Feature Flags
# =========================================================

# Enable/disable specific features
FEATURES = {
    "query_generation": True,      # Use LLM to generate queries
    "gap_analysis": True,          # Analyze gaps after each search
    "educated_estimation": True,   # Fill gaps with estimates
    "dzd_conversion": True,        # Convert to DZD currency
    "algeria_focus": True,         # Prioritize Algeria suppliers
    "supplier_enrichment": True,   # Enrich supplier data
    "spec_extraction": True,       # Extract specs from search
    "price_estimation": True,      # Estimate prices when missing
}

# =========================================================
# Advanced Settings
# =========================================================

# Parallel processing settings
MAX_PARALLEL_MACHINES = 7

# Cache settings
ENABLE_SEARCH_CACHE = False
CACHE_EXPIRY_HOURS = 0

# Quality assurance
ENABLE_ESTIMATION_REVIEW = True
ESTIMATION_CONFIDENCE_PENALTY = 0.2  # Reduce confidence for estimated values

# =========================================================
# Helper Functions
# =========================================================

def get_config():
    """Get all configuration as a dictionary."""
    import sys
    module = sys.modules[__name__]
    config = {}
    for key in dir(module):
        if key.isupper() and not key.startswith('_'):
            config[key] = getattr(module, key)
    return config


def update_config(**kwargs):
    """Update configuration values dynamically."""
    import sys
    module = sys.modules[__name__]
    for key, value in kwargs.items():
        if hasattr(module, key):
            setattr(module, key, value)
        else:
            raise ValueError(f"Unknown configuration key: {key}")


def reset_config():
    """Reset all configuration to default values."""
    # This would reload the module - implement if needed
    pass
