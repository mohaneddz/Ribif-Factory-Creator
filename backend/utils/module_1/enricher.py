
import json
import time
import concurrent.futures
from typing import Any, Dict, List, Optional
from utils.logger import get_logger
from vertex_utils import generate_message
from utils.web_search.agentic import agentic_search
from utils.web_search.sourcing_agent import sourcing_agent
from utils.module_1.helpers import safe_json_loader, normalize_headers
from config import WEB_SEARCH_ENABLED

logger = get_logger(__name__)

# Shared worker pool for Module 1 enrichment
SHARED_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=7)
MACHINE_ENRICHMENT_TIMEOUT_S = 90
MAX_SUPPLIERS_PER_MACHINE = 12

# =========================================================
# 0) Prompts for Enrichment
# =========================================================

SYSTEM_INSTRUCTION = """
You are a senior industrial engineer and business analyst specializing in Industry 5.0 and factory automation.
Your task is to ENRICH and COMPLETE a raw extraction of an industrial project.
- Use engineering best-guesses for missing values.
- Ensure technical consistency across all stages (materials vs machines vs products).
- Normalize values and units (kW, m, metrics, etc.).
- Provide rationale and confidence levels for all estimated fields.
- Respond in the same language as the input (likely French or English).
"""

STRICT_JSON_HEADER = "OUTPUT RULES: Return ONLY a valid JSON object. No markdown. No commentary.\n"

ROUTING_PROMPT = """
GOAL: Create a production routing for each product family.
INPUT JSON: {raw_json}

REQUIREMENTS for Stage 5 (processus_production):
For each product family, define:
- Inputs (raw materials)
- Ordered Steps (ordered)
- Key machines used
- Inline QC steps
- Outputs (semi-finished / finished)
- Packaging & warehousing (ASRS / AGV integration)

CREATE ROUTINGS FOR AT MINIMUM:
1. SPC flooring
2. Injection molded parts
3. Extrusion (films/profiles)
4. Thermoformed parts
5. 3D membrane press / thermofoil panels
6. Resin-based coatings (PU/polyurea/epoxy)
7. Safety glass (laminated/tempered) + UTG

OUTPUT FORMAT for Stage 5:
{{
  "processus_production": [
    {{
      "produit": "string",
      "etapes": [
        {{ 
          "step": 1, 
          "name": "string", 
          "machine": "string", 
          "inputs": ["string"], 
          "qc": "string", 
          "outputs": ["string"],
          "parametres_process": {{
            "temperature": "string (e.g. 180°C or N/A)",
            "pression": "string (e.g. 5 bar or N/A)",
            "temps_cycle": "string (e.g. 45s or N/A)"
          }}
        }}
      ]
    }}
  ],
  "kpi_production": {{ "oee_cible": "85%", "trs_cible": "80%", "taux_rebut_acceptable": "2%", "temps_changement_serie": "45 min" }}
}}
"""

QUANTITIES_PROMPT = """
GOAL: Estimate consumption and production volumes based on industrial baselines.
INPUT JSON: {raw_json}

REQUIREMENTS:
1. For each Raw Material in Stage 2, estimate `quantite_estimee` (valeur, unite, periode).
2. For each Product in Stage 3, estimate `volume_production` (capacite, unite, periode).
3. Base estimates on typical factory capacities (e.g., SPC line 30-60 t/day, Injection mold cycles 20-60s).
4. Assume 2 shifts/day, 300 days/year unless stated otherwise.

OUTPUT FORMAT (Fragment):
{{
  "stage_2_matieres_premieres": {{ "matieres_premieres": [...] }},
  "stage_3_produits_fabriques": {{ "produits_fabriques": [...] }}
}}
"""

NORMALIZATION_PROMPT = """
GOAL: Final pass for normalization and consistency.
INPUT JSON: {full_json}

REQUIREMENTS:
1. Normalize field names (consistent usage of French/English as per project context).
2. Ensure units are consistent (kW, m, mm, kg, tons).
3. Reconcile machine counts in Stage 4 with the routing in Stage 5.
4. Fill any remaining "N/A" with educated estimates.
5. Add `value_source`, `confidence`, and `rationale` to every guessed/estimated field.

OUTPUT: Return the FULL COMPLETED JSON.
"""

