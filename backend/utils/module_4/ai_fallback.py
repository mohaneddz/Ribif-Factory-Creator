"""
AI Fallback Supplier Generation for Module 4

Provides intelligent fallback suppliers using:
1. Typical manufacturers from Phase B (industry knowledge)
2. Category-based curated supplier maps
3. Domain knowledge about known brands/sellers/integrators per machine type

All AI-generated suppliers are marked with is_ai_fallback=True and explanatory notes.
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ============================================================================
# CURATED SUPPLIER MAPS BY CATEGORY
# ============================================================================

CURATED_SUPPLIERS_BY_CATEGORY = {
    # Glass machinery manufacturers
    "glass_tempering": [
        {
            "supplier_name": "Glaston Corporation",
            "region": "Finland/Global",
            "website": "https://www.glaston.net",
            "price_estimate": "â‚¬500,000 - â‚¬2,000,000",
            "price_type": "Ex-works",
            "notes": "AI suggestion: Leading glass tempering furnace manufacturer with global presence",
            "relevance_score": 0.8,
            "is_ai_fallback": True,
            "ai_tag": "â˜…",
            "availability_note": "No public suppliers found; AI suggestion based on domain knowledge"
        },
        {
            "supplier_name": "Bystronic Glass",
            "region": "Switzerland/Global",
            "website": "https://www.bystronic-glass.com",
            "price_estimate": "â‚¬400,000 - â‚¬1,500,000",
            "price_type": "Ex-works",
            "notes": "AI suggestion: Premium glass processing equipment manufacturer",
            "relevance_score": 0.8,
            "is_ai_fallback": True,
            "ai_tag": "â˜…",
            "availability_note": "No public suppliers found; AI suggestion based on domain knowledge"
        },
    ],
    "glass_lamination": [
        {
            "supplier_name": "Glaston Lamination",
            "region": "Finland/Global",
            "website": "https://www.glaston.net",
            "price_estimate": "â‚¬300,000 - â‚¬1,000,000",
            "price_type": "Ex-works",
            "notes": "AI suggestion: Complete lamination line solutions",
            "relevance_score": 0.8,
            "is_ai_fallback": True,
            "ai_tag": "â˜…",
            "availability_note": "No public suppliers found; AI suggestion based on domain knowledge"
        },
    ],
    "glass_bending": [
        {
            "supplier_name": "Hegla GmbH",
            "region": "Germany",
            "website": "https://www.hegla.com",
            "price_estimate": "â‚¬250,000 - â‚¬800,000",
            "price_type": "Ex-works",
            "notes": "AI suggestion: Glass bending and processing machinery",
            "relevance_score": 0.8,
            "is_ai_fallback": True,
            "ai_tag": "â˜…",
            "availability_note": "No public suppliers found; AI suggestion based on domain knowledge"
        },
    ],
    
    # Plastic extrusion
    "extrusion": [
        {
            "supplier_name": "Davis-Standard LLC",
            "region": "USA/Global",
            "website": "https://www.davis-standard.com",
            "price_estimate": "$200,000 - $1,500,000",
            "price_type": "FOB",
            "notes": "AI suggestion: Leading extrusion systems and complete lines",
            "relevance_score": 0.8,
            "is_ai_fallback": True,
            "ai_tag": "â˜…",
            "availability_note": "No public suppliers found; AI suggestion based on domain knowledge"
        },
        {
            "supplier_name": "Battenfeld-Cincinnati",
            "region": "Germany/USA",
            "website": "https://www.battenfeld-cincinnati.com",
            "price_estimate": "â‚¬150,000 - â‚¬1,200,000",
            "price_type": "Ex-works",
            "notes": "AI suggestion: Extrusion lines and downstream equipment",
            "relevance_score": 0.8,
            "is_ai_fallback": True,
            "ai_tag": "â˜…",
            "availability_note": "No public suppliers found; AI suggestion based on domain knowledge"
        },
    ],
    
    # Thermoforming
    "thermoforming": [
        {
            "supplier_name": "ILLIG Maschinenbau",
            "region": "Germany",
            "website": "https://www.illig.de",
            "price_estimate": "â‚¬200,000 - â‚¬800,000",
            "price_type": "Ex-works",
            "notes": "AI suggestion: World leader in thermoforming technology",
            "relevance_score": 0.9,
            "is_ai_fallback": True, "ai_tag": "★",
            "availability_note": "No public suppliers found; AI suggestion based on domain knowledge"
        },
        {
            "supplier_name": "Kiefel GmbH",
            "region": "Germany",
            "website": "https://www.kiefel.com",
            "price_estimate": "â‚¬180,000 - â‚¬750,000",
            "price_type": "Ex-works",
            "notes": "AI suggestion: Premium thermoforming and packaging machinery",
            "relevance_score": 0.9,
            "is_ai_fallback": True, "ai_tag": "★",
            "availability_note": "No public suppliers found; AI suggestion based on domain knowledge"
        },
    ],
    
    # Injection molding
    "injection_molding": [
        {
            "supplier_name": "Engel Austria GmbH",
            "region": "Austria/Global",
            "website": "https://www.engelglobal.com",
            "price_estimate": "â‚¬80,000 - â‚¬500,000",
            "price_type": "Ex-works",
            "notes": "AI suggestion: Premium injection molding machines, global leader",
            "relevance_score": 0.9,
            "is_ai_fallback": True, "ai_tag": "★",
            "availability_note": "No public suppliers found; AI suggestion based on domain knowledge"
        },
        {
            "supplier_name": "Haitian International",
            "region": "China/Global",
            "website": "https://www.haitian.com",
            "price_estimate": "$50,000 - $300,000",
            "price_type": "FOB",
            "notes": "AI suggestion: High-volume injection molding manufacturer",
            "relevance_score": 0.8,
            "is_ai_fallback": True, "ai_tag": "★",
            "availability_note": "No public suppliers found; AI suggestion based on domain knowledge"
        },
        {
            "supplier_name": "Arburg GmbH",
            "region": "Germany",
            "website": "https://www.arburg.com",
            "price_estimate": "â‚¬100,000 - â‚¬600,000",
            "price_type": "Ex-works",
            "notes": "AI suggestion: Premium injection molding technology",
            "relevance_score": 0.9,
            "is_ai_fallback": True, "ai_tag": "★",
            "availability_note": "No public suppliers found; AI suggestion based on domain knowledge"
        },
    ],
    
    # Painting robots
    "painting_robot": [
        {
            "supplier_name": "DÃ¼rr Systems AG",
            "region": "Germany",
            "website": "https://www.durr.com",
            "price_estimate": "â‚¬150,000 - â‚¬500,000",
            "price_type": "Ex-works",
            "notes": "AI suggestion: Leading painting and surface finishing automation",
            "relevance_score": 0.9,
            "is_ai_fallback": True, "ai_tag": "★",
            "availability_note": "No public suppliers found; AI suggestion based on domain knowledge"
        },
        {
            "supplier_name": "ABB Robotics",
            "region": "Global",
            "website": "https://new.abb.com/products/robotics",
            "price_estimate": "â‚¬80,000 - â‚¬300,000",
            "price_type": "Ex-works",
            "notes": "AI suggestion: Industrial robots for painting applications",
            "relevance_score": 0.8,
            "is_ai_fallback": True, "ai_tag": "★",
            "availability_note": "No public suppliers found; AI suggestion based on domain knowledge"
        },
    ],
    
    # Membrane press
    "membrane_press": [
        {
            "supplier_name": "IMA Schelling Group",
            "region": "Austria/Italy",
            "website": "https://www.ima.it",
            "price_estimate": "â‚¬100,000 - â‚¬400,000",
            "price_type": "Ex-works",
            "notes": "AI suggestion: Vacuum membrane press systems for furniture",
            "relevance_score": 0.8,
            "is_ai_fallback": True, "ai_tag": "★",
            "availability_note": "No public suppliers found; AI suggestion based on domain knowledge"
        },
    ],
    
    # Recycling/granulation
    "recycling_granulation": [
        {
            "supplier_name": "EREMA Engineering Recycling",
            "region": "Austria",
            "website": "https://www.erema.at",
            "price_estimate": "â‚¬150,000 - â‚¬600,000",
            "price_type": "Ex-works",
            "notes": "AI suggestion: Leading plastic recycling systems manufacturer",
            "relevance_score": 0.9,
            "is_ai_fallback": True, "ai_tag": "★",
            "availability_note": "No public suppliers found; AI suggestion based on domain knowledge"
        },
        {
            "supplier_name": "Rapid Granulator",
            "region": "Sweden",
            "website": "https://www.rapidgranulator.com",
            "price_estimate": "â‚¬30,000 - â‚¬200,000",
            "price_type": "Ex-works",
            "notes": "AI suggestion: Industrial granulators and size reduction equipment",
            "relevance_score": 0.8,
            "is_ai_fallback": True, "ai_tag": "★",
            "availability_note": "No public suppliers found; AI suggestion based on domain knowledge"
        },
    ],
    
    # Automated door lines
    "door_automation": [
        {
            "supplier_name": "HOMAG Group",
            "region": "Germany",
            "website": "https://www.homag.com",
            "price_estimate": "â‚¬200,000 - â‚¬1,000,000",
            "price_type": "Ex-works",
            "notes": "AI suggestion: Complete door manufacturing lines and automation",
            "relevance_score": 0.8,
            "is_ai_fallback": True, "ai_tag": "★",
            "availability_note": "No public suppliers found; AI suggestion based on domain knowledge"
        },
    ],
    
    # Generic/unknown
    "generic": [
        {
            "supplier_name": "Regional Industrial Equipment Distributors",
            "region": "Algeria/MENA",
            "website": "",
            "price_estimate": "Contact for quote",
            "price_type": "Regional",
            "notes": "AI suggestion: General industrial machinery distributors in MENA region",
            "relevance_score": 0.5,
            "is_ai_fallback": True, "ai_tag": "★",
            "availability_note": "No public suppliers found; generic AI suggestion"
        },
    ],
}

# ============================================================================
# CATEGORY DETECTION FROM CANONICAL NAME
# ============================================================================

def detect_category_from_canonical(canonical_name: str) -> str:
    """
    Detect supplier category from canonical machine name.
    
    Args:
        canonical_name: Canonical machine name
        
    Returns:
        Category key for CURATED_SUPPLIERS_BY_CATEGORY
    """
    name_lower = canonical_name.lower()
    
    # Glass machinery
    if 'glass' in name_lower:
        if 'temper' in name_lower:
            return 'glass_tempering'
        elif 'laminat' in name_lower:
            return 'glass_lamination'
        elif 'bend' in name_lower or 'curve' in name_lower:
            return 'glass_bending'
    
    # Plastic machinery
    if 'extru' in name_lower:
        return 'extrusion'
    if 'thermoform' in name_lower:
        return 'thermoforming'
    if 'injection' in name_lower or 'molding' in name_lower:
        return 'injection_molding'
    
    # Robotics
    if 'paint' in name_lower and 'robot' in name_lower:
        return 'painting_robot'
    
    # Membrane press
    if 'membrane' in name_lower and 'press' in name_lower:
        return 'membrane_press'
    
    # Recycling
    if 'recycl' in name_lower or 'granulat' in name_lower:
        return 'recycling_granulation'
    
    # Doors
    if 'door' in name_lower and ('automat' in name_lower or 'line' in name_lower):
        return 'door_automation'
    
    return 'generic'


# ============================================================================
# AI FALLBACK SUPPLIER GENERATION
# ============================================================================

def generate_ai_fallback_suppliers(
    canonical_name: str,
    typical_manufacturers: Optional[List[str]] = None,
    max_suppliers: int = 3
) -> List[Dict]:
    """
    Generate AI fallback suppliers when no public suppliers are found.
    
    Strategy:
    1. Use typical_manufacturers from Phase B if available
    2. Use category-based curated suppliers
    3. Add explanatory metadata (is_ai_fallback, ai_tag, notes, availability_note)
    
    Args:
        canonical_name: Canonical machine name
        typical_manufacturers: Known manufacturers from Phase B industry knowledge
        max_suppliers: Maximum number of AI suppliers to generate
        
    Returns:
        List of AI-generated supplier dictionaries with is_ai_fallback=True
    """
    ai_suppliers = []
    
    # Strategy 1: Use typical manufacturers from Phase B
    if typical_manufacturers and len(typical_manufacturers) > 0:
        logger.info(f"Generating AI fallback from typical manufacturers: {typical_manufacturers}")
        
        for i, mfr_name in enumerate(typical_manufacturers[:max_suppliers]):
            ai_supplier = {
                "supplier_name": mfr_name,
                "region": "Global",
                "website": "",
                "price_estimate": "Contact for quote",
                "price_type": "Indicative",
                "notes": f"AI suggestion: Known manufacturer for {canonical_name} (from industry database)",
                "relevance_score": 0.7,
                "is_ai_fallback": True, "ai_tag": "★",
                "availability_note": "No public suppliers found; AI suggestion based on typical manufacturers",
                "emails": [],
                "phones": [],
                "contact_pages": [],
                "quality_score": 0.65,
                "evidence": ["Typical manufacturer from industry knowledge"]
            }
            ai_suppliers.append(ai_supplier)
    
    # Strategy 2: Use category-based curated suppliers
    if len(ai_suppliers) < max_suppliers:
        category = detect_category_from_canonical(canonical_name)
        logger.info(f"Detected category '{category}' for {canonical_name}")
        
        curated = CURATED_SUPPLIERS_BY_CATEGORY.get(category, [])
        
        # Add curated suppliers (avoiding duplicates with typical manufacturers)
        existing_names = {s['supplier_name'].lower() for s in ai_suppliers}
        
        for curated_supplier in curated:
            if len(ai_suppliers) >= max_suppliers:
                break
            
            if curated_supplier['supplier_name'].lower() not in existing_names:
                # Ensure all required fields are present
                supplier_copy = curated_supplier.copy()
                supplier_copy.setdefault('emails', [])
                supplier_copy.setdefault('phones', [])
                supplier_copy.setdefault('contact_pages', [])
                supplier_copy.setdefault('quality_score', 0.70)
                supplier_copy.setdefault('evidence', ['Curated AI suggestion from domain knowledge'])
                
                ai_suppliers.append(supplier_copy)
                existing_names.add(supplier_copy['supplier_name'].lower())
    
    logger.info(f"Generated {len(ai_suppliers)} AI fallback suppliers for {canonical_name}")
    return ai_suppliers


def add_no_suppliers_subtext(machine_result: Dict) -> Dict:
    """
    Add no_public_suppliers_subtext to machine result when applicable.
    
    Args:
        machine_result: Machine enrichment result dictionary
        
    Returns:
        Modified machine_result with subtext added
    """
    suppliers = machine_result.get('suppliers', [])
    
    # Check if all suppliers are AI-generated
    all_ai = all(s.get('is_ai_fallback', False) for s in suppliers) if suppliers else True
    
    if all_ai or len(suppliers) == 0:
        machine_result['no_public_suppliers_subtext'] = (
            "No public suppliers available for this machine/material. "
            "Suggestions below are AI-generated based on industry knowledge."
        )
        logger.info(f"Added no_public_suppliers_subtext to {machine_result.get('machine_input', {}).get('canonical_name', 'unknown')}")
    
    return machine_result

