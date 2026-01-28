"""
Module 4 part 1: Machine Data Enrichment.

This module provides pure Python functions to enrich machine specifications
using online search and scraping. It relies on Perplexity (preferred) with
fallbacks to SerpAPI and DuckDuckGo, plus trafilatura/beautifulsoup4.

No FastAPI, no database, no CLI dependencies.
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any

from pydantic import BaseModel, Field

# Optional imports for functionality
try:
    from ddgs import DDGS
except ImportError:
    DDGS = None

try:
    import trafilatura
except ImportError:
    trafilatura = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

# Import search providers (Perplexity + SerpAPI + DuckDuckGo)
try:
    from .search_providers import search_all_providers
    from .database import settings
except ImportError:
    search_all_providers = None
    settings = None

# Import image quality scorer for Module 2
try:
    from .image_quality_scorer import enrich_machine_with_best_image
except ImportError:
    enrich_machine_with_best_image = None

# Import Document AI for PDF spec extraction
try:
    from .document_ai_extractor import DocumentAIExtractor
except ImportError:
    DocumentAIExtractor = None

# Import CAD file scraper (TraceParts, 3D ContentCentral, GrabCAD)
try:
    from .cad_scraper import find_cad_files
except ImportError:
    find_cad_files = None

# Import Gemini spec extractor for unstructured text
try:
    from .gemini_spec_extractor import GeminiSpecExtractor
except ImportError:
    GeminiSpecExtractor = None

# Configure logger (handlers to be configured by caller)
logger = logging.getLogger(__name__)


# ============================================================================
# DATA MODELS
# ============================================================================

class MachineInput(BaseModel):
    """Basic machine information input for enrichment."""
    id: str = Field(..., description="Internal ID (e.g. INJ-001)")
    name: str = Field(..., description="Machine name")
    category: str = Field(..., description="Machine category/type")
    manufacturer: Optional[str] = None
    base_model: Optional[str] = None
    original_specs: Dict[str, Any] = Field(default_factory=dict, description="Original specs from Module 1")


class MachineInputModule1(BaseModel):
    """Machine input matching module1_data.json format with support for NULL/missing values."""
    nom_machine: str = Field(..., description="Machine name (e.g. 'Machine d'injection plastique')")
    type: str = Field(..., description="Machine type/category (e.g. 'Presse à injection')")
    fabricant_recommande: Optional[str] = None
    quantite_necessaire: Optional[int] = None
    use: Optional[str] = None
    
    specifications: Dict[str, Any] = Field(
        default_factory=dict,
        description="Specifications dict with capacite, puissance, dimensions, alimentation (no poids)"
    )
    performance: Dict[str, Any] = Field(
        default_factory=dict,
        description="Performance dict with cadence, rendement, temps_cycle, etc."
    )
    
    def get_null_fields(self) -> Dict[str, str]:
        """
        Detect which fields are NULL/missing and need to be filled by scraping.
        
        Returns dict mapping field name to field type for search strategy.
        Example: {'capacite': 'spec', 'puissance': 'spec', 'cadence': 'performance'}
        """
        null_fields = {}
        
        # Check specifications for NULL values
        for field_name, field_value in self.specifications.items():
            if field_name == 'dimensions' and isinstance(field_value, dict):
                # For nested dimensions, check if any dimension is missing
                for dim_name, dim_value in field_value.items():
                    if dim_name != 'unite' and not dim_value:
                        null_fields[f'dimensions_{dim_name}'] = 'spec'
            elif not field_value:
                null_fields[field_name] = 'spec'
        
        # Check performance for NULL values
        for field_name, field_value in self.performance.items():
            if not field_value:
                null_fields[field_name] = 'performance'
        
        return null_fields
    
    def get_search_query_parts(self) -> List[str]:
        """
        Build search query parts from non-NULL fields.
        Used to construct search queries for missing values.
        
        Returns list of terms: [machine_name, machine_type, manufacturer]
        """
        parts = []
        if self.nom_machine:
            parts.append(self.nom_machine)
        if self.type:
            parts.append(self.type)
        if self.fabricant_recommande:
            parts.append(self.fabricant_recommande)
        return parts
    
    def to_machine_input(self) -> MachineInput:
        """Convert Module1 format to standard MachineInput for backwards compatibility."""
        return MachineInput(
            id=f"M-{self.nom_machine[:3].upper()}",
            name=self.nom_machine,
            category=self.type,
            manufacturer=self.fabricant_recommande.split()[0] if self.fabricant_recommande else None,
            base_model=None,
            original_specs={**self.specifications, **self.performance}
        )


class SpecMetadata(BaseModel):
    """Metadata for a single specification field."""
    source: str = Field(..., description="Where the spec came from (web_scrape, gemini, document_ai, user_provided, etc.)")
    confidence: float = Field(default=0.5, description="Confidence score 0.0-1.0")
    extraction_method: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class MachineSpecs(BaseModel):
    """Enriched machine specifications with source tracking."""
    # Spec values
    capacity: Optional[str] = None
    power: Optional[str] = None
    dimensions: Optional[str] = None
    weight: Optional[str] = None
    raw_specs: Dict[str, str] = Field(default_factory=dict)
    
    # Source tracking for each field
    capacity_metadata: Optional[SpecMetadata] = None
    power_metadata: Optional[SpecMetadata] = None
    dimensions_metadata: Optional[SpecMetadata] = None
    weight_metadata: Optional[SpecMetadata] = None
    
    # Overall specs confidence
    avg_confidence: float = Field(default=0.0, description="Average confidence across all specs")
    confidence_report: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Detailed confidence report per spec field"
    )
    
    def get_field_confidence(self, field_name: str) -> float:
        """Get confidence score for a specific field."""
        metadata_name = f"{field_name}_metadata"
        metadata = getattr(self, metadata_name, None)
        if metadata and hasattr(metadata, 'confidence'):
            return metadata.confidence
        return 0.0
    
    def get_field_source(self, field_name: str) -> Optional[str]:
        """Get source for a specific field."""
        metadata_name = f"{field_name}_metadata"
        metadata = getattr(self, metadata_name, None)
        if metadata and hasattr(metadata, 'source'):
            return metadata.source
        return None
    
    def update_confidence_report(self) -> None:
        """Calculate and update the confidence report."""
        report = {}
        confidences = []
        
        for field_name in ['capacity', 'power', 'dimensions', 'weight']:
            field_value = getattr(self, field_name, None)
            metadata = getattr(self, f"{field_name}_metadata", None)
            
            if field_value:
                conf = metadata.confidence if metadata else 0.5
                confidences.append(conf)
                report[field_name] = {
                    'value': field_value,
                    'confidence': conf,
                    'source': metadata.source if metadata else 'unknown',
                    'extraction_method': metadata.extraction_method if metadata else None,
                    'timestamp': metadata.timestamp.isoformat() if metadata else None
                }
        
        self.confidence_report = report
        self.avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0


class MachineAssets(BaseModel):
    """Enriched machine assets (URLs)."""
    image_urls: List[str] = Field(default_factory=list)
    datasheet_urls: List[str] = Field(default_factory=list)
    cad_urls: List[str] = Field(default_factory=list)


class EnrichedMachine(BaseModel):
    """Fully enriched machine record."""
    input: MachineInput
    specs: MachineSpecs
    assets: MachineAssets
    manufacturer_website: Optional[str] = None
    product_page_url: Optional[str] = None
    sources_used: List[str] = Field(default_factory=list)
    completeness_score: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Module 2 CAD/3D Conversion
    best_image_url: Optional[str] = None
    image_quality_score: float = 0.0
    image_analysis: Dict[str, Any] = Field(default_factory=dict)
    
    # Document AI PDF extraction
    pdf_specs_extracted: Dict[str, Any] = Field(default_factory=dict, description="Specs from PDF datasheets via Document AI")
    
    # CAD file discovery from TraceParts, 3D ContentCentral, GrabCAD
    cad_sources: Dict[str, List[str]] = Field(default_factory=dict, description="CAD files from different sources")
    
    # Gemini LLM extraction
    gemini_specs: Dict[str, Any] = Field(default_factory=dict, description="Specs extracted via Gemini from unstructured text")
    
    def generate_confidence_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive confidence report for all specs.
        
        Returns dict with:
        - per_field: Confidence for each extracted field
        - overall_confidence: Average confidence
        - source_summary: Which APIs/methods were used
        - recommendations: Suggestions for improving confidence
        """
        self.specs.update_confidence_report()
        
        sources_summary = {}
        for field_name, details in self.specs.confidence_report.items():
            source = details.get('source', 'unknown')
            if source not in sources_summary:
                sources_summary[source] = []
            sources_summary[source].append(field_name)
        
        # Generate recommendations
        recommendations = []
        if self.specs.avg_confidence < 0.6:
            recommendations.append("Low confidence scores - consider manual verification")
        if not self.specs.capacity and not self.specs.power:
            recommendations.append("Core specs (capacity/power) missing - search may have failed")
        if not self.assets.image_urls:
            recommendations.append("No images found - consider alternative search terms")
        if self.completeness_score < 0.5:
            recommendations.append("Less than 50% data complete - significant gaps remain")
        
        return {
            'per_field': self.specs.confidence_report,
            'overall_confidence': self.specs.avg_confidence,
            'source_summary': sources_summary,
            'completeness_score': self.completeness_score,
            'field_count_filled': sum(1 for field in ['capacity', 'power', 'dimensions', 'weight'] 
                                      if getattr(self.specs, field)),
            'field_count_total': 4,
            'recommendations': recommendations,
            'timestamp': datetime.now().isoformat()
        }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _clean_text(text: str) -> str:
    """Normalize text by removing extra whitespace."""
    return re.sub(r'\s+', ' ', text).strip()