# =========================================================
# 1) Enricher Class
# =========================================================

class RIBIFEnricher:
    def __init__(self):
        pass

    def _call_llm_json(self, prompt: str, tag: str) -> Dict[str, Any]:
        try:
            raw = generate_message(
                prompt=STRICT_JSON_HEADER + prompt,
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.2
            )
            data = safe_json_loader(raw)
            if not data and tag == "normalization":
                # Retry once for normalization if it failed
                logger.warning(f"Normalization failed, retrying once...")
                raw_retry = generate_message(
                    prompt="Your previous output was malformed. Return ONLY valid JSON.\n" + STRICT_JSON_HEADER + prompt,
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.1
                )
                data = safe_json_loader(raw_retry)
            return data
        except Exception as e:
            logger.error(f"Enricher LLM call '{tag}' failed: {e}")
            return {}

    def enrich_machine(self, machine: Dict[str, Any]) -> Dict[str, Any]:
        """Deep enrichment for a single machine using agentic web search."""
        # This is now a wrapper around the global enrichment strategy
        return self.enrich_one_machine_global(machine)

    def enrich_one_machine_global(self, machine: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redesigned Module 1 machine enrichment:
        - Single global search pass.
        - Discover OEMs, Distributors, Integrators, and Service Providers in one go.
        - Hard limits on suppliers and time.
        - Resilient JSON normalization.
        """
        name = machine.get("nom_machine")
        manufacturer = machine.get("fabricant_recommande", "")
        
        if not name or name == "N/A":
            return machine

        logger.info(f"Global enrichment starting for: {name}")
        t_start = time.time()
        
        try:
            # 1. Specs Discovery
            # We still use the agentic search for specs as it's targeted
            specs_res = agentic_search.search_specs_agentic(name, manufacturer)
            
            # 2. Global Sourcing Pass (Non-phased)
            global_query = f"{name} {manufacturer} suppliers distributors Algeria MENA Europe USA"
            logger.info(f"Single global sourcing pass for: {name}")
            
            # We bypass the sourcing_agent's phased logic for speed
            from utils.web_search import aggregator
            search_results = aggregator.search_machine_suppliers(global_query, max_total_results=MAX_SUPPLIERS_PER_MACHINE)
            
            suppliers = []
            for s in search_results:
                suppliers.append({
                    "supplier_name": s.supplier_name,
                    "role": s.price_type if "Distributor" not in s.price_type else "Distributor", # Heuristic if role not explicit
                    "region": s.region,
                    "website": s.website,
                    "source_urls": [s.source_url] if s.source_url else [],
                    "confidence": "high" if s.relevance_score > 0.6 else "medium",
                    "notes": s.customs_algeria_info
                })
            
            # Use LLM to normalize/categorize suppliers if we have time/budget, 
            # but for speed, we stick to the aggregated list.
            
            # 3. Update Machine Data
            machine["selected_models"] = [
                {"brand": specs_res.manufacturer or manufacturer, "model": specs_res.model or "Best-fit model", "type": "primary"},
                {"brand": "Alternative OEM", "model": "Equivalent Model", "type": "alternative"}
            ]
            machine["suppliers"] = suppliers[:MAX_SUPPLIERS_PER_MACHINE]
            machine["algeria_distributor_found"] = any(s.get("region") == "Algeria" for s in suppliers)
            
            # Specs enrichment
            curr_specs = machine.get("specifications", {})
            if isinstance(curr_specs, dict) and specs_res.specifications:
                for k, v in specs_res.specifications.items():
                    if not curr_specs.get(k) or curr_specs[k] == "N/A":
                        curr_specs[k] = v
                machine["specifications"] = curr_specs

            # Quantity estimation (engineering heuristic)
            qty = machine.get("quantite_necessaire", 0)
            if qty == 0:
                machine["quantite_necessaire"] = 1
                machine["quantite_rationale"] = "Defaulted to 1 unit as baseline."

            # Metadata
            machine["_web_enrichment"] = {
                "datasheets": specs_res.datasheet_urls,
                "images": specs_res.image_urls,
                "sources": specs_res.sources,
                "agentic_notes": "Enriched via non-phased global sourcing."
            }
            machine["value_source"] = "web"
            machine["confidence"] = "high" if specs_res.sources else "low"
            machine["rationale"] = f"Technical data and suppliers aggregated via global search for {name}."

        except Exception as e:
            logger.warning(f"Failed to enrich machine {name}: {e}")
            machine["enrichment_error"] = str(e)
            machine["value_source"] = "estimate"
            machine["confidence"] = "low"
            machine["rationale"] = f"Enrichment timeout or failure ({str(e)}). Using basic template."

        logger.info(f"Machine {name} enriched in {round(time.time() - t_start, 2)}s")
        return machine

    def process(self, raw_json: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point for enrichment."""
        logger.info("Starting Comprehensive Module 1 Enrichment...")
        t0 = time.time()

        # Task D: Localization
        info = raw_json.get("stage_1_informations_generales", {}).get("informations_generales", {})
        loc = info.get("localisation", {})
        loc["pays"] = "Algeria"
        loc["ville"] = "Algiers"
        if not loc.get("zone") or loc["zone"] == "N/A":
            loc["zone"] = "Zone industrielle (Rouiba/Reghaia)"
        info["localisation"] = loc
        raw_json["stage_1_informations_generales"]["informations_generales"] = info

        # Parallel Execution of Tasks A, B, C using SHARED_EXECUTOR
        # A: Stage 5 Routing
        future_routing = SHARED_EXECUTOR.submit(self._call_llm_json, ROUTING_PROMPT.format(raw_json=json.dumps(raw_json)), "routing")
        
        # C: Quantities (Stage 2 & 3)
        future_quantities = SHARED_EXECUTOR.submit(self._call_llm_json, QUANTITIES_PROMPT.format(raw_json=json.dumps(raw_json)), "quantities")
        
        # B: Machine Enrichment (Stage 4)
        machines = raw_json.get("stage_4_machines_equipements", {}).get("machines_production", [])
        future_machines = [SHARED_EXECUTOR.submit(self.enrich_one_machine_global, m) for m in machines]

        # Wait and Merge
        try:
            routing_data = future_routing.result(timeout=120)
            quantities_data = future_quantities.result(timeout=120)
        except Exception as e:
            logger.error(f"Enrichment task timed out or failed: {e}")
            routing_data = {}
            quantities_data = {}
        
        enriched_machines = []
        for i, f in enumerate(future_machines):
            original_machine = machines[i]
            try:
                result = f.result(timeout=MACHINE_ENRICHMENT_TIMEOUT_S)
                enriched_machines.append(result)
            except Exception as e:
                logger.warning(f"Machine enrichment failed or timed out for {original_machine.get('nom_machine')}: {e}")
                # Fallback: use original machine and mark error
                original_machine["enrichment_error"] = str(e)
                enriched_machines.append(original_machine)

        # Merge Results
        raw_json["stage_5_processus_production"] = routing_data
        
        if "stage_2_matieres_premieres" in quantities_data:
            raw_json["stage_2_matieres_premieres"] = quantities_data["stage_2_matieres_premieres"]
        
        if "stage_3_produits_fabriques" in quantities_data:
            raw_json["stage_3_produits_fabriques"] = quantities_data["stage_3_produits_fabriques"]

        raw_json["stage_4_machines_equipements"]["machines_production"] = enriched_machines

        # Task E: Final Pass Normalization
        final_json = self._call_llm_json(NORMALIZATION_PROMPT.format(full_json=json.dumps(raw_json)), "normalization")
        
        # Fallback if normalization failed
        if not final_json:
            final_json = raw_json

        # Add enrichment summary
        final_json["enrichment_summary"] = {
            "assumptions": {
                "shifts": 2,
                "oee": 0.75,
                "region": "Algeria (MENA distribution)",
                "industrial_standard": "Industry 5.0"
            },
            "top_uncertainties": [
                "UTG (Ultra Thin Glass) specific equipment service availability in Algeria",
                "Specific local supplier lead times"
            ],
            "recommended_next_updates": [
                "Request specific electrical layout from client",
                "Verify import permits for Polyurethane/Isocyanates"
            ],
            "processing_time": round(time.time() - t0, 3)
        }

        logger.info(f"Enrichment complete in {final_json['enrichment_summary']['processing_time']}s")
        return final_json

enricher = RIBIFEnricher()
