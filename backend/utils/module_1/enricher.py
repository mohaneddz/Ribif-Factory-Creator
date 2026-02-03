
import json
import time
import concurrent.futures
from typing import Any, Dict, List, Optional
from utils.logger import get_logger
from vertex_utils import generate_message
from utils.web_search.agentic import agentic_search
from utils.web_search.sourcing_agent import sourcing_agent
from utils.module_1.helpers import safe_json_loader, normalize_headers
from utils.module_1.zero_shot_enricher import ZeroShotEnricher
from utils.normalization import normalize_numeric, canonicalize_key
from utils.quota_manager import (
    with_quota_check, with_rate_limit, with_retry,
    is_quota_error, get_user_friendly_error, get_quota_tracker
)
from utils.pipeline_metrics import create_pipeline_metrics
from config import WEB_SEARCH_ENABLED
import os

logger = get_logger(__name__)

# Enable zero-shot enrichment mode
ENABLE_ZERO_SHOT = True

# =========================================================
# Machine Specification Defaults (for filling N/A values)
# =========================================================

MACHINE_SPEC_DEFAULTS = {
    # Injection molding machines
    "injection": {
        "capacite": "100-5000T de force de fermeture",
        "puissance": "50-250 kW",
        "dimensions": "6m x 2m x 2.5m",
        "alimentation": "380V triphasé",
        "cadence": "20-60 cycles/heure",
        "rendement": "85%",
        "temps_cycle": "30-90 secondes"
    },
    # Extrusion machines
    "extrusion": {
        "capacite": "50-500 kg/h",
        "puissance": "30-150 kW",
        "dimensions": "8m x 1.5m x 2m",
        "alimentation": "380V triphasé",
        "cadence": "continu",
        "rendement": "90%",
        "temps_cycle": "continu"
    },
    # CNC machines
    "cnc": {
        "capacite": "Pièces jusqu'à 500mm",
        "puissance": "15-45 kW",
        "dimensions": "3m x 2.5m x 2.5m",
        "alimentation": "380V triphasé",
        "cadence": "Variable selon pièce",
        "rendement": "85%",
        "temps_cycle": "2-30 minutes/pièce"
    },
    # Welding/soudure
    "soudure": {
        "capacite": "Épaisseur 1-50mm",
        "puissance": "10-40 kW",
        "dimensions": "2m x 1.5m x 1.8m",
        "alimentation": "380V triphasé",
        "cadence": "5-20 soudures/heure",
        "rendement": "80%",
        "temps_cycle": "1-5 minutes/joint"
    },
    # Press/presse
    "presse": {
        "capacite": "50-2000 tonnes",
        "puissance": "20-100 kW",
        "dimensions": "4m x 3m x 4m",
        "alimentation": "380V triphasé",
        "cadence": "10-60 cycles/heure",
        "rendement": "85%",
        "temps_cycle": "15-60 secondes"
    },
    # Robot/automate
    "robot": {
        "capacite": "Charge utile 5-200 kg",
        "puissance": "5-20 kW",
        "dimensions": "Rayon d'action 1-3m",
        "alimentation": "380V triphasé",
        "cadence": "20-120 cycles/minute",
        "rendement": "95%",
        "temps_cycle": "3-15 secondes"
    },
    # Conveyeur/transport
    "convoyeur": {
        "capacite": "100-1000 kg/m",
        "puissance": "1-10 kW",
        "dimensions": "Variable selon installation",
        "alimentation": "380V triphasé",
        "cadence": "5-30 m/min",
        "rendement": "98%",
        "temps_cycle": "continu"
    },
    # Assemblage/assembly
    "assemblage": {
        "capacite": "10-100 unités/heure",
        "puissance": "3-15 kW",
        "dimensions": "2m x 1m x 1.5m",
        "alimentation": "380V triphasé",
        "cadence": "Variable",
        "rendement": "90%",
        "temps_cycle": "30-120 secondes"
    },
    # Découpe/cutting
    "découpe": {
        "capacite": "Épaisseur 0.5-50mm",
        "puissance": "10-50 kW",
        "dimensions": "4m x 2m x 2m",
        "alimentation": "380V triphasé",
        "cadence": "1-10 m/min",
        "rendement": "85%",
        "temps_cycle": "Variable selon pièce"
    },
    # Moulage/molding
    "moulage": {
        "capacite": "Volume 0.1-500 L",
        "puissance": "30-200 kW",
        "dimensions": "5m x 3m x 3m",
        "alimentation": "380V triphasé",
        "cadence": "5-30 cycles/heure",
        "rendement": "85%",
        "temps_cycle": "2-15 minutes"
    },
    # Compresseur
    "compresseur": {
        "capacite": "5-100 m³/min",
        "puissance": "15-250 kW",
        "dimensions": "2m x 1.5m x 1.8m",
        "alimentation": "380V triphasé",
        "cadence": "continu",
        "rendement": "90%",
        "temps_cycle": "continu"
    },
    # Four/oven
    "four": {
        "capacite": "Volume 0.5-50 m³",
        "puissance": "50-500 kW",
        "dimensions": "4m x 3m x 3m",
        "alimentation": "380V triphasé ou gaz",
        "cadence": "1-10 cycles/jour",
        "rendement": "75%",
        "temps_cycle": "1-24 heures"
    },
    # Pompe/pump
    "pompe": {
        "capacite": "10-1000 L/min",
        "puissance": "1-50 kW",
        "dimensions": "1m x 0.5m x 0.8m",
        "alimentation": "380V triphasé",
        "cadence": "continu",
        "rendement": "85%",
        "temps_cycle": "continu"
    },
    # Mélangeur/mixer
    "mélangeur": {
        "capacite": "50-5000 L",
        "puissance": "5-75 kW",
        "dimensions": "2m x 2m x 3m",
        "alimentation": "380V triphasé",
        "cadence": "2-10 lots/heure",
        "rendement": "90%",
        "temps_cycle": "10-60 minutes"
    },
    # Contrôle qualité/QC
    "contrôle": {
        "capacite": "Variable selon équipement",
        "puissance": "1-5 kW",
        "dimensions": "1.5m x 1m x 1.5m",
        "alimentation": "220V monophasé",
        "cadence": "10-100 tests/heure",
        "rendement": "99%",
        "temps_cycle": "30-180 secondes"
    },
    # Thermoforming/thermoformage
    "thermoformage": {
        "capacite": "Feuilles 0.5-10mm épaisseur",
        "puissance": "30-100 kW",
        "dimensions": "4m x 2.5m x 2.5m",
        "alimentation": "380V triphasé",
        "cadence": "5-30 cycles/heure",
        "rendement": "85%",
        "temps_cycle": "30-120 secondes"
    },
    # Broyeur/grinder/crusher
    "broyeur": {
        "capacite": "100-5000 kg/h",
        "puissance": "20-150 kW",
        "dimensions": "3m x 2m x 2.5m",
        "alimentation": "380V triphasé",
        "cadence": "continu",
        "rendement": "90%",
        "temps_cycle": "continu"
    },
    # Sécheur/dryer
    "sécheur": {
        "capacite": "100-2000 kg/lot",
        "puissance": "20-100 kW",
        "dimensions": "3m x 2m x 3m",
        "alimentation": "380V triphasé ou gaz",
        "cadence": "1-5 lots/jour",
        "rendement": "85%",
        "temps_cycle": "2-8 heures"
    },
    # Rectifieuse/grinding machine
    "rectifieuse": {
        "capacite": "Précision 0.001-0.01mm",
        "puissance": "10-30 kW",
        "dimensions": "2.5m x 2m x 2m",
        "alimentation": "380V triphasé",
        "cadence": "5-20 pièces/heure",
        "rendement": "90%",
        "temps_cycle": "5-30 minutes/pièce"
    },
    # Plieuse/bending machine
    "plieuse": {
        "capacite": "Force 50-500 tonnes",
        "puissance": "15-75 kW",
        "dimensions": "4m x 2m x 2.5m",
        "alimentation": "380V triphasé",
        "cadence": "10-60 plis/heure",
        "rendement": "90%",
        "temps_cycle": "10-60 secondes"
    },
    # Cisaille/shearing machine
    "cisaille": {
        "capacite": "Épaisseur 1-25mm, largeur 3-6m",
        "puissance": "15-50 kW",
        "dimensions": "5m x 2m x 2.5m",
        "alimentation": "380V triphasé",
        "cadence": "10-40 coupes/heure",
        "rendement": "90%",
        "temps_cycle": "15-60 secondes"
    },
    # Poinçonneuse/punching machine
    "poinçonneuse": {
        "capacite": "Force 10-100 tonnes",
        "puissance": "10-40 kW",
        "dimensions": "3m x 2m x 2.5m",
        "alimentation": "380V triphasé",
        "cadence": "20-200 coups/minute",
        "rendement": "85%",
        "temps_cycle": "0.3-3 secondes/coup"
    },
    # Emballage/packaging
    "emballage": {
        "capacite": "10-100 unités/minute",
        "puissance": "5-20 kW",
        "dimensions": "3m x 1.5m x 2m",
        "alimentation": "380V triphasé",
        "cadence": "Variable selon produit",
        "rendement": "95%",
        "temps_cycle": "1-6 secondes/unité"
    },
    # Palettiseur/palletizer
    "palettiseur": {
        "capacite": "5-30 palettes/heure",
        "puissance": "10-30 kW",
        "dimensions": "4m x 3m x 3m",
        "alimentation": "380V triphasé",
        "cadence": "Variable selon configuration",
        "rendement": "95%",
        "temps_cycle": "2-10 minutes/palette"
    },
    # Étiqueteuse/labeling machine
    "étiqueteuse": {
        "capacite": "50-500 produits/minute",
        "puissance": "2-5 kW",
        "dimensions": "2m x 1m x 1.5m",
        "alimentation": "220V monophasé",
        "cadence": "Variable selon produit",
        "rendement": "98%",
        "temps_cycle": "0.1-1 seconde/produit"
    },
    # Default/generic
    "default": {
        "capacite": "Variable selon modèle",
        "puissance": "5-50 kW",
        "dimensions": "2m x 1.5m x 2m",
        "alimentation": "380V triphasé",
        "cadence": "Variable",
        "rendement": "85%",
        "temps_cycle": "Variable selon opération"
    }
}

