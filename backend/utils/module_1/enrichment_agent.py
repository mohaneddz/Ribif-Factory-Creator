
import json
import concurrent.futures
import time
from typing import Dict, Any, List

from vertex_utils import generate_message
from utils.web_search.agentic import agentic_search
from utils.logger import get_logger

logger = get_logger(__name__)

STAGES_PROMPT = """
You are an expert industrial process engineer.
Your task is to generate a realistic Stage 5 Production Routing for the following product families:
{products}

For EACH product family, define:
1. Inputs (Raw Materials)
2. Major Process Steps (ordered)
3. Key Machines/Equipment used at each step (refer to this list if applicable: {machines})
4. Inline Quality Control (QC) steps
5. Output (Intermediate/Finished)
6. Packaging & Warehousing step

Format your response as a JSON object keyed by product family name.
Example:
{{
  "SPC Flooring": {{
    "steps": [
       {{ "step": 1, "name": "Mixing", "machine": "High-speed Mixer", "inputs": ["PVC", "CaCO3"], "qc": "Moisture check" }},
       ...
    ]
  }}
}}
"""

QUANTITY_ESTIMATION_PROMPT = """
You are an industrial engineer.
Estimate the required quantity for the following machine based on the production context.

Machine: {machine_name}
Context: {context}
Total Project Goal: {project_goal}

Assume efficient industrial operation (e.g. 2 shifts, 60-75% OEE).
Return a JSON object:
{{
   "quantity": <integer>,
   "rationale": "<short explanation>"
}}
"""

MATERIAL_ESTIMATION_PROMPT = """
You are an expert in industrial materials.
Estimate consumption ranges for: {materials}
Given products: {products}

Return JSON with estimates (value, unit, period) for each material.
"""

