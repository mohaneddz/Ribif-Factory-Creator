"""
Zero-Shot Intelligent Machine Enrichment Module
================================================

This module implements an intelligent, self-directed enrichment system that:
1. Extracts vague machine descriptions from documents
2. Uses LLM to generate smart web search queries
3. Performs web searches to find real machines matching specifications
4. Analyzes gaps and determines if more queries are needed
5. Makes educated estimations for publicly unavailable data
6. Converts pricing to DZD (Algeria) with appropriate tariffs

Key Features:
- Query limit tracking (max 2 queries per machine by default)
- Gap analysis after each search iteration
- Intelligent query refinement based on missing data
- Currency conversion to DZD (USD * 160 + tariffs)
- Algeria-focused sourcing with fallback to international suppliers
"""

import json
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from utils.logger import get_logger
from vertex_utils import generate_message
from utils.web_search.aggregator import search_machine_suppliers, search_general
from utils.web_search.base import SearchResult

# Import configuration
try:
    from utils.module_1.zero_shot_config import (
        MAX_QUERIES_PER_MACHINE,
        USD_TO_DZD_RATE,
        IMPORT_TARIFF_RATE,
        QUERY_GENERATION_TEMPERATURE,
        GAP_ANALYSIS_TEMPERATURE,
        ESTIMATION_TEMPERATURE,
        MAX_SEARCH_RESULTS_PER_QUERY,
        SEARCH_DELAY,
    )
except ImportError:
    # Fallback to defaults if config not available
    MAX_QUERIES_PER_MACHINE = 1
    USD_TO_DZD_RATE = 160
    IMPORT_TARIFF_RATE = 0.15
    QUERY_GENERATION_TEMPERATURE = 0.3
    GAP_ANALYSIS_TEMPERATURE = 0.2
    ESTIMATION_TEMPERATURE = 0.4
    MAX_SEARCH_RESULTS_PER_QUERY = 5
    SEARCH_DELAY = 0.2

logger = get_logger(__name__)

# =========================================================
# Data Classes
# =========================================================

@dataclass
class QueryBudget:
    """Tracks query usage per machine."""
    machine_name: str
    max_queries: int = MAX_QUERIES_PER_MACHINE
    queries_used: int = 0
    queries_history: List[str] = field(default_factory=list)
    
    def can_query(self) -> bool:
        """Check if more queries are allowed."""
        return self.queries_used < self.max_queries
    
    def remaining(self) -> int:
        """Get remaining query count."""
        return max(0, self.max_queries - self.queries_used)
    
    def consume(self, query: str) -> bool:
        """Consume one query if available."""
        if self.can_query():
            self.queries_used += 1
            self.queries_history.append(query)
            logger.info(f"Query {self.queries_used}/{self.max_queries} used for {self.machine_name}: {query}")
            return True
        return False


@dataclass
class MachineData:
    """Structured machine data for enrichment."""
    name: str
    raw_description: str
    machine_type: str
    specifications: Dict[str, Any] = field(default_factory=dict)
    suppliers: List[Dict[str, Any]] = field(default_factory=list)
    pricing: Dict[str, Any] = field(default_factory=dict)
    gaps: List[str] = field(default_factory=list)
    confidence: str = "low"
    search_results: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "nom_machine": self.name,
            "description": self.raw_description,
            "type": self.machine_type,
            "specifications": self.specifications,
            "suppliers": self.suppliers,
            "pricing": self.pricing,
            "confidence": self.confidence,
            "gaps": self.gaps,
            "search_sources": self.search_results
        }


# =========================================================
# Prompts
# =========================================================

QUERY_GENERATION_PROMPT = """You are an expert industrial equipment researcher.

MACHINE DESCRIPTION (raw from document):
{raw_description}

CURRENT DATA COLLECTED:
{current_data}

IDENTIFIED GAPS:
{gaps}

QUERIES REMAINING: {remaining_queries}

TASK:
Generate {num_queries} highly specific web search queries to find:
- Real manufacturer models matching the specifications
- Technical specifications (capacity, power, dimensions)
- Pricing information (FOB, CIF Algeria if possible)
- Suppliers/distributors in Algeria or nearby (MENA, Europe)

REQUIREMENTS:
1. Queries must be specific and actionable
2. Include manufacturer brands if known (e.g., "Haitian", "Engel", "Arburg" for injection molding)
3. Include capacity/specs from the description
4. Target Algeria/MENA region when relevant
5. Focus on filling the IDENTIFIED GAPS

LOCATION CONTEXT: Algeria (so prioritize MENA, Europe, Turkey suppliers)

OUTPUT FORMAT (JSON only):
{{
  "queries": [
    "query 1 - specific search string",
    "query 2 - specific search string"
  ],
  "reasoning": "Why these queries will fill the gaps"
}}

EXAMPLES:
- "Haitian injection molding machine 100 ton to 5000 ton specifications price"
- "industrial injection molding equipment suppliers Algeria MENA"
- "plastic injection machine 100-5000T FOB price distributors"
"""