def _calculate_completeness(machine: EnrichedMachine) -> float:
    """Calculate completeness score (0.0 - 1.0)."""
    score = 0.0
    if machine.specs.capacity: score += 15
    if machine.specs.power: score += 15
    if machine.specs.dimensions: score += 10
    if machine.specs.weight: score += 10
    
    if machine.assets.image_urls: score += 20
    if machine.assets.datasheet_urls: score += 15
    if machine.assets.cad_urls: score += 15
    
    return min(score / 100.0, 1.0)


def _build_field_specific_search_query(field_name: str, machine_input: MachineInputModule1 | MachineInput) -> str:
    """
    Build field-specific search query for a particular NULL field.
    
    Maps field names to targeted search terms to find only missing information.
    """
    # Get machine identifiers
    if isinstance(machine_input, MachineInputModule1):
        machine_name = machine_input.nom_machine
        machine_type = machine_input.type
        manufacturer = machine_input.fabricant_recommande
    else:
        machine_name = machine_input.name
        machine_type = machine_input.category
        manufacturer = machine_input.manufacturer
    
    # Field-specific search strategies
    field_queries = {
        'capacite': f"{machine_name} capacité spécifications tonnage",
        'capacity': f"{machine_name} capacity specifications ton",
        'puissance': f"{machine_name} puissance kW consommation électrique",
        'power': f"{machine_name} power kW horsepower consumption",
        'dimensions': f"{machine_name} dimensions size measurements length width height",
        'longueur': f"{machine_name} dimensions longueur length specifications",
        'largeur': f"{machine_name} dimensions largeur width specifications",
        'hauteur': f"{machine_name} dimensions hauteur height specifications",
        'weight': f"{machine_name} weight mass specifications kg",
        'poids': f"{machine_name} poids masse specifications kg",
        'cadence': f"{machine_name} cadence cycle rate cycles per hour",
        'rendement': f"{machine_name} rendement efficiency performance",
        'temps_cycle': f"{machine_name} temps cycle time duration",
        'alimentation': f"{machine_name} alimentation power supply voltage",
    }
    
    # Return field-specific query or generic fallback
    if field_name in field_queries:
        query = field_queries[field_name]
    else:
        # Generic query for unknown fields
        query = f"{machine_name} {field_name} specifications"
    
    # Add manufacturer if known
    if manufacturer:
        query = f"{query} {manufacturer}"
    
    return query


