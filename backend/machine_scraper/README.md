# Machine Scraper Tool

Autonomous web scraping tool for industrial machine specifications and images.

## Overview

This tool searches the web for industrial machines, scrapes their specifications, extracts images, and scores them using Google Cloud Vision API for CAD/3D conversion suitability.

## Quick Start

### 1. Setup

```bash
cd machine_scraper
pip install -r requirements.txt
```

Set up Google Cloud credentials:
```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS="$(pwd)\ribif-module4-key.json"
```

### 2. Input Format

Create/edit `machines_to_scrape.json` with machines in this format:

```json
{
  "machines": [
    {
      "nom_machine": "Machine name",
      "type": "Machine type",
      "fabricant_recommande": "Recommended manufacturer",
      "quantite_necessaire": null,
      "use": null,
      "specifications": {
        "capacite": null,
        "puissance": "300 kW",
        "dimensions": {
          "longueur": null,
          "largeur": "4 m",
          "hauteur": "6 m",
          "unite": "m"
        }
      },
      "performance": {
        "cadence": "30 cycles/heure",
        "rendement": "95 %",
        "temps_cycle": "2 minutes"
      }
    }
  ]
}
```

### 3. Run Scraper

```bash
python scrape_from_json.py
```

Output will be saved to `output/scraping_results.json`

## Output Format

```json
{
  "nom_machine": "Machine d'injection plastique",
  "type": "Presse à injection",
  "fabricant_recommande": "KraussMaffei",
  "quantite_necessaire": null,
  "use": null,
  "specifications": {
    "capacite": "500 kN",
    "puissance": "300 kW",
    "dimensions": {...},
    "alimentation": "380 V, 3 phases, 50 Hz"
  },
  "performance": {
    "cadence": "30 cycles/heure",
    "rendement": "95 %",
    "temps_cycle": "2 minutes"
  },
  "assets": {
    "image_urls": [...],
    "datasheet_urls": [],
    "cad_urls": []
  },
  "best_image_url": "...",
  "image_quality_score": 47.8,
  "manufacturer_website": "...",
  "product_page_url": "...",
  "completeness_score": 0.35
}
```

## Files

- `scrape_from_json.py` - Main batch processing script
- `machines_to_scrape.json` - Input machine definitions
- `app/machine_enrichment.py` - Core enrichment pipeline
- `app/image_quality_scorer.py` - Vision API integration and image selection
- `app/output_formatter.py` - Output formatting with French field names
- `app/search_providers.py` - Web search with fallback chain (Perplexity, Tavily, SerpAPI, DuckDuckGo)
- `app/scraper.py` - Web page scraping
- `test_scraper_simple.py` - Test with hardcoded machine
- `test_scraper_json_input.py` - Test with single JSON machine

## Features

- **Multi-source web search** with intelligent fallback
- **Spec extraction** from product pages
- **Image scraping** with filtering to exclude non-product images
- **Vision API scoring** for image quality and CAD suitability
- **Batch processing** from JSON input file
- **French field names** in output (matches input format)
- **Preservation** of input values for unmatched specs
