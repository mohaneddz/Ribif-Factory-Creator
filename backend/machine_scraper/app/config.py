"""Domain trust and quality configuration.

Defines trusted domains, marketplace filters, and scoring weights.
"""

# High-trust domains (OEMs, manufacturers, established suppliers)
TRUSTED_DOMAINS = {
    "billion.fr",
    "chenhsong.eu",
    "wittmann-group.com",
    "dayamachinery.com",
    "eurotechmachinery.com",
    "extrudex.de",
    "hansweber.de",
    "gtmsmart.com",
    "visualpackaging.com",
    "mikformen.com",
    "smartpackmachine.com",
    "europur.org",
    "ivk-europe.com",
    "vfse.org",
    "quimidroga.com",
    "lanyasilane.de",
    "moseta.eu",
    "senssefloor.com",
    "proluxefloor.com",
    "bynewmaterials.com",
    "pcc.eu",
    "alfredkochen.de",
    "schulz-farben.de",
    "foampartner.com",
    "novalglass.com",
    "mecanumeric.com",
    "rodbolpack.com",
    "cms.it",
    "zappe.com",
    "yjing-extrusion.com",
    "jwellextrusions.com",
    "euro-machinery.com",
}

# Low-trust domains (marketplaces, directories, forums - to deprioritize)
LOW_TRUST_DOMAINS = {
    "alibaba.com",
    "made-in-china.com",
    "indiamart.com",
    "globalspec.com",
    "thomasnet.com",
    "europages.com",
    "pinterest.com",
    "youtube.com",
    "twitter.com",
    "facebook.com",
    "linkedin.com",
    "reddit.com",
    "slideshare.net",
    "medium.com",
    "quora.com",
}

# Marketplace filter (skip entirely)
MARKETPLACE_DOMAINS = {
    "alibaba.com",
    "aliexpress.com",
    "made-in-china.com",
    "indiamart.com",
    "globalsources.com",
    "amazon.com",
    "ebay.com",
}

# PDF and non-HTML content to skip
SKIP_EXTENSIONS = {".pdf", ".ppt", ".pptx", ".xls", ".xlsx", ".doc", ".docx"}

# Scoring weights for result ranking
SCORING_WEIGHTS = {
    "semantic_score": 0.35,      # How well content matches query
    "provider_count": 0.25,       # How many providers found this URL (1-3)
    "contact_presence": 0.25,     # Has email or phone extracted
    "domain_trust": 0.15,         # Trusted domain bonus
}

# Domain trust score mapping
DOMAIN_TRUST_SCORES = {
    "trusted": 1.0,
    "neutral": 0.6,
    "low_trust": 0.4,
    "marketplace": 0.1,
}