# ============================================================================
# CORE FUNCTIONS
# ============================================================================

async def _search_with_fallback(query: str, max_results: int = 5) -> List[str]:
    """
    Search using intelligent fallback chain.
    
    Priority:
    1. Perplexity (AI-curated, best understanding)
    2. Tavily (AI-ranked web search)
    3. SerpAPI (Google quality)
    4. DuckDuckGo (free fallback)
    
    Returns list of URLs.
    """
    if search_all_providers and settings:
        try:
            logger.info(f"Searching for: {query}")
            results = await search_all_providers(
                query=query,
                max_results=max_results,
            )
            urls = [r.get("url") for r in results if r.get("url")]
            if urls:
                logger.info(f"Found {len(urls)} URLs from search providers")
                return urls
        except Exception as e:
            logger.error(f"Search provider error: {e}")
    
    # Fallback: DuckDuckGo (free, always available)
    logger.info(f"Falling back to DuckDuckGo for: {query}")
    if DDGS:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                urls = [r.get('href') for r in results if r.get('href')]
                if urls:
                    logger.info(f"DuckDuckGo found {len(urls)} URLs")
                    return urls
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
    
    return []


def search_machine_online(machine: MachineInput, max_results: int = 5, field_name: Optional[str] = None) -> List[str]:
    """
    Search for machine product pages with intelligent fallback chain.
    
    Supports field-specific searches to find only missing information.
    
    Args:
        machine: MachineInput object with machine details
        max_results: Maximum number of results to return
        field_name: Optional field name to use field-specific search query
        
    Orchestrates async search within sync context.
    Returns a list of candidate URLs.
    """
    # If field_name provided, use field-specific search query
    if field_name and isinstance(machine, MachineInput):
        # This is a backward-compatible mode
        query = _build_field_specific_search_query(field_name, machine)
    else:
        # Standard generic search
        query_parts = [machine.manufacturer, machine.base_model, machine.category, "specifications"]
        query = " ".join([p for p in query_parts if p])
    
    logger.info(f"Searching for machine specs: {query}")
    
    # Run async search
    try:
        urls = asyncio.run(_search_with_fallback(query, max_results))
    except RuntimeError as e:
        # asyncio.run() fails if already in event loop
        logger.warning(f"Could not use asyncio.run: {e}, falling back to sync search")
        if DDGS:
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=max_results))
                    urls = [r.get('href') for r in results if r.get('href')]
            except Exception as e:
                logger.error(f"Sync DuckDuckGo search failed: {e}")
                urls = []
        else:
            urls = []
    
    return urls