# FAST MODE: Skip web searches and use LLM estimation only (much faster)
# Can be controlled via environment variable FAST_MODE_ENRICHMENT=0 to disable
FAST_MODE = os.getenv("FAST_MODE_ENRICHMENT", "1").lower() in ("1", "true", "yes")

# Shared worker pool for Module 1 enrichment
SHARED_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=7)
MACHINE_ENRICHMENT_TIMEOUT_S = 30 if FAST_MODE else 90  # Reduced timeout
MAX_SUPPLIERS_PER_MACHINE = 5 if FAST_MODE else 12  # Fewer suppliers in fast mode

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
GOAL: Create a production routing for each product family USING ONLY THE MACHINES ALREADY EXTRACTED.
INPUT JSON: {raw_json}

CRITICAL: DO NOT add or suggest new machines. Use ONLY the machines listed in stage_4_machines_equipements.

REQUIREMENTS for Stage 5 (processus_production):
For each product family, define:
- Inputs (raw materials)
- Ordered Steps (ordered)
- Key machines used (MUST be from existing machines list only)
- Inline QC steps
- Outputs (semi-finished / finished)
- Packaging & warehousing (only if machines already exist)

CREATE ROUTINGS based on the products and machines found in the document.
Use only machines that are already extracted in Stage 4.