GAP_ANALYSIS_PROMPT = """You are an expert industrial analyst.

MACHINE: {machine_name}
RAW DESCRIPTION: {raw_description}

SEARCH RESULTS OBTAINED:
{search_results}

CURRENT DATA:
{current_data}

TASK:
Analyze if we have ENOUGH information to proceed with educated estimates.

CRITICAL FIELDS (must have at least 2 of these):
1. Machine type/category
2. Capacity or technical specs
3. General manufacturer brands (even generic ones)

OUTPUT FORMAT (JSON only):
{{
  "gaps": [
    "missing field 1",
    "missing field 2"
  ],
  "critical_gaps": [
    "essential field (only if NONE of the critical fields exist)"
  ],
  "confidence_level": "low/medium/high",
  "needs_more_queries": true/false,
  "reasoning": "Why we can or cannot proceed with estimates"
}}

IMPORTANT:
- If we have machine type + general specs: needs_more_queries = false (we can estimate the rest)
- If we have ANY manufacturer brand: needs_more_queries = false (we can estimate models/pricing)
- Only set needs_more_queries = true if we have ZERO useful information
- Most data (pricing, exact specs) can be estimated - web search is NOT required
- Prefer estimation over additional queries for speed
"""

ESTIMATION_PROMPT = """You are a senior industrial engineer specializing in factory equipment.

MACHINE: {machine_name}
DESCRIPTION: {raw_description}
MACHINE TYPE: {machine_type}

DATA COLLECTED:
{collected_data}

REMAINING GAPS:
{gaps}

CONTEXT:
- Location: Algeria
- Currency: DZD (1 USD ≈ 160 DZD + 15% import tariff for new equipment)
- Market: Industrial manufacturing sector

TASK:
Provide EDUCATED ESTIMATIONS for all remaining gaps using:
1. Industry standards for similar equipment
2. Typical capacity/power ranges for this machine type
3. Regional pricing patterns (Algeria imports from Europe, Turkey, China)
4. Engineering best practices

OUTPUT FORMAT (JSON only):
{{
  "estimated_fields": {{
    "field_name": {{
      "value": "estimated value with unit",
      "source": "estimation",
      "confidence": "low/medium/high",
      "rationale": "Why this estimate makes sense"
    }}
  }},
  "manufacturer_recommendations": [
    {{"brand": "Brand 1", "rationale": "Why this brand fits"}},
    {{"brand": "Brand 2", "rationale": "Why this brand fits"}}
  ],
  "pricing_estimate": {{
    "price_range_usd": [min, max],
    "price_range_dzd": [min, max],
    "includes_tariff": true/false,
    "rationale": "Pricing reasoning"
  }}
}}

IMPORTANT:
- Be conservative with estimates
- Clearly mark all values as estimates
- Provide solid engineering rationale
- Consider Algeria's import market (typically 10-30% markup over FOB)
"""

# =========================================================
# Core Enricher Class
# =========================================================