def scrape_machine_page(url: str) -> Tuple[MachineSpecs, MachineAssets]:
    """
    Scrape a machine product page for specs and assets.
    
    Uses trafilatura for text extraction and BeautifulSoup for links/images.
    """
    specs = MachineSpecs()
    assets = MachineAssets()
    
    if not trafilatura or not BeautifulSoup:
        logger.warning("Scraping libraries (trafilatura/bs4) not installed")
        return specs, assets

    logger.info(f"Scraping {url}")
    
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return specs, assets
            
        # Extract text for specs
        text_content = trafilatura.extract(downloaded, include_tables=True, include_comments=False)
        if text_content:
            # Regex extraction similar to original module
            # Capacity
            cap_match = re.search(r"(\d+[\s\-.]*)(?:tonnes?|tons?|kN|kg\/?h)", text_content, re.IGNORECASE)
            if cap_match: specs.capacity = _clean_text(cap_match.group(0))
            
            # Power
            pow_match = re.search(r"(\d+[\s\-.]*)(?:kW|HP|MW)", text_content, re.IGNORECASE)
            if pow_match: specs.power = _clean_text(pow_match.group(0))
            
            # Dimensions
            dim_match = re.search(r"(\d+[\s\-.]*)[x×](\d+[\s\-.]*)[x×](\d+[\s\-.]*)(?:mm|cm|m)", text_content, re.IGNORECASE)
            if dim_match: specs.dimensions = _clean_text(dim_match.group(0))
            
            # Weight
            w_match = re.search(r"(\d+[\s\-.]*)(?:kg|tonnes?|lbs)", text_content, re.IGNORECASE)
            if w_match: specs.weight = _clean_text(w_match.group(0))

        # Extract assets using BeautifulSoup
        soup = BeautifulSoup(downloaded, 'html.parser')
        
        # Images (heuristic: large enough, likely product images)
        for img in soup.find_all('img', src=True):
            src = img['src']
            if not src.startswith('http'):
                # Simple relative URL handling (could be improved)
                if src.startswith('/'):
                    from urllib.parse import urljoin
                    src = urljoin(url, src)
                else:
                    continue
            
            # skip tiny icons (heuristic filter based on filename usually not possible without headers, 
            # so we just skip obvious common icon names)
            if any(x in src.lower() for x in ['logo', 'icon', 'pixel', 'tracker']):
                continue
                
            assets.image_urls.append(src)
            
        # Datasheets (PDFs)
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.lower().endswith('.pdf'):
                if not href.startswith('http'):
                     from urllib.parse import urljoin
                     href = urljoin(url, href)
                
                link_text = link.get_text().lower()
                if any(x in link_text for x in ['datasheet', 'brochure', 'spec', 'catalog', 'manual']):
                    assets.datasheet_urls.append(href)
                    
        # CAD (STEP, IGES, etc)
        cad_exts = ['.stp', '.step', '.igs', '.iges', '.stl', '.dxf']
        for link in soup.find_all('a', href=True):
            href = link['href']
            if any(href.lower().endswith(ext) for ext in cad_exts):
                if not href.startswith('http'):
                     from urllib.parse import urljoin
                     href = urljoin(url, href)
                assets.cad_urls.append(href)

    except Exception as e:
        logger.error(f"Scraping error on {url}: {e}")

    # Unique assets
    assets.image_urls = list(set(assets.image_urls))
    assets.datasheet_urls = list(set(assets.datasheet_urls))
    assets.cad_urls = list(set(assets.cad_urls))

    return specs, assets


