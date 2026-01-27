"""
Helper function to format enriched machine output cleanly.

Removes unnecessary fields and converts field names to French.
Preserves all input fields and merges with scraped values.
"""

from typing import Dict, Any, Optional


def format_enriched_output(enriched, input_data=None) -> Dict[str, Any]:
    """
    Format enriched machine output for clean JSON export.
    
    - Removes: image_analysis, pdf_specs_extracted, timestamp
    - Removes: original_specs (keeps only extracted specs)
    - Preserves all specification fields from input (even if null)
    - Merges scraped values with input values
    - Keeps null values for untouched fields
    """
    
    # Map English spec names to French
    spec_mapping = {
        'capacity': 'capacite',
        'power': 'puissance',
        'dimensions': 'dimensions',
        'weight': 'poids'
    }
    
    # Build specifications - merge input with scraped values
    specs_french = {}
    
    # If input_data provided, preserve its structure
    if input_data and hasattr(input_data, 'specifications'):
        input_specs = input_data.specifications
        # Preserve all input specification fields
        for key, value in input_specs.items():
            specs_french[key] = value
    
    # Overlay scraped values (only if they exist)
    if enriched.specs.capacity:
        specs_french['capacite'] = enriched.specs.capacity
    if enriched.specs.power:
        specs_french['puissance'] = enriched.specs.power
    if enriched.specs.dimensions:
        specs_french['dimensions'] = enriched.specs.dimensions
    if enriched.specs.weight:
        specs_french['poids'] = enriched.specs.weight
    
    # Build performance - preserve input performance data
    performance_data = {}
    if input_data and hasattr(input_data, 'performance'):
        input_perf = input_data.performance
        # Preserve all input performance fields
        for key, value in input_perf.items():
            performance_data[key] = value
    
    # Determine use value - keep null if not provided, otherwise use input value
    use_value = None
    if input_data and hasattr(input_data, 'use'):
        use_value = input_data.use
    
    # Determine quantite_necessaire
    quantite_value = None
    if input_data and hasattr(input_data, 'quantite_necessaire'):
        quantite_value = input_data.quantite_necessaire
    
    # Build clean output
    output = {
        "nom_machine": enriched.input.name,
        "type": enriched.input.category,
        "fabricant_recommande": enriched.input.manufacturer,
        "quantite_necessaire": quantite_value,
        "use": use_value,
        
        "specifications": specs_french,
        "performance": performance_data,
        
        "assets": {
            "image_urls": enriched.assets.image_urls,
            "datasheet_urls": enriched.assets.datasheet_urls,
            "cad_urls": enriched.assets.cad_urls
        },
        
        "best_image_url": enriched.best_image_url,
        "image_quality_score": enriched.image_quality_score,
        
        "manufacturer_website": enriched.manufacturer_website,
        "product_page_url": enriched.product_page_url,
        
        "completeness_score": enriched.completeness_score
    }
    
    return output