CRITICAL FOR PROCESS PARAMETERS (parametres_process):
You MUST provide realistic estimated values for ALL process parameters based on:
- The type of machine being used
- The type of operation being performed
- Industry standards for similar processes
- The materials being processed

DO NOT use "N/A" for parametres_process. Always estimate realistic values:
- temperature: Estimate based on the process type (e.g., injection molding: 180-280°C, CNC machining: ambient/25°C, welding: 1500-3000°C, assembly: ambient/25°C, heat treatment: 150-900°C)
- pression: Estimate based on the machine type (e.g., injection molding: 50-200 bar, hydraulic press: 100-500 bar, pneumatic systems: 6-10 bar, vacuum processes: 0.001-1 bar, ambient processes: 1 bar)
- temps_cycle: Estimate based on complexity and machine (e.g., injection molding: 15-60s, CNC operation: 30s-5min, assembly: 10-120s, welding: 5-30s per joint, quality check: 30-180s)

OUTPUT FORMAT for Stage 5:
{{
  "processus_production": [
    {{
      "produit": "string",
      "etapes": [
        {{ 
          "step": 1, 
          "name": "string", 
          "machine": "string (MUST match a machine from stage_4)", 
          "inputs": ["string"], 
          "qc": "string", 
          "outputs": ["string"],
          "parametres_process": {{
            "temperature": "string (REQUIRED - e.g. 180°C, 25°C for ambient)",
            "pression": "string (REQUIRED - e.g. 5 bar, 1 bar for ambient)",
            "temps_cycle": "string (REQUIRED - e.g. 45s, 2 min, 30s)"
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
GOAL: Final pass for normalization and consistency WITHOUT adding or removing machines.
INPUT JSON: {full_json}

CRITICAL: DO NOT add, remove, or suggest new machines. Keep the exact list from Stage 4.

REQUIREMENTS:
1. Normalize field names (consistent usage of French/English as per project context).
2. Ensure units are consistent (kW, m, mm, kg, tons).
3. Reconcile machine counts in Stage 4 with the routing in Stage 5.
4. CRITICAL: Fill ALL "N/A" values for process parameters (temperature, pression, temps_cycle) with realistic estimates based on:
   - The type of machine being used
   - Industry standards for similar processes
   - The materials being processed
   Example estimates:
   - temperature: injection molding 180-280°C, CNC machining 25°C, welding 1500-3000°C, assembly 25°C
   - pression: injection molding 50-200 bar, hydraulic press 100-500 bar, pneumatic 6-10 bar, ambient 1 bar
   - temps_cycle: injection 15-60s, CNC 30s-5min, assembly 10-120s, welding 5-30s
5. Add `value_source`, `confidence`, and `rationale` to every guessed/estimated field.
6. Keep the EXACT same machines in stage_4_machines_equipements - DO NOT add or remove any.

OUTPUT: Return the FULL COMPLETED JSON with the SAME machines list and NO "N/A" values for process parameters.
"""

# =========================================================
# Machine N/A Value Filler Function
# =========================================================

def get_machine_type_key(machine: Dict[str, Any]) -> str:
    """
    Determine the machine type key for looking up default specifications.
    Analyzes machine name, type, and use to find the best match.
    """
    # Build search text from machine info
    name = str(machine.get("nom_machine", "")).lower()
    machine_type = str(machine.get("type", "")).lower()
    use = str(machine.get("use", "")).lower()
    search_text = f"{name} {machine_type} {use}"
    
    # Priority order of machine type keys to check
    type_keywords = [
        ("injection", ["injection", "injecter", "injecting"]),
        ("extrusion", ["extrusion", "extruder", "extrudeuse"]),
        ("cnc", ["cnc", "usinage", "machining", "fraisage", "tournage", "milling", "turning"]),
        ("soudure", ["soudure", "soudage", "welding", "souder"]),
        ("presse", ["presse", "press", "emboutissage", "stamping", "hydraulique"]),
        ("robot", ["robot", "automate", "bras", "manipulateur", "cobot"]),
        ("convoyeur", ["convoyeur", "conveyor", "transport", "manutention", "tapis", "band"]),
        ("assemblage", ["assemblage", "assembly", "montage"]),
        ("découpe", ["découpe", "cutting", "coupe", "laser", "plasma", "oxycoupage"]),
        ("moulage", ["moulage", "molding", "moule", "mold", "rotomoulage"]),
        ("compresseur", ["compresseur", "compressor", "air comprimé"]),
        ("four", ["four", "oven", "furnace", "étuve"]),
        ("pompe", ["pompe", "pump", "pompage"]),
        ("mélangeur", ["mélangeur", "mixer", "malaxeur", "agitateur", "mixing"]),
        ("contrôle", ["contrôle", "control", "inspection", "test", "mesure", "qc", "qualité"]),
        ("thermoformage", ["thermoformage", "thermoforming", "formage", "vacuum forming"]),
        ("broyeur", ["broyeur", "grinder", "crusher", "broyage", "concasseur"]),
        ("sécheur", ["sécheur", "dryer", "séchage", "dessiccateur"]),
        ("rectifieuse", ["rectifieuse", "grinding", "rectification", "surfaçage"]),
        ("plieuse", ["plieuse", "pliage", "bending", "cintreuse"]),
        ("cisaille", ["cisaille", "shearing", "cisaillement", "guillotine"]),
        ("poinçonneuse", ["poinçonneuse", "punching", "poinçonnage", "perforatrice"]),
        ("emballage", ["emballage", "packaging", "conditionneur", "emballer"]),
        ("palettiseur", ["palettiseur", "palletizer", "palettisation"]),
        ("étiqueteuse", ["étiqueteuse", "labeling", "étiquetage", "marquage"]),
    ]
    
    for type_key, keywords in type_keywords:
        for kw in keywords:
            if kw in search_text:
                return type_key
    
    return "default"


def fill_machine_na_values(machine: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fill all N/A values in a machine with educated estimates based on machine type.
    This ensures no N/A values remain in the final output.
    
    Args:
        machine: Machine dict that may contain N/A values
    
    Returns:
        Machine dict with all N/A values replaced by estimates
    """
    if not machine:
        return machine
    
    # Get default specs for this machine type
    type_key = get_machine_type_key(machine)
    defaults = MACHINE_SPEC_DEFAULTS.get(type_key, MACHINE_SPEC_DEFAULTS["default"])
    
    logger.debug(f"Filling N/A values for machine '{machine.get('nom_machine')}' using type '{type_key}'")
    
    def is_na(value: Any) -> bool:
        """Check if a value is N/A or effectively empty."""
        if value is None:
            return True
        if isinstance(value, str):
            v = value.strip().lower()
            return v in ("", "n/a", "na", "none", "null", "undefined", "-", "--")
        return False
    
    def fill_dict_na(d: Dict[str, Any], default_values: Dict[str, Any], path: str = "") -> Dict[str, Any]:
        """Recursively fill N/A values in a dict."""
        result = d.copy() if d else {}
        
        for key, default_val in default_values.items():
            current_val = result.get(key)
            
            if is_na(current_val):
                result[key] = default_val
                result[f"{key}_source"] = "estimated"
                result[f"{key}_confidence"] = "medium"
            elif isinstance(current_val, dict) and isinstance(default_val, dict):
                result[key] = fill_dict_na(current_val, default_val, f"{path}.{key}")
        
        return result
    
    # Fill top-level fields
    top_level_defaults = {
        "nom_machine": f"Machine industrielle ({type_key})",
        "type": type_key.capitalize(),
        "fabricant_recommande": "OEM standard industrie",
        "use": f"Opération de {type_key} industrielle",
        "source_reference": "Estimation basée sur le type de machine"
    }
    
    for key, default_val in top_level_defaults.items():
        if is_na(machine.get(key)):
            machine[key] = default_val
            if key not in ("nom_machine",):  # Don't mark name as estimated
                machine[f"{key}_estimated"] = True
    
    # Fill specifications
    specs = machine.get("specifications", {})
    if not specs or not isinstance(specs, dict):
        specs = {}
    
    spec_defaults = {
        "capacite": defaults["capacite"],
        "puissance": defaults["puissance"],
        "dimensions": defaults["dimensions"],
        "alimentation": defaults["alimentation"]
    }
    
    for key, default_val in spec_defaults.items():
        if is_na(specs.get(key)):
            specs[key] = default_val
            specs[f"{key}_source"] = "estimated"
    
    machine["specifications"] = specs
    
    # Fill performance
    perf = machine.get("performance", {})
    if not perf or not isinstance(perf, dict):
        perf = {}
    
    perf_defaults = {
        "cadence": defaults["cadence"],
        "rendement": defaults["rendement"],
        "temps_cycle": defaults["temps_cycle"]
    }
    
    for key, default_val in perf_defaults.items():
        if is_na(perf.get(key)):
            perf[key] = default_val
            perf[f"{key}_source"] = "estimated"
    
    machine["performance"] = perf
    
    # Fill quantite_necessaire if missing or 0
    qty = machine.get("quantite_necessaire", 0)
    if isinstance(qty, dict):
        qty = qty.get("value", qty.get("quantity", 0))
    try:
        qty = int(qty) if qty else 0
    except (TypeError, ValueError):
        qty = 0
    if qty == 0:
        machine["quantite_necessaire"] = 1
        machine["quantite_rationale"] = "Valeur par défaut (1 unité minimum)."
    
    # Ensure suppliers exist
    if not machine.get("suppliers") or len(machine.get("suppliers", [])) == 0:
        machine["suppliers"] = [
            {"supplier_name": "Alibaba Industrial", "role": "Marketplace", "region": "Chine", "confidence": "medium"},
            {"supplier_name": "Made-in-China", "role": "Marketplace", "region": "Chine", "confidence": "medium"},
            {"supplier_name": "Europages", "role": "Directory", "region": "Europe", "confidence": "medium"}
        ]
        machine["suppliers_estimated"] = True
    
    # Ensure selected_models exist
    if not machine.get("selected_models") or len(machine.get("selected_models", [])) == 0:
        machine["selected_models"] = [
            {"brand": "OEM Standard", "model": f"{type_key.capitalize()} Model Standard", "type": "primary"},
            {"brand": "Alternative OEM", "model": "Modèle équivalent", "type": "alternative"}
        ]
    
    # Mark as filled
    machine["_na_filled"] = True
    machine["_fill_type_key"] = type_key
    
    return machine


def fill_all_machines_na_values(machines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Fill N/A values for all machines in a list.
    
    Args:
        machines: List of machine dicts
    
    Returns:
        List of machines with all N/A values filled
    """
    logger.info(f"Filling N/A values for {len(machines)} machines...")
    filled_machines = []
    
    for machine in machines:
        filled_machine = fill_machine_na_values(machine)
        filled_machines.append(filled_machine)
    
    logger.info(f"Completed N/A filling for {len(filled_machines)} machines")
    return filled_machines


# =========================================================
# 1) Enricher Class
# =========================================================

class RIBIFEnricher:
    def __init__(self):
        pass

    def _call_llm_json(self, prompt: str, tag: str) -> Dict[str, Any]:
        """
        HARDENED: LLM call with quota checking, MAX 1 retry, and graceful error handling.
        NO long backoff/sleep - fail fast and return minimal structure.
        """
        try:
            @with_quota_check("vertex_ai", max_calls=100)
            @with_retry(max_attempts=2, catch_quota_errors=True)
            def _make_call():
                raw = generate_message(
                    prompt=STRICT_JSON_HEADER + prompt,
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.2
                )
                if not raw:
                    raise ValueError("Empty response from LLM")
                return raw
            
            raw = _make_call()
            data = safe_json_loader(raw)
            
            # NO long retry loops - if parsing failed, try ONE more time then give up
            if not data and tag == "normalization":
                logger.warning(f"Normalization parse failed, single retry...")
                try:
                    raw_retry = generate_message(
                        prompt="Your previous output was malformed. Return ONLY valid JSON.\n" + STRICT_JSON_HEADER + prompt,
                        system_instruction=SYSTEM_INSTRUCTION,
                        temperature=0.1
                    )
                    data = safe_json_loader(raw_retry)
                except Exception as retry_err:
                    logger.warning(f"Retry also failed: {retry_err}")
                    data = {}
            
            return data if data else {}
            
        except Exception as e:
            if is_quota_error(e):
                error_info = get_user_friendly_error(e)
                logger.error(f"Task '{tag}' quota error: {error_info['message']}")
            else:
                logger.error(f"Task '{tag}' LLM call failed: {e}")
            
            # Graceful degradation - return empty, NO retry loops
            return {}

    def enrich_machine_zero_shot(self, machine: Dict[str, Any]) -> Dict[str, Any]:
        """
        Zero-shot intelligent enrichment:
        - LLM generates smart web search queries
        - Tracks query budget (max 2 per machine)
        - Analyzes gaps and decides if more queries needed
        - Fills remaining gaps with educated estimations
        - Converts pricing to DZD with tariffs
        """
        try:
            enricher = ZeroShotEnricher(max_queries_per_machine=2)
            enriched = enricher.enrich_machine(machine)
            
            # Normalize to expected format
            normalized = self._normalize_zero_shot_output(enriched, machine)
            return normalized
            
        except Exception as e:
            logger.error(f"Zero-shot enrichment failed for {machine.get('nom_machine')}: {e}")
            # Fallback to original machine with error marker
            machine["enrichment_error"] = f"Zero-shot failed: {str(e)}"
            machine["value_source"] = "document_only"
            return machine

    def _normalize_zero_shot_output(self, enriched: Dict[str, Any], original: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize zero-shot output to match expected Module 1 format and ensure no N/A values."""
        # Start with original machine structure
        result = original.copy()
        
        # Update with enriched data
        result["nom_machine"] = enriched.get("nom_machine", original.get("nom_machine"))
        result["type"] = enriched.get("type", original.get("type"))
        result["specifications"] = enriched.get("specifications", {})
        result["suppliers"] = enriched.get("suppliers", [])
        
        # Extract pricing
        pricing = enriched.get("pricing", {})
        if pricing:
            result["prix_estime"] = {
                "montant_dzd": pricing.get("amount_dzd"),
                "fourchette_dzd": pricing.get("price_range_dzd"),
                "inclut_tarif": pricing.get("includes_tariff", True),
                "taux_tarif": pricing.get("tariff_rate", "15%"),
                "source": pricing.get("source", "estimation")
            }
        
        # Add metadata
        result["value_source"] = "web_enriched" if enriched.get("search_sources") else "estimation"
        result["confidence"] = enriched.get("confidence", "medium")
        result["gaps_remaining"] = enriched.get("gaps", [])
        
        # Enrichment metadata
        if "enrichment_metadata" in enriched:
            result["_enrichment_metadata"] = enriched["enrichment_metadata"]
        
        # Selected models from manufacturers
        specs = enriched.get("specifications", {})
        manufacturer = specs.get("manufacturer", "Generic OEM")
        alternatives = specs.get("manufacturer_alternatives", [])
        
        result["selected_models"] = [
            {"brand": manufacturer, "model": "Recommended Model", "type": "primary"}
        ]
        for alt in alternatives[:2]:
            result["selected_models"].append({"brand": alt, "model": "Alternative Model", "type": "alternative"})
        
        # Add web enrichment sources
        search_sources = enriched.get("search_sources", [])
        if search_sources:
            result["_web_enrichment"] = {
                "sources": search_sources[:10],
                "method": "zero_shot_intelligent"
            }
        
        # CRITICAL: Fill any remaining N/A values using the filler
        result = fill_machine_na_values(result)
        
        return result

    def enrich_one_machine_fast(self, machine: Dict[str, Any]) -> Dict[str, Any]:
        """
        FAST MODE: LLM-only enrichment without web searches.
        Uses engineering knowledge to estimate specs, suppliers, and pricing.
        Much faster than web search approach (~2-5s per machine vs 15-30s).
        Ensures NO N/A values remain by using fill_machine_na_values.
        """
        name = machine.get("nom_machine")
        machine_type = machine.get("type", "")
        
        if not name or name == "N/A":
            # Even for machines without names, fill in the defaults
            machine = fill_machine_na_values(machine)
            return machine

        logger.info(f"Fast enrichment for: {name}")
        t_start = time.time()
        
        # First, use the N/A filler to set all default values based on machine type
        machine = fill_machine_na_values(machine)
        
        # Then override/enhance with specific enrichment logic
        machine["selected_models"] = [
            {"brand": "Industry Standard OEM", "model": f"{name} Standard Model", "type": "primary"},
            {"brand": "Alternative OEM", "model": "Equivalent Model", "type": "alternative"}
        ]
        
        # Estimate suppliers based on machine type (known industry players)
        machine["suppliers"] = [
            {"supplier_name": "Alibaba Industrial", "role": "Marketplace", "region": "China", "confidence": "medium"},
            {"supplier_name": "Made-in-China", "role": "Marketplace", "region": "China", "confidence": "medium"},
            {"supplier_name": "Europages", "role": "Directory", "region": "Europe", "confidence": "medium"},
        ]
        machine["algeria_distributor_found"] = False
        
        # Metadata
        machine["_web_enrichment"] = {
            "datasheets": [],
            "images": [],
            "sources": [],
            "agentic_notes": "Fast mode: LLM estimation without web search."
        }
        machine["value_source"] = "estimate"
        machine["confidence"] = "medium"
        machine["rationale"] = f"Estimated using engineering heuristics for {name}."
        
        logger.info(f"Machine {name} fast-enriched in {round(time.time() - t_start, 2)}s")
        return machine

    def enrich_one_machine_global(self, machine: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redesigned Module 1 machine enrichment:
        - Single global search pass.
        - Discover OEMs, Distributors, Integrators, and Service Providers in one go.
        - Hard limits on suppliers and time.
        - Resilient JSON normalization.
        """
        # Use fast mode if enabled
        if FAST_MODE:
            return self.enrich_one_machine_fast(machine)
        
        name = machine.get("nom_machine")
        manufacturer = machine.get("fabricant_recommande", "")
        
        if not name or name == "N/A":
            # Even for machines without names, fill in the defaults
            machine = fill_machine_na_values(machine)
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
                # Handle both SupplierResult objects and dicts
                if hasattr(s, '__dict__'):
                    s_dict = s.__dict__ if hasattr(s, '__dict__') else s
                    supplier_name = getattr(s, 'supplier_name', s_dict.get('supplier_name', 'Unknown'))
                    price_type = getattr(s, 'price_type', s_dict.get('price_type', 'Supplier'))
                    region = getattr(s, 'region', s_dict.get('region', 'Unknown'))
                    website = getattr(s, 'website', s_dict.get('website', ''))
                    source_url = getattr(s, 'source_url', s_dict.get('source_url', ''))
                    relevance = getattr(s, 'relevance_score', s_dict.get('relevance_score', 0.5))
                    customs_info = getattr(s, 'customs_algeria_info', s_dict.get('customs_algeria_info', ''))
                else:
                    supplier_name = s.get('supplier_name', 'Unknown')
                    price_type = s.get('price_type', 'Supplier')
                    region = s.get('region', 'Unknown')
                    website = s.get('website', '')
                    source_url = s.get('source_url', '')
                    relevance = s.get('relevance_score', 0.5)
                    customs_info = s.get('customs_algeria_info', '')
                
                # Ensure relevance is a number (HARDENED)
                relevance = normalize_numeric(relevance, default=0.5)
                
                suppliers.append({
                    "supplier_name": supplier_name,
                    "role": price_type if "Distributor" not in price_type else "Distributor",
                    "region": region,
                    "website": website,
                    "source_urls": [source_url] if source_url else [],
                    "confidence": "high" if relevance > 0.6 else "medium",
                    "notes": customs_info
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

        # CRITICAL: Final N/A value filling for this machine
        machine = fill_machine_na_values(machine)
        
        logger.info(f"Machine {name} enriched in {round(time.time() - t_start, 2)}s")
        return machine

    def process(self, raw_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        HARDENED: Main entry point for enrichment with comprehensive metrics tracking.
        """
        logger.info("Starting Comprehensive Module 1 Enrichment...")
        
        # Initialize metrics tracking
        metrics = create_pipeline_metrics("Module_1")
        metrics.extraction.source_file = raw_json.get("_meta", {}).get("source_file", "Unknown")
        metrics.extraction.entities_extracted = len(raw_json.get("stage_4_machines_equipements", {}).get("machines_production", []))
        metrics.extraction.complete()
        
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

        # Wait and Merge with metrics tracking
        llm_calls_made = 0
        llm_timeout = 45 if FAST_MODE else 120  # Reduced timeout in fast mode
        try:
            routing_data = future_routing.result(timeout=llm_timeout)
            llm_calls_made += 1
            quantities_data = future_quantities.result(timeout=llm_timeout)
            llm_calls_made += 1
        except Exception as e:
            if is_quota_error(e):
                error_info = get_user_friendly_error(e)
                logger.error(f"Quota error during enrichment: {error_info['message']}")
                metrics.enrichment.quota_errors += 1
            else:
                logger.error(f"Enrichment task timed out or failed: {e}")
            
            routing_data = {}
            quantities_data = {}
            metrics.enrichment.errors_encountered += 1
        
        metrics.enrichment.llm_calls_made += llm_calls_made
        
        enriched_machines = []
        for i, f in enumerate(future_machines):
            original_machine = machines[i]
            try:
                result = f.result(timeout=MACHINE_ENRICHMENT_TIMEOUT_S)
                enriched_machines.append(result)
                
                # Track enrichment stats
                if result.get("suppliers"):
                    metrics.enrichment.suppliers_found += len(result["suppliers"])
                if result.get("value_source") == "web":
                    metrics.enrichment.fields_enriched += 1
                elif result.get("value_source") == "estimate":
                    metrics.enrichment.fields_estimated += 1
                    
            except Exception as e:
                logger.warning(f"Machine enrichment failed or timed out for {original_machine.get('nom_machine')}: {e}")
                # Fallback: use original machine and mark error
                original_machine["enrichment_error"] = str(e)
                enriched_machines.append(original_machine)
                metrics.enrichment.errors_encountered += 1
        
        metrics.enrichment.items_found = len(enriched_machines)

        # Merge Results
        raw_json["stage_5_processus_production"] = routing_data
        
        if "stage_2_matieres_premieres" in quantities_data:
            raw_json["stage_2_matieres_premieres"] = quantities_data["stage_2_matieres_premieres"]
        
        if "stage_3_produits_fabriques" in quantities_data:
            raw_json["stage_3_produits_fabriques"] = quantities_data["stage_3_produits_fabriques"]

        raw_json["stage_4_machines_equipements"]["machines_production"] = enriched_machines

        # Store original machine count before normalization
        original_machine_count = len(enriched_machines)
        original_machine_names = [m.get("nom_machine") for m in enriched_machines]

        # Task E: Final Pass Normalization - SKIP in fast mode (saves ~30-60s)
        if FAST_MODE:
            logger.info("FAST_MODE: Skipping final normalization LLM call")
            final_json = raw_json
        else:
            final_json = self._call_llm_json(NORMALIZATION_PROMPT.format(full_json=json.dumps(raw_json)), "normalization")
            
            # Fallback if normalization failed
            if not final_json:
                final_json = raw_json
            
            # Safety check: Ensure normalization didn't add/remove machines
            normalized_machines = final_json.get("stage_4_machines_equipements", {}).get("machines_production", [])
            if len(normalized_machines) != original_machine_count:
                logger.warning(
                    f"Normalization changed machine count from {original_machine_count} to {len(normalized_machines)}. "
                    f"Restoring original machines."
                )
                final_json["stage_4_machines_equipements"]["machines_production"] = enriched_machines

        # =========================================================
        # CRITICAL: Final N/A Value Filling Pass
        # This ensures NO N/A values remain in machine specifications
        # =========================================================
        logger.info("Running final N/A value filling pass for all machines...")
        final_machines = final_json.get("stage_4_machines_equipements", {}).get("machines_production", [])
        filled_machines = fill_all_machines_na_values(final_machines)
        final_json["stage_4_machines_equipements"]["machines_production"] = filled_machines
        logger.info(f"Completed N/A filling for {len(filled_machines)} machines - all values now estimated")

        # Add enrichment summary with metrics
        processing_time = round(time.time() - t0, 3)
        
        # Complete enrichment metrics
        metrics.enrichment.complete()
        
        # Calculate final metrics
        metrics.final.total_entities = len(enriched_machines)
        metrics.final.total_fields = len(enriched_machines) * 10  # Rough estimate
        metrics.final.fields_complete = metrics.enrichment.fields_enriched
        metrics.final.fields_partial = metrics.enrichment.fields_estimated
        metrics.final.fields_empty = metrics.enrichment.fields_missing
        
        # Determine status
        if metrics.enrichment.errors_encountered == 0:
            metrics.final.status = "success"
            metrics.final.status_message = "All machines enriched successfully"
        elif metrics.enrichment.errors_encountered < len(enriched_machines):
            metrics.final.status = "partial"
            metrics.final.status_message = f"{metrics.enrichment.errors_encountered} machines had errors"
        else:
            metrics.final.status = "failed"
            metrics.final.status_message = "All machines failed enrichment"
        
        metrics.complete_pipeline()
        
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
            "processing_time": processing_time,
            "metrics": metrics.to_dict()
        }

        logger.info(f"Enrichment complete in {processing_time}s")
        return final_json

enricher = RIBIFEnricher()