def enrich_machine(machine: MachineInput) -> EnrichedMachine:
    """
    Orchestrate enrichment: search -> scrape -> extract PDFs -> find CAD -> LLM enhancement.
    
    Pipeline:
    1. Search for product URLs
    2. Scrape manufacturer website (images, datasheets, CAD)
    3. Extract specs from PDFs using Document AI (if datasheets found)
    4. Find CAD files from TraceParts, 3D ContentCentral, GrabCAD
    5. Use Gemini to extract specs from unstructured HTML (if needed)
    6. Select best image for Module 2 CAD/3D conversion
    """
    candidate_urls = search_machine_online(machine)
    
    best_specs = MachineSpecs()
    best_assets = MachineAssets()
    product_page = None
    manufacturer_site = None
    
    # Try to find a manufacturer site match
    for url in candidate_urls:
        if machine.manufacturer and machine.manufacturer.lower().replace(" ", "") in url.lower():
            manufacturer_site = url
            # If we don't have a product page yet, assume this is it
            if not product_page:
                product_page = url
    
    # If no specific product page found but we have candidates, pick the first one
    if not product_page and candidate_urls:
        product_page = candidate_urls[0]
        
    sources = []
    if product_page:
        specs, assets = scrape_machine_page(product_page)
        best_specs = specs
        best_assets = assets
        sources.append(product_page)
        
    enriched = EnrichedMachine(
        input=machine,
        specs=best_specs,
        assets=best_assets,
        manufacturer_website=manufacturer_site,
        product_page_url=product_page,
        sources_used=sources
    )
    
    # ============================================================
    # PHASE 1: Document AI PDF Spec Extraction
    # ============================================================
    if DocumentAIExtractor and best_assets.datasheet_urls:
        try:
            logger.info(f"Found {len(best_assets.datasheet_urls)} datasheets, attempting Document AI extraction")
            extractor = DocumentAIExtractor()
            
            # Try first PDF (could be enhanced to try multiple)
            pdf_url = best_assets.datasheet_urls[0]
            logger.info(f"Extracting specs from PDF: {pdf_url}")
            
            # Note: Document AI requires local PDF path, so this would need download first
            # For now, store for async processing
            enriched.pdf_specs_extracted = {
                'pdf_url': pdf_url,
                'status': 'pending_download',
                'note': 'PDF download and extraction requires async processing'
            }
            
        except Exception as e:
            logger.warning(f"Document AI extraction failed: {e}")
    
    # ============================================================
    # PHASE 2: CAD File Discovery (TraceParts, 3D ContentCentral, GrabCAD)
    # ============================================================
    if find_cad_files and machine.manufacturer and machine.base_model:
        try:
            logger.info(f"Searching for CAD files: {machine.manufacturer} {machine.base_model}")
            
            # Run async CAD search synchronously
            try:
                loop = asyncio.get_running_loop()
                # Already in event loop, use it
                cad_results = asyncio.run_coroutine_threadsafe(
                    find_cad_files(machine.manufacturer, machine.base_model, max_results=5),
                    loop
                ).result(timeout=30)
            except RuntimeError:
                # No event loop, create new one
                cad_results = asyncio.run(find_cad_files(machine.manufacturer, machine.base_model, max_results=5))
            
            enriched.cad_sources = cad_results
            
            # Add to assets
            all_cads = []
            for source, urls in cad_results.items():
                all_cads.extend(urls)
            best_assets.cad_urls.extend(all_cads)
            best_assets.cad_urls = list(set(best_assets.cad_urls))  # Remove duplicates
            
            logger.info(f"Found {len(all_cads)} CAD files from {len(cad_results)} sources")
            
        except Exception as e:
            logger.warning(f"CAD file search failed: {e}")
    
    # ============================================================
    # PHASE 3: Gemini Spec Extraction from Unstructured Text
    # ============================================================
    if GeminiSpecExtractor and best_specs.raw_specs:
        try:
            logger.info("Attempting Gemini LLM extraction for unstructured specs")
            
            # Combine raw specs into text
            specs_text = "\n".join([f"{k}: {v}" for k, v in best_specs.raw_specs.items()])
            
            extractor = GeminiSpecExtractor(
                api_key=getattr(settings, "GOOGLE_API_KEY", None) if settings else None
            )
            
            # Run async Gemini extraction
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            
            if loop:
                # Already in event loop
                import asyncio
                task = asyncio.create_task(extractor.extract_specs(
                    specs_text,
                    manufacturer=machine.manufacturer,
                    model=machine.base_model
                ))
                gemini_results = asyncio.run(task)
            else:
                gemini_results = asyncio.run(extractor.extract_specs(
                    specs_text,
                    manufacturer=machine.manufacturer,
                    model=machine.base_model
                ))
            
            enriched.gemini_specs = gemini_results
            logger.info(f"Gemini extracted: {[k for k, v in gemini_results.items() if v and k != 'raw_response']}")
            
        except Exception as e:
            logger.warning(f"Gemini extraction failed: {e}")
    
    enriched.completeness_score = _calculate_completeness(enriched)
    
    # ============================================================
    # PHASE 4: Image Quality Scoring for Module 2
    # ============================================================
    if enrich_machine_with_best_image and best_assets.image_urls:
        try:
            import asyncio as aio
            enriched_dict = enriched.dict()
            enriched_dict['images'] = best_assets.image_urls
            enriched_dict = aio.run(enrich_machine_with_best_image(enriched_dict))
            
            # Add best image info back to enriched object
            enriched.best_image_url = enriched_dict.get('best_image_url')
            enriched.image_quality_score = enriched_dict.get('image_quality_score', 0.0)
            enriched.image_analysis = enriched_dict.get('image_analysis', {})
        except Exception as e:
            logger.warning(f"Image quality scoring failed: {e}")
    
    return enriched


