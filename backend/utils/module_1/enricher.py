
import json
import time
import concurrent.futures
from typing import Any, Dict, List, Optional
from utils.logger import get_logger
from vertex_utils import generate_message
from utils.web_search.agentic import agentic_search
from config import WEB_SEARCH_ENABLED

logger = get_logger(__name__)

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
            # Cleanup
            cleaned = raw.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            return json.loads(cleaned)
        except Exception as e:
            logger.error(f"Enricher LLM call '{tag}' failed: {e}")
            return {}

    def enrich_machine(self, machine: Dict[str, Any]) -> Dict[str, Any]:
        """Deep enrichment for a single machine using agentic web search."""
        name = machine.get("nom_machine")
        manufacturer = machine.get("fabricant_recommande", "")
        
        if not name or name == "N/A":
            return machine

        logger.info(f"Enriching machine: {name}")
        
        # 1. Generate queries (handled inside agentic_search mainly, but we can give it a hint)
        # The agentic_search already does multiple loops.
        
        try:
            # 2. Agentic search for specs
            specs_res = agentic_search.search_specs_agentic(name, manufacturer)
            
            # 3. Store results
            machine["selected_models"] = [
                {"brand": specs_res.manufacturer or manufacturer, "model": specs_res.model or "Best-fit model", "type": "primary"},
                {"brand": "Alternative OEM", "model": "Equivalent Model", "type": "alternative"}
            ]
            
            # Enrich specifications
            curr_specs = machine.get("specifications", {})
            if isinstance(curr_specs, dict) and specs_res.specifications:
                for k, v in specs_res.specifications.items():
                    if not curr_specs.get(k) or curr_specs[k] == "N/A":
                        curr_specs[k] = v
                machine["specifications"] = curr_specs

            # 4. Quantity estimation
            # If quantity is 0 or missing, estimate it
            qty = machine.get("quantite_necessaire", 0)
            if qty == 0:
                # Engineering estimate based on name
                qty_map = {
                    "spc": 2, "extrusion": 2, "injection": 10, "thermoformage": 2, 
                    "membrane": 1, "trempe": 1, "lamination": 1, "agv": 15, "asrs": 1
                }
                found_qty = 1
                for k, v in qty_map.items():
                    if k in name.lower():
                        found_qty = v
                        break
                machine["quantite_necessaire"] = found_qty
                machine["quantite_rationale"] = f"Estimated based on typical industrial capacity for a project of this scale."

            # 5. Metadata
            machine["_web_enrichment"] = {
                "datasheets": specs_res.datasheet_urls,
                "images": specs_res.image_urls,
                "sources": specs_res.sources,
                "agentic_notes": "Deep enriched via RIBIF Enriched Module"
            }
            machine["value_source"] = "web"
            machine["confidence"] = "high" if specs_res.sources else "low"
            machine["rationale"] = f"Technical specifications found via web search for {name}."

        except Exception as e:
            logger.warning(f"Failed to enrich machine {name}: {e}")
            machine["value_source"] = "estimate"
            machine["confidence"] = "low"
            machine["rationale"] = "Web search failed, using default factory template."

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

        # Parallel Execution of Tasks A, B, C
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # A: Stage 5 Routing
            future_routing = executor.submit(self._call_llm_json, ROUTING_PROMPT.format(raw_json=json.dumps(raw_json)), "routing")
            
            # C: Quantities (Stage 2 & 3)
            future_quantities = executor.submit(self._call_llm_json, QUANTITIES_PROMPT.format(raw_json=json.dumps(raw_json)), "quantities")
            
            # B: Machine Enrichment (Stage 4)
            machines = raw_json.get("stage_4_machines_equipements", {}).get("machines_production", [])
            future_machines = [executor.submit(self.enrich_machine, m) for m in machines]

            # Wait and Merge
            routing_data = future_routing.result()
            quantities_data = future_quantities.result()
            
            enriched_machines = []
            for f in future_machines:
                enriched_machines.append(f.result())

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