class ZeroShotEnricher:
    """
    Intelligent zero-shot enrichment system for industrial machines.
    """
    
    def __init__(self, max_queries_per_machine: int = MAX_QUERIES_PER_MACHINE):
        self.max_queries_per_machine = max_queries_per_machine
        logger.info(f"ZeroShotEnricher initialized with max {max_queries_per_machine} queries per machine")
    
    def enrich_machine(self, machine_raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main enrichment pipeline for a single machine.
        
        Args:
            machine_raw: Raw machine data from document extraction
            
        Returns:
            Enriched machine data with all available fields filled
        """
        start_time = time.time()
        
        # 1. Parse raw machine data
        machine_data = self._parse_raw_machine(machine_raw)
        budget = QueryBudget(machine_data.name, self.max_queries_per_machine)
        
        logger.info(f"Starting zero-shot enrichment for: {machine_data.name}")
        logger.info(f"Query budget: {budget.max_queries} queries available")
        
        # 2. Initial gap analysis
        gaps = self._initial_gap_analysis(machine_data)
        machine_data.gaps = gaps
        
        # 3. Iterative query-search-analyze loop
        iteration = 0
        while budget.can_query():
            iteration += 1
            logger.info(f"Iteration {iteration}: {budget.remaining()} queries remaining")
            
            # Generate queries
            queries = self._generate_queries(machine_data, budget, gaps)
            if not queries:
                logger.info("No more queries generated, ending search loop")
                break
            
            # Execute searches
            search_results = []
            for query in queries:
                if budget.consume(query):
                    results = self._execute_search(query)
                    search_results.extend(results)
                    time.sleep(SEARCH_DELAY)  # Rate limiting
            
            # Update machine data with results
            self._integrate_search_results(machine_data, search_results)
            
            # Analyze gaps again
            gap_analysis = self._analyze_gaps(machine_data, search_results)
            gaps = gap_analysis.get("gaps", [])
            needs_more = gap_analysis.get("needs_more_queries", False)
            
            machine_data.gaps = gaps
            machine_data.confidence = gap_analysis.get("confidence_level", "medium")
            
            if not needs_more:
                logger.info("Sufficient data collected, ending search loop")
                break
        
        # 4. Fill remaining gaps with educated estimations
        machine_data = self._fill_with_estimations(machine_data)
        
        # 5. Convert pricing to DZD
        self._convert_pricing_to_dzd(machine_data)
        
        # 6. Final assembly
        enriched = machine_data.to_dict()
        enriched["enrichment_metadata"] = {
            "queries_used": budget.queries_used,
            "queries_history": budget.queries_history,
            "processing_time_s": round(time.time() - start_time, 2),
            "method": "zero_shot_intelligent",
            "final_confidence": machine_data.confidence
        }
        
        logger.info(f"Enrichment complete for {machine_data.name} in {enriched['enrichment_metadata']['processing_time_s']}s")
        return enriched
    
    def _parse_raw_machine(self, raw: Dict[str, Any]) -> MachineData:
        """Parse raw machine extraction into structured format."""
        name = raw.get("nom_machine", raw.get("name", "Unknown Machine"))
        description = raw.get("description", raw.get("use", raw.get("utilisation", "")))
        machine_type = raw.get("type", raw.get("categorie", "General Industrial Equipment"))
        
        # Extract any existing specifications
        specs = {}
        if "specifications" in raw:
            specs = raw["specifications"]
        if "puissance" in raw:
            specs["power"] = raw["puissance"]
        if "dimensions" in raw:
            specs["dimensions"] = raw["dimensions"]
        
        return MachineData(
            name=name,
            raw_description=description,
            machine_type=machine_type,
            specifications=specs
        )
    
    def _initial_gap_analysis(self, machine: MachineData) -> List[str]:
        """Identify what information is missing from initial extraction."""
        gaps = []
        
        required_fields = [
            ("manufacturer", "Manufacturer/Brand"),
            ("model", "Model number or series"),
            ("power", "Power rating"),
            ("capacity", "Production capacity"),
            ("dimensions", "Physical dimensions"),
            ("weight", "Equipment weight"),
            ("price", "Pricing information"),
            ("suppliers", "Suppliers/distributors")
        ]
        
        for key, label in required_fields:
            if key not in machine.specifications or not machine.specifications.get(key):
                gaps.append(label)
        
        if not machine.suppliers:
            gaps.append("Suppliers in Algeria/MENA")
        
        return gaps
    
    def _generate_queries(self, machine: MachineData, budget: QueryBudget, gaps: List[str]) -> List[str]:
        """Use LLM to generate intelligent search queries."""
        remaining = budget.remaining()
        if remaining == 0:
            return []
        
        num_queries = 1  # Generate only 1 query for speed
        
        prompt = QUERY_GENERATION_PROMPT.format(
            raw_description=machine.raw_description,
            current_data=json.dumps(machine.specifications, indent=2),
            gaps=", ".join(gaps) if gaps else "None - comprehensive search",
            remaining_queries=remaining,
            num_queries=num_queries
        )
        
        try:
            response = generate_message(
                prompt=prompt,
                system_instruction="You are an expert at generating effective web search queries.",
                temperature=QUERY_GENERATION_TEMPERATURE
            )
            
            # Parse JSON response
            data = self._parse_llm_json(response)
            queries = data.get("queries", [])
            
            logger.info(f"Generated queries: {queries}")
            logger.info(f"Reasoning: {data.get('reasoning', 'N/A')}")
            
            return queries[:num_queries]
            
        except Exception as e:
            logger.error(f"Query generation failed: {e}")
            # Fallback: generate basic query
            return [f"{machine.name} specifications price suppliers"]
    
    def _execute_search(self, query: str) -> List[Dict[str, Any]]:
        """Execute web search and return results."""
        logger.info(f"Executing search: {query}")
        
        try:
            # Use aggregator for comprehensive search
            results = search_general(query, max_results=MAX_SEARCH_RESULTS_PER_QUERY)
            
            parsed_results = []
            for r in results:
                parsed_results.append({
                    "title": r.title,
                    "url": r.url,
                    "snippet": r.snippet,
                    "source": r.source
                })
            
            logger.info(f"Found {len(parsed_results)} results")
            return parsed_results
            
        except Exception as e:
            logger.error(f"Search execution failed: {e}")
            return []
    
    def _integrate_search_results(self, machine: MachineData, results: List[Dict[str, Any]]):
        """Extract relevant information from search results and update machine data."""
        machine.search_results.extend([r["url"] for r in results])
        
        # Use LLM to extract structured data from search results
        if not results:
            return
        
        # Prepare results text
        results_text = "\n\n".join([
            f"Title: {r['title']}\nURL: {r['url']}\nSnippet: {r['snippet']}"
            for r in results[:5]  # Limit to top 5 to avoid token limits
        ])
        
        extraction_prompt = f"""Extract structured information from these search results.

MACHINE: {machine.name}

SEARCH RESULTS:
{results_text}

Extract:
1. Manufacturer brands mentioned
2. Model numbers
3. Technical specifications (power, capacity, dimensions, weight)
4. Price information (any currency)
5. Supplier/distributor names and locations

OUTPUT FORMAT (JSON only):
{{
  "manufacturers": ["brand1", "brand2"],
  "models": ["model1", "model2"],
  "specifications": {{"spec_name": "value"}},
  "pricing": {{"currency": "USD", "amount": 50000, "type": "FOB"}},
  "suppliers": [{{"name": "Company", "location": "Country"}}]
}}
"""
        
        try:
            response = generate_message(
                prompt=extraction_prompt,
                system_instruction="Extract structured data from web search results.",
                temperature=0.1
            )
            
            data = self._parse_llm_json(response)
            
            # Merge extracted data
            if "manufacturers" in data and data["manufacturers"]:
                if "manufacturer" not in machine.specifications:
                    machine.specifications["manufacturer"] = data["manufacturers"][0]
            
            if "specifications" in data:
                machine.specifications.update(data["specifications"])
            
            if "suppliers" in data:
                machine.suppliers.extend(data["suppliers"])
            
            if "pricing" in data and data["pricing"]:
                machine.pricing = data["pricing"]
            
        except Exception as e:
            logger.warning(f"Failed to extract data from search results: {e}")
    
    def _analyze_gaps(self, machine: MachineData, recent_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze what gaps remain after search."""
        results_summary = "\n".join([r.get("title", "") for r in recent_results[:5]])
        
        prompt = GAP_ANALYSIS_PROMPT.format(
            machine_name=machine.name,
            raw_description=machine.raw_description,
            search_results=results_summary,
            current_data=json.dumps({
                "specifications": machine.specifications,
                "suppliers": machine.suppliers,
                "pricing": machine.pricing
            }, indent=2)
        )
        
        try:
            response = generate_message(
                prompt=prompt,
                system_instruction="Analyze data gaps and determine if more searches are needed.",
                temperature=GAP_ANALYSIS_TEMPERATURE
            )
            
            return self._parse_llm_json(response)
            
        except Exception as e:
            logger.error(f"Gap analysis failed: {e}")
            return {
                "gaps": [],
                "critical_gaps": [],
                "confidence_level": "medium",
                "needs_more_queries": False,
                "reasoning": "Analysis failed"
            }
    
    def _fill_with_estimations(self, machine: MachineData) -> MachineData:
        """Fill remaining gaps with educated estimations."""
        if not machine.gaps:
            return machine
        
        logger.info(f"Filling {len(machine.gaps)} remaining gaps with estimations")
        
        prompt = ESTIMATION_PROMPT.format(
            machine_name=machine.name,
            raw_description=machine.raw_description,
            machine_type=machine.machine_type,
            collected_data=json.dumps({
                "specifications": machine.specifications,
                "suppliers": machine.suppliers,
                "pricing": machine.pricing
            }, indent=2),
            gaps=", ".join(machine.gaps)
        )
        
        try:
            response = generate_message(
                prompt=prompt,
                system_instruction="Provide educated estimations for missing industrial equipment data.",
                temperature=ESTIMATION_TEMPERATURE
            )
            
            data = self._parse_llm_json(response)
            
            # Integrate estimations
            if "estimated_fields" in data:
                for field, details in data["estimated_fields"].items():
                    if field not in machine.specifications or not machine.specifications[field]:
                        machine.specifications[field] = details.get("value")
                        machine.specifications[f"{field}_source"] = "estimation"
                        machine.specifications[f"{field}_rationale"] = details.get("rationale")
            
            if "manufacturer_recommendations" in data and not machine.specifications.get("manufacturer"):
                brands = [m["brand"] for m in data["manufacturer_recommendations"]]
                machine.specifications["manufacturer"] = brands[0] if brands else "Generic OEM"
                machine.specifications["manufacturer_alternatives"] = brands[1:3]
            
            if "pricing_estimate" in data and not machine.pricing:
                machine.pricing = data["pricing_estimate"]
                machine.pricing["source"] = "estimation"
            
            logger.info("Estimations integrated successfully")
            
        except Exception as e:
            logger.error(f"Estimation failed: {e}")
        
        return machine
    
    def _convert_pricing_to_dzd(self, machine: MachineData):
        """Convert all pricing to DZD with appropriate tariffs."""
        if not machine.pricing:
            return
        
        logger.info("Converting pricing to DZD")
        
        # Get USD price
        usd_price = None
        currency = machine.pricing.get("currency", "USD")
        
        if currency == "USD":
            usd_price = machine.pricing.get("amount")
        elif currency == "EUR":
            # EUR to USD conversion (approximate)
            eur_amount = machine.pricing.get("amount", 0)
            usd_price = eur_amount * 1.1  # Rough conversion
        elif currency == "CNY":
            # CNY to USD conversion
            cny_amount = machine.pricing.get("amount", 0)
            usd_price = cny_amount * 0.14  # Rough conversion
        
        if isinstance(machine.pricing.get("price_range_usd"), list):
            usd_min, usd_max = machine.pricing["price_range_usd"]
            dzd_min = int(usd_min * USD_TO_DZD_RATE * (1 + IMPORT_TARIFF_RATE))
            dzd_max = int(usd_max * USD_TO_DZD_RATE * (1 + IMPORT_TARIFF_RATE))
            
            machine.pricing["price_range_dzd"] = [dzd_min, dzd_max]
            machine.pricing["includes_tariff"] = True
            machine.pricing["tariff_rate"] = f"{IMPORT_TARIFF_RATE * 100}%"
            
        elif usd_price:
            dzd_price = int(usd_price * USD_TO_DZD_RATE * (1 + IMPORT_TARIFF_RATE))
            machine.pricing["amount_dzd"] = dzd_price
            machine.pricing["includes_tariff"] = True
            machine.pricing["tariff_rate"] = f"{IMPORT_TARIFF_RATE * 100}%"
            machine.pricing["conversion_rate"] = USD_TO_DZD_RATE
        
        logger.info(f"Pricing converted to DZD: {machine.pricing.get('amount_dzd', machine.pricing.get('price_range_dzd'))}")
    
    def _parse_llm_json(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response, handling various formats."""
        # Remove markdown code blocks if present
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        
        response = response.strip()
        
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON: {e}")
            logger.error(f"Response: {response}")
            return {}


# =========================================================
# Convenience Function
# =========================================================

def enrich_machine_zero_shot(machine_raw: Dict[str, Any], max_queries: int = MAX_QUERIES_PER_MACHINE) -> Dict[str, Any]:
    """
    Convenience function to enrich a single machine with zero-shot approach.
    
    Args:
        machine_raw: Raw machine data from extraction
        max_queries: Maximum number of web search queries allowed
        
    Returns:
        Enriched machine data
    """
    enricher = ZeroShotEnricher(max_queries_per_machine=max_queries)
    return enricher.enrich_machine(machine_raw)