def enrich_machines(machines: List[MachineInput]) -> List[EnrichedMachine]:
    """Batch enrich a list of machines."""
    return [enrich_machine(m) for m in machines]

def enrich_machine_module1(machine_input: MachineInputModule1, search_null_fields_only: bool = True) -> EnrichedMachine:
    """
    Enrich a machine in Module 1 format with intelligent NULL-aware searching.
    
    Args:
        machine_input: MachineInputModule1 with potentially NULL specification fields
        search_null_fields_only: If True, only search for NULL fields (default: True)
        
    Returns:
        EnrichedMachine with filled specifications and images
    """
    logger.info(f"Enriching machine: {machine_input.nom_machine}")
    
    # Detect which fields are NULL and need searching
    null_fields = machine_input.get_null_fields() if search_null_fields_only else {}
    logger.info(f"NULL fields detected: {list(null_fields.keys())}")
    
    # Get search query parts from non-NULL fields
    query_parts = machine_input.get_search_query_parts()
    logger.info(f"Building searches from non-NULL fields: {query_parts}")
    
    # Convert to standard MachineInput for compatibility with existing functions
    standard_input = machine_input.to_machine_input()
    
    # For each NULL field, perform a targeted search
    search_results = {}
    for field_name, field_type in null_fields.items():
        logger.info(f"Searching for NULL field: {field_name}")
        
        # Generate field-specific search query
        search_query = _build_field_specific_search_query(field_name, machine_input)
        logger.info(f"Field-specific query: {search_query}")
        
        # Perform search
        urls = search_machine_online(standard_input, max_results=3)
        if urls:
            search_results[field_name] = urls
            logger.info(f"Found {len(urls)} candidate pages for {field_name}")
    
    # Generic image search (always do this)
    logger.info("Performing generic image search")
    image_search_query = " ".join(query_parts) + " images specifications"
    try:
        image_urls_from_search = asyncio.run(_search_with_fallback(image_search_query, max_results=10))
    except RuntimeError:
        # Already in event loop
        image_urls_from_search = []
    
    # Run standard enrichment pipeline
    enriched = enrich_machine(standard_input)
    
    # Log that this was Module 1 format enrichment
    logger.info(f"Completed Module 1 enrichment for {machine_input.nom_machine}: {enriched.completeness_score:.1%} complete")
    
    return enriched


def enrich_machines_module1(machines: List[MachineInputModule1]) -> List[EnrichedMachine]:
    """Batch enrich a list of machines in Module 1 format with NULL-aware searching."""
    return [enrich_machine_module1(m) for m in machines]