class RibifEnrichmentAgent:
    def __init__(self):
        self.logger = logger

    def enrich_json(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point to enrich Module 1 JSON.
        """
        # 0. Setup Context
        products = data.get("stage_3_produits_fabriques", {}).get("produits_fabriques", [])
        machines_stage_4 = data.get("stage_4_machines_equipements", {}).get("machines_production", [])
        materials = data.get("stage_2_matieres_premieres", {}).get("matieres_premieres", [])
        info = data.get("stage_1_informations_generales", {}).get("informations_generales", {})
        
        # Localization force
        if "localisation" in info:
            info["localisation"]["pays"] = "Algeria"
            info["localisation"]["ville"] = "Algiers" # as per prompt, default
        
        # Parallel Execution
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            # Task A: Stage 5 Routing
            future_routing = executor.submit(self._generate_routing, products, machines_stage_4)
            
            # Task B: Machine Enrichment
            future_machines = executor.submit(self._enrich_machines, machines_stage_4, products, info)
            
            # Task C: Materials Estimation
            future_materials = executor.submit(self._enrich_materials, materials, products)
            
            # Wait for results
            routing_res = future_routing.result()
            machines_res = future_machines.result()
            materials_res = future_materials.result()

        # Update Data
        if "stage_5_processus_production" not in data:
            data["stage_5_processus_production"] = {}
        data["stage_5_processus_production"]["processus_production"] = routing_res
        
        data["stage_4_machines_equipements"]["machines_production"] = machines_res
        data["stage_2_matieres_premieres"]["matieres_premieres"] = materials_res
        
        return data

    def _generate_routing(self, products: List[Dict], machines: List[Dict]) -> List[Dict]:
        """Task A: Generate production routing."""
        product_names = [p.get("nom_produit") for p in products]
        machine_names = [m.get("nom_machine") for m in machines]
        
        prompt = STAGES_PROMPT.format(products=", ".join(product_names), machines=", ".join(machine_names))
        response = generate_message(prompt, temperature=0.5, system_instruction="Output valid JSON only.")
        
        try:
            # cleanup json markdown
            clean = response.strip()
            if clean.startswith("```json"): clean = clean[7:]
            if clean.endswith("```"): clean = clean[:-3]
            routing_dict = json.loads(clean)
            
            # Convert to list format expected by schema if necessary, or keep as dict? 
            # Existing schema has "processus_production": [] which usually implies a list of steps.
            # But here we have per-product routings. Adaptation: return list of objects with "product" key.
            final_routing = []
            for prod, steps in routing_dict.items():
                final_routing.append({
                    "produit": prod,
                    "etapes": steps.get("steps", [])
                })
            return final_routing
        except Exception as e:
            self.logger.error(f"Routing generation failed: {e}")
            return []

    def _enrich_machines(self, machines: List[Dict], products: List[Dict], info: Dict) -> List[Dict]:
        """Task B: Machine enrichment + quantities."""
        enriched_machines = []
        
        def process_single_machine(machine):
            name = machine.get("nom_machine")
            m_type = machine.get("type", "")
            
            # 1. Quantity Estimation (LLM)
            # We do this logic first or parallel? Let's do it simply here.
            qty_prompt = QUANTITY_ESTIMATION_PROMPT.format(
                machine_name=name,
                context=json.dumps(products[:3]), # summary of products
                project_goal=info.get("objectifs_strategiques", "")
            )
            qty_data = {}
            try:
                qty_raw = generate_message(qty_prompt, temperature=0.3)
                qty_clean = qty_raw.strip().replace("```json", "").replace("```", "")
                qty_data = json.loads(qty_clean)
            except:
                pass
            
            # Safely extract quantity - handle cases where LLM returns nested objects
            raw_qty = qty_data.get("quantity", machine.get("quantite_necessaire") or 1)
            if isinstance(raw_qty, dict):
                # Handle nested structures like {"value": 1, "unit": "pieces"}
                raw_qty = raw_qty.get("value", raw_qty.get("quantity", 1))
            try:
                machine["quantite_necessaire"] = int(raw_qty) if raw_qty else 1
            except (TypeError, ValueError):
                machine["quantite_necessaire"] = 1
            machine["rationale_quantite"] = qty_data.get("rationale", "Estimated based on project scale")
            
            # 2. Specs Enrichment (Agentic Search)
            # Uses agentic.py to search for specs
            specs_res = agentic_search.search_specs_agentic(name, machine.get("fabricant_recommande", ""))
            
            # Update machine with found specs
            if specs_res.specifications:
                current_specs = machine.get("specifications", {})
                current_specs.update(specs_res.specifications)
                machine["specifications"] = current_specs
                
            # Add web enrichment metadata
            machine["_web_enrichment"] = {
                "datasheets": specs_res.datasheet_urls,
                "images": specs_res.image_urls,
                "sources": specs_res.sources,
                "search_queries": [] # Agentic search doesn't return queries in result obj yet, implementation detail
            }
            
            # 3. Model Selection (Simulated by 'selected_models' requirement)
            # We extract model names from specs if present, otherwise ask LLM to pick from 'knowledge'
            # For now, we'll placeholder or extract if 'model' key in specs
            models = []
            if specs_res.model: models.append(specs_res.model)
            machine["selected_models"] = models
            
            return machine

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(process_single_machine, m) for m in machines]
            for future in concurrent.futures.as_completed(futures):
                try:
                    enriched_machines.append(future.result())
                except Exception as e:
                    self.logger.error(f"Machine enrichment failed: {e}")
                    
        return enriched_machines

    def _enrich_materials(self, materials: List[Dict], products: List[Dict]) -> List[Dict]:
        """Task C: Materials Estimation."""
        mat_names = [m.get("nom_materiau") for m in materials]
        prod_names = [p.get("nom_produit") for p in products]
        
        prompt = MATERIAL_ESTIMATION_PROMPT.format(materials=", ".join(mat_names), products=", ".join(prod_names))
        try:
            res = generate_message(prompt, temperature=0.3)
            clean = res.strip().replace("```json", "").replace("```", "")
            estimates = json.loads(clean)
            
            # Map back
            # Assuming estimates is a dict keyed by material name
            for mat in materials:
                name = mat.get("nom_materiau")
                if name in estimates:
                     mat["quantite_estimee"] = estimates[name]
                     mat["value_source"] = "estimate"
            return materials
        except:
             return materials

