"""
RIBIF Module 6: TCO (Total Cost of Ownership) Calculation
Consolidated module following ribif_module_1 structure
Uses Gemini API for cost estimations

TCO Formula: TCO = Ci + Co + Cm + Cd - Rv

Component Breakdown:
- Ci (Initial Costs) = Cp + Cins + Ctr + Cinf + Ci_training
  * Cp: Purchase price (equipment cost + import duties + taxes)
  * Cins: Installation (site prep, connections, commissioning)
  * Ctr: Transportation (shipping, freight, handling, insurance)
  * Cinf: Infrastructure (building mods, utilities upgrade)
  * Ci_training: Training (operator training, documentation)

- Co (Operating Costs) = Ce + Clab + Ccons + Cutil
  * Ce: Energy (electricity, gas, fuel)
  * Clab: Labor (operators, supervision, benefits)
  * Ccons: Consumables (lubricants, filters, tooling)
  * Cutil: Utilities (water, compressed air, cooling)

- Cm (Maintenance Costs) = Cpm + Ccm + Csp
  * Cpm: Preventive maintenance (scheduled inspections)
  * Ccm: Corrective maintenance (unplanned repairs)
  * Csp: Spare parts (replacement components)

- Cd (Downtime/Hidden Costs) = Cprod_loss + Cqual + Cenv + Ccompliance
  * Cprod_loss: Production loss (lost output × margin)
  * Cqual: Quality costs (scrap, rework, returns)
  * Cenv: Environmental (waste, emissions)
  * Ccompliance: Regulatory (permits, certifications)

- Rv (Residual Value) = (Cp × depreciation_factor) - Cdisposal
  * Depreciation factor: 10-30% after 10-15 years
  * Cdisposal: Decommissioning and removal costs
"""
import os
import json
import re
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import date, datetime
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

from utils.logger import get_logger

logger = get_logger(__name__)

# ============================================
# MODULE VERSION FOR IDEMPOTENCY
# ============================================
MODULE6_VERSION = "v1"

# ============================================
# HEURISTIC FALLBACK TABLE (by machine category)
# ============================================
MACHINE_HEURISTICS = {
    "injection": {"base_price": 12_000_000, "impl_pct": 0.10, "ops_pct": 0.05, "maint_pct": 0.04},
    "extrusion": {"base_price": 15_000_000, "impl_pct": 0.12, "ops_pct": 0.06, "maint_pct": 0.05},
    "thermoform": {"base_price": 10_000_000, "impl_pct": 0.10, "ops_pct": 0.05, "maint_pct": 0.04},
    "cnc": {"base_price": 18_000_000, "impl_pct": 0.08, "ops_pct": 0.04, "maint_pct": 0.03},
    "robot": {"base_price": 20_000_000, "impl_pct": 0.15, "ops_pct": 0.06, "maint_pct": 0.05},
    "conveyor": {"base_price": 4_000_000, "impl_pct": 0.08, "ops_pct": 0.03, "maint_pct": 0.02},
    "compressor": {"base_price": 3_500_000, "impl_pct": 0.06, "ops_pct": 0.04, "maint_pct": 0.03},
    "mixer": {"base_price": 5_000_000, "impl_pct": 0.08, "ops_pct": 0.04, "maint_pct": 0.03},
    "packaging": {"base_price": 8_000_000, "impl_pct": 0.10, "ops_pct": 0.05, "maint_pct": 0.04},
    "assembly": {"base_price": 7_000_000, "impl_pct": 0.10, "ops_pct": 0.05, "maint_pct": 0.04},
    "lamination": {"base_price": 12_000_000, "impl_pct": 0.10, "ops_pct": 0.05, "maint_pct": 0.04},
    "glass": {"base_price": 25_000_000, "impl_pct": 0.12, "ops_pct": 0.06, "maint_pct": 0.05},
    "recycling": {"base_price": 15_000_000, "impl_pct": 0.12, "ops_pct": 0.06, "maint_pct": 0.05},
    "storage": {"base_price": 8_000_000, "impl_pct": 0.08, "ops_pct": 0.03, "maint_pct": 0.02},
    "agv": {"base_price": 15_000_000, "impl_pct": 0.10, "ops_pct": 0.04, "maint_pct": 0.03},
    "default": {"base_price": 10_000_000, "impl_pct": 0.10, "ops_pct": 0.05, "maint_pct": 0.04},
}

MATERIAL_HEURISTICS = {
    "polymer": {"unit_price": 2_500, "transport_pct": 0.08, "storage_pct": 0.02, "wastage_pct": 0.015},
    "resin": {"unit_price": 3_200, "transport_pct": 0.08, "storage_pct": 0.02, "wastage_pct": 0.015},
    "plastic": {"unit_price": 1_800, "transport_pct": 0.08, "storage_pct": 0.02, "wastage_pct": 0.015},
    "glass": {"unit_price": 4_500, "transport_pct": 0.10, "storage_pct": 0.03, "wastage_pct": 0.02},
    "metal": {"unit_price": 3_800, "transport_pct": 0.10, "storage_pct": 0.02, "wastage_pct": 0.015},
    "additive": {"unit_price": 8_000, "transport_pct": 0.06, "storage_pct": 0.015, "wastage_pct": 0.01},
    "colorant": {"unit_price": 9_500, "transport_pct": 0.06, "storage_pct": 0.015, "wastage_pct": 0.01},
    "default": {"unit_price": 2_800, "transport_pct": 0.08, "storage_pct": 0.02, "wastage_pct": 0.015},
}


# ============================================
# HELPER FUNCTIONS
# ============================================

def canonicalize_name(name: str) -> str:
    """
    Normalize a material/machine name for matching:
    - lowercase
    - remove parentheses content
    - remove quantities, units, descriptors after dash
    - strip extra whitespace
    """
    if not name:
        return ""
    result = name.lower().strip()
    # Remove parentheses and their content
    result = re.sub(r'\s*\([^)]*\)', '', result)
    # Remove content after dash (often quantities/descriptors)
    result = re.sub(r'\s*-\s*.*$', '', result)
    # Remove quantities/numbers with units
    result = re.sub(r'\b\d+\s*(kg|g|t|tonnes?|litres?|l|m|cm|mm)\b', '', result, flags=re.IGNORECASE)
    # Normalize whitespace
    result = re.sub(r'\s+', ' ', result).strip()
    return result


def compute_input_fingerprint(data: Dict[str, Any]) -> str:
    """
    Compute SHA256 fingerprint of canonical Module 6 input.
    Used for idempotency checking.
    """
    # Extract only the fields that affect computation
    canonical = {
        "machines": [],
        "materials": [],
        "products": [],
    }
    
    # Machines from enriched data
    for m in data.get("machines_enriched", []):
        machine_input = m.get("machine_input", {})
        canonical["machines"].append({
            "name": canonicalize_name(machine_input.get("nom_machine", "")),
            "type": machine_input.get("type", ""),
        })
    
    # Materials from stage 2
    stage_2 = data.get("stage_2_matieres_premieres", {})
    matieres = stage_2.get("matieres_premieres", [])
    if isinstance(matieres, dict):
        matieres = matieres.get("matieres_premieres", [])
    for mat in matieres:
        canonical["materials"].append(canonicalize_name(mat.get("nom_materiau", "")))
    
    # Products from stage 3
    stage_3 = data.get("stage_3_produits_fabriques", {})
    products = stage_3.get("produits_fabriques", [])
    if isinstance(products, dict):
        products = products.get("produits_fabriques", [])
    for p in products:
        canonical["products"].append(canonicalize_name(p.get("nom_produit", "")))
    
    # Sort for determinism
    canonical["machines"].sort(key=lambda x: x.get("name", ""))
    canonical["materials"].sort()
    canonical["products"].sort()
    
    canonical_json = json.dumps(canonical, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical_json.encode()).hexdigest()[:16]


def get_machine_category_key(machine_name: str, machine_type: str = "") -> str:
    """Determine heuristic category from machine name/type."""
    text = f"{machine_name} {machine_type}".lower()
    if "injection" in text:
        return "injection"
    if "extru" in text:
        return "extrusion"
    if "thermo" in text:
        return "thermoform"
    if "cnc" in text or "usinage" in text:
        return "cnc"
    if "robot" in text:
        return "robot"
    if "convoy" in text or "conveyor" in text or "transport" in text:
        return "conveyor"
    if "compress" in text:
        return "compressor"
    if "mix" in text or "mélang" in text:
        return "mixer"
    if "emball" in text or "packag" in text:
        return "packaging"
    if "assembl" in text:
        return "assembly"
    if "lamin" in text:
        return "lamination"
    if "verre" in text or "glass" in text:
        return "glass"
    if "recycl" in text or "granul" in text:
        return "recycling"
    if "stock" in text or "silo" in text or "asrs" in text:
        return "storage"
    if "agv" in text or "guidage" in text:
        return "agv"
    return "default"


def get_material_category_key(material_name: str) -> str:
    """Determine heuristic category from material name."""
    text = material_name.lower()
    if any(k in text for k in ["polyur", "polyprop", "polyéth", "polyeth", "pvc", "abs", "pe", "pp", "polymer"]):
        return "polymer"
    if "resin" in text or "résine" in text or "époxy" in text or "epoxy" in text:
        return "resin"
    if "plast" in text:
        return "plastic"
    if "verre" in text or "glass" in text:
        return "glass"
    if any(k in text for k in ["métal", "metal", "acier", "steel", "alumin", "fer", "iron"]):
        return "metal"
    if "additif" in text or "additive" in text:
        return "additive"
    if "color" in text or "pigment" in text or "teint" in text:
        return "colorant"
    return "default"


def get_heuristic_machine_estimate(machine_name: str, machine_type: str = "") -> Dict[str, Any]:
    """Generate heuristic-based machine estimate when LLM fails."""
    category = get_machine_category_key(machine_name, machine_type)
    h = MACHINE_HEURISTICS.get(category, MACHINE_HEURISTICS["default"])
    base = h["base_price"]
    return {
        "estimated_purchase_price": base,
        "implementation_cost": int(base * h["impl_pct"]),
        "annual_operations_cost": int(base * h["ops_pct"]),
        "annual_maintenance_cost": int(base * h["maint_pct"]),
        "annual_downtime_cost": int(base * 0.02),
        "resale_value": int(base * 0.35),
        "disposal_cost": int(base * 0.02),
        "lifetime_years": 10,
        "confidence": "low",
        "source": "heuristic",
        "notes": f"Heuristic estimate based on category '{category}' - LLM estimation failed",
    }


def get_heuristic_material_estimate(material_name: str) -> Dict[str, Any]:
    """Generate heuristic-based material estimate when LLM fails."""
    category = get_material_category_key(material_name)
    h = MATERIAL_HEURISTICS.get(category, MATERIAL_HEURISTICS["default"])
    return {
        "unit_price": h["unit_price"],
        "transport_pct": h["transport_pct"],
        "storage_pct": h["storage_pct"],
        "wastage_pct": h["wastage_pct"],
        "confidence": "low",
        "source": "heuristic",
        "notes": f"Heuristic estimate based on category '{category}' - LLM estimation failed",
    }

# ============================================
# PYDANTIC MODELS
# ============================================

class MachineSpecs(BaseModel):
    """Machine specifications from RIBIF"""
    capacite: Optional[str] = None
    puissance: Optional[str] = None
    dimensions: Optional[Dict[str, str]] = None
    poids: Optional[str] = None
    alimentation: Optional[str] = None


class MachineInput(BaseModel):
    """Machine input from RIBIF module"""
    id: str
    name: str
    category: str
    manufacturer: str
    base_model: Optional[str] = None
    original_specs: MachineSpecs


class SupplierInfo(BaseModel):
    """Supplier information from web search"""
    supplier_name: str
    website: str
    region: str
    price_estimate: Optional[float] = None
    lead_time_days: Optional[int] = None
    source: str
    notes: Optional[str] = None
    relevance_score: float = 0.0


class TCOCalculationInput(BaseModel):
    """Combined RIBIF input for TCO calculation"""
    machine_input: MachineInput
    suppliers: List[SupplierInfo] = []
    ribif_metadata: Optional[Dict[str, Any]] = None
    estimated_revenue: Optional[float] = None
    stage_1_informations_generales: Optional[Dict[str, Any]] = None
    stage_2_matieres_premieres: Optional[Dict[str, Any]] = None
    stage_3_produits_fabriques: Optional[Dict[str, Any]] = None
    stage_4_machines_equipements: Optional[Dict[str, Any]] = None
    stage_5_processus_production: Optional[Dict[str, Any]] = None
    stage_6_informations_complementaires: Optional[Dict[str, Any]] = None


class CostBreakdown(BaseModel):
    """Percentage breakdown of TCO components"""
    initial_pct: float
    operations_pct: float
    maintenance_pct: float
    downtime_pct: float
    resale_offset_pct: float


class MachineTCO(BaseModel):
    """TCO calculation for a single machine"""
    machine_id: str
    machine_name: str
    category: str
    manufacturer: str
    initial_cost: float
    operations_cost: float
    maintenance_cost: float
    downtime_cost: float
    resale_value: float
    total_tco: float
    annual_tco: float
    lifetime_years: int
    cost_breakdown: CostBreakdown
    estimated_purchase_price: float
    estimation_confidence: str
    estimation_source: str = "llm"
    estimation_notes: str = Field(default="", exclude=True)


class ProductTCO(BaseModel):
    """TCO calculation for a product category"""
    nom_produit: str
    categorie: Optional[str] = None
    landing_cost: float
    holding_cost: float
    quality_cost: float
    administrative_cost: float
    total_tco: float


class RawMaterialTCO(BaseModel):
    """TCO calculation for a raw material"""
    nom_materiau: str
    type_materiau: Optional[str] = None
    categorie: Optional[str] = None
    quantite_annuelle: float
    unite: str
    unit_price: float
    annual_cost: float
    transport_cost: float
    storage_cost: float
    wastage_cost: float
    total_tco: float
    estimation_confidence: str
    estimation_source: str = "llm"
    estimation_notes: str = Field(default="", exclude=True)


class AnnualTCOBreakdown(BaseModel):
    """Annual breakdown of TCO"""
    year: int
    machines_tco: float
    products_tco: float
    raw_materials_tco: float
    total_tco: float
    cumulative_tco: float


class TCOCalculationOutput(BaseModel):
    """Complete TCO calculation response"""
    company_name: str
    project_name: str
    calculation_date: date
    total_tco: float
    average_annual_tco: float
    tco_per_unit_revenue: float
    machine_tco: List[MachineTCO]
    total_machines_tco: float
    product_tco: List[ProductTCO]
    total_products_tco: float
    raw_materials_tco: List[RawMaterialTCO] = []
    total_raw_materials_tco: float = 0.0
    annual_tco: List[AnnualTCOBreakdown]
    stage_1_informations_generales: Dict[str, Any]
    stage_2_matieres_premieres: Dict[str, Any] = {}
    stage_3_produits_fabriques: Dict[str, Any]
    stage_6_informations_complementaires: Dict[str, Any]


# ============================================
# RIBIF MODULE 6 - TCO CALCULATOR
# ============================================

class RIBIFModule6TCO:
    """
    RIBIF Module 6: Total Cost of Ownership Calculator
    Uses Gemini API for intelligent cost estimation with Algerian market context
    Supports English and French input/output
    All monetary values are in Algerian Dinar (DZD)
    """
    
    SYSTEM_PROMPT = """You are an expert in financial analysis and industrial cost estimation for SMALL TO MID-SIZE companies in Algeria.
You must estimate realistic acquisition, operating, maintenance, and disposal costs of industrial equipment.

CRITICAL RULES:
1. These are SMALL TO MID-SIZE Algerian companies with annual revenue of 50M-500M DZD.
2. All prices must be realistic for this market segment - NOT prices for large multinationals.
3. ASSUME USED OR ENTRY-LEVEL EQUIPMENT unless explicitly specified as "new" or "premium".
4. ALL VALUES MUST BE IN ALGERIAN DINAR (DZD).
5. BE CONSERVATIVE - when in doubt, estimate LOWER not higher.

=== REALISTIC PRICE RANGES (DZD) - THESE ARE YOUR HARD LIMITS ===

INDIVIDUAL MACHINES (single units, not production lines):
- Small injection molding (≤200t): 4,000,000 - 12,000,000 DZD
- Medium injection molding (200-500t): 12,000,000 - 25,000,000 DZD
- Extrusion machine (single): 6,000,000 - 18,000,000 DZD
- CNC machine (basic-mid): 6,000,000 - 20,000,000 DZD
- Industrial mixer/blender: 1,500,000 - 8,000,000 DZD
- Packaging machine: 2,000,000 - 10,000,000 DZD
- Conveyor system: 1,000,000 - 5,000,000 DZD
- Compressor (industrial): 1,000,000 - 4,000,000 DZD
- Chiller unit: 1,500,000 - 6,000,000 DZD
- Lamination machine: 4,000,000 - 15,000,000 DZD
- Assembly equipment: 2,000,000 - 8,000,000 DZD
- AGV/automated transport: 8,000,000 - 20,000,000 DZD

PRODUCTION LINES (multiple integrated machines):
- Small production line: 15,000,000 - 40,000,000 DZD
- Medium production line: 40,000,000 - 80,000,000 DZD

RAW MATERIALS (DZD per tonne, CIF Algeria):
- Standard polymers (PP, PE, PVC): 150,000 - 220,000 DZD/tonne
- Engineering plastics (ABS, PC): 220,000 - 320,000 DZD/tonne
- Specialty resins (epoxy, PU): 280,000 - 450,000 DZD/tonne
- Additives/colorants: 350,000 - 600,000 DZD/tonne
- Glass materials: 180,000 - 350,000 DZD/tonne
- Metal materials: 180,000 - 300,000 DZD/tonne

ANNUAL COST RATIOS (as % of purchase price):
- Implementation/installation: 5-12%
- Annual operations (energy, labor): 4-10%
- Annual maintenance: 3-6%
- Annual downtime: 1-3%
- Resale value at end of life: 25-40%

IMPORTANT: If you're unsure, use the MIDDLE of the range, not the maximum.
Respond ONLY with valid JSON containing estimates in DZD (Algerian Dinar)."""

    # French keywords for language detection
    FRENCH_KEYWORDS = [
        "projet", "entreprise", "secteur", "activité", "produits", "fabriqués",
        "matières", "premières", "équipements", "processus", "production",
        "informations", "générales", "complémentaires", "capacité", "puissance",
        "machines", "fournisseurs", "coûts", "prix", "algérie"
    ]

    def __init__(self, api_key: str = None):
        """
        Initialize the RIBIF Module 6 TCO Calculator with Gemini API.
        """
        load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("❌ Error: GOOGLE_API_KEY not found.")

        self.client = genai.Client(api_key=self.api_key)
        self.model_name = "gemini-2.5-flash"
        self._detected_language = "en"  # Default to English
        logger.info("Gemini initialized for TCO Module: %s", self.model_name)

    def detect_language(self, input_data: Dict[str, Any]) -> str:
        """
        Detect the language of the input data (French or English).
        Returns 'fr' for French, 'en' for English.
        """
        text_content = json.dumps(input_data, ensure_ascii=False).lower()
        french_count = sum(1 for keyword in self.FRENCH_KEYWORDS if keyword in text_content)
        
        # If more than 3 French keywords found, consider it French
        if french_count >= 3:
            self._detected_language = "fr"
            return "fr"
        
        self._detected_language = "en"
        return "en"

    def call_gemini(self, prompt: str, retry_strict: bool = False) -> Tuple[Dict, bool, str]:
        """
        Call Gemini API and extract JSON from response.
        Returns (result_dict, json_ok, raw_response) tuple.
        """
        raw_response = ""
        try:
            if retry_strict:
                prompt = prompt + "\n\nCRITICAL: RETURN VALID JSON ONLY. All numeric fields must have numeric values (not null, not strings)."
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.SYSTEM_PROMPT,
                    temperature=0.3,
                    top_p=0.95,
                    top_k=64,
                ),
            )
            if hasattr(response, "text") and response.text:
                content = response.text.strip()
                raw_response = content
                
                # Strip markdown code fences if present
                if content.startswith("```"):
                    # Remove opening fence (```json or ```)
                    first_newline = content.find('\n')
                    if first_newline != -1:
                        content = content[first_newline + 1:]
                # Remove closing fence if present (may be at end or not)
                if "```" in content:
                    content = content.split("```")[0].strip()
                
                # Extract JSON from response
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    try:
                        parsed = json.loads(content[json_start:json_end])
                        return parsed, True, raw_response
                    except json.JSONDecodeError as je:
                        logger.error("JSON parse error: %s", je)
                        return {}, False, raw_response
                else:
                    logger.error("No JSON braces found. json_start=%s, json_end=%s", json_start, json_end)
                    return {}, False, raw_response
            else:
                if hasattr(response, 'prompt_feedback'):
                    logger.error("Response blocked: %s", response.prompt_feedback)
                else:
                    logger.error("Empty response from Gemini")
                return {}, False, raw_response
        except Exception as e:
            logger.error("Gemini API Error: %s", e)
            return {}, False, raw_response

    def _validate_machine_estimate(self, result: Dict, machine: Dict) -> Tuple[Dict, bool]:
        """
        Validate required values in the estimate.
        Returns (validated_dict, schema_ok) tuple.
        """
        required_numeric = [
            "estimated_purchase_price",
            "implementation_cost",
            "annual_operations_cost",
            "annual_maintenance_cost",
        ]
        optional_numeric = [
            "annual_downtime_cost",
            "resale_value",
            "disposal_cost",
            "lifetime_years",
        ]
        
        # Check required numeric fields
        for key in required_numeric:
            val = result.get(key)
            if val is None or val == "":
                return result, False
            try:
                float(val)
            except (TypeError, ValueError):
                return result, False
        
        # Check optional numeric fields - set defaults if missing
        for key in optional_numeric:
            val = result.get(key)
            if val is None or val == "":
                # Set reasonable defaults
                if key == "annual_downtime_cost":
                    result[key] = float(result["estimated_purchase_price"]) * 0.02
                elif key == "resale_value":
                    result[key] = float(result["estimated_purchase_price"]) * 0.35
                elif key == "disposal_cost":
                    result[key] = float(result["estimated_purchase_price"]) * 0.02
                elif key == "lifetime_years":
                    result[key] = 10
            else:
                try:
                    float(val)
                except (TypeError, ValueError):
                    return result, False

        return {
            "estimated_purchase_price": result.get("estimated_purchase_price"),
            "implementation_cost": result.get("implementation_cost"),
            "annual_operations_cost": result.get("annual_operations_cost"),
            "annual_maintenance_cost": result.get("annual_maintenance_cost"),
            "annual_downtime_cost": result.get("annual_downtime_cost"),
            "resale_value": result.get("resale_value"),
            "disposal_cost": result.get("disposal_cost"),
            "lifetime_years": result.get("lifetime_years"),
            "confidence": result.get("confidence", "medium"),
            "source": result.get("source", "llm"),
            "notes": result.get("notes", ""),
        }, True

    def _get_note(self, note_type: str) -> str:
        """Get note text in the appropriate language."""
        notes = {
            "fallback_machine": {
                "en": "Default estimate based on machine capacity",
                "fr": "Estimation par défaut basée sur la capacité de la machine"
            },
            "fallback_material": {
                "en": "Default estimate based on international market prices",
                "fr": "Estimation par défaut basée sur les prix du marché international"
            },
            "validated_machine": {
                "en": "Estimate based on provided specifications",
                "fr": "Estimation basée sur les spécifications fournies"
            },
            "validated_material": {
                "en": "LLM estimate validated",
                "fr": "Estimation LLM validée"
            }
        }
        return notes.get(note_type, {}).get(self._detected_language, notes.get(note_type, {}).get("en", ""))

    def estimate_machine_tco(
        self, 
        machine: Dict[str, Any], 
        suppliers: List[Dict[str, Any]],
        use_llm: bool = True
    ) -> Dict[str, Any]:
        """
        Estimate complete TCO for a machine based on RIBIF data and supplier info.
        """
        if not use_llm:
            raise ValueError("LLM estimation disabled; cannot produce machine TCO without explicit inputs.")
        
        no_supplier_text = "No suppliers identified" if self._detected_language == "en" else "Aucun fournisseur identifié"
        supplier_summary = "\n".join([
            f"- {s.get('supplier_name', 'Unknown')}: {s.get('region', 'N/A')} - {s.get('notes', '')[:100]}"
            for s in suppliers[:5]
        ]) if suppliers else no_supplier_text
        
        specs = machine.get('original_specs', {})
        # Ensure specs is a dict
        if hasattr(specs, 'model_dump'):
            specs = specs.model_dump()
        elif not isinstance(specs, dict):
            specs = {}
        specs_text = f"""
- Capacity: {specs.get('capacite', 'N/A')}
- Power: {specs.get('puissance', 'N/A')}
- Dimensions: {specs.get('dimensions', 'N/A')}
- Weight: {specs.get('poids', 'N/A')}
- Power supply: {specs.get('alimentation', 'N/A')}
"""
        
        # Detect if this is a production line vs single machine
        machine_name = machine.get('name', 'Unknown')
        is_production_line = any(kw in machine_name.lower() for kw in ['ligne de', 'ligne d\'', 'production line', 'ligne', 'système'])
        
        line_guidance = ""
        if is_production_line:
            line_guidance = """
IMPORTANT: This appears to be a PRODUCTION LINE, not a single machine.
For a SMALL Algerian company, estimate the MINIMUM viable configuration:
- estimated_purchase_price should be 15,000,000 - 60,000,000 DZD for most lines
- Only exceed 60,000,000 DZD if the line is highly complex or automated
- Assume USED or REFURBISHED equipment is acceptable
"""
        else:
            line_guidance = """
IMPORTANT: This is a SINGLE MACHINE (not a production line).
For a SMALL Algerian company:
- estimated_purchase_price should typically be 5,000,000 - 30,000,000 DZD
- Only exceed 30,000,000 DZD for very large/specialized equipment
- Assume USED or ENTRY-LEVEL equipment is acceptable
"""
        
        base_prompt = f"""Estimate the complete TCO for this industrial machine in Algeria with realistic, defensible numbers.
{line_guidance}
    Rules:
    - All amounts must be numeric (no strings) and in DZD.
    - Use realistic bounds and ratios:
      * implementation_cost: 5–15% of estimated_purchase_price
      * annual_operations_cost: 3–8% of estimated_purchase_price
      * annual_maintenance_cost: 2–6% of estimated_purchase_price
      * annual_downtime_cost: 1–4% of estimated_purchase_price
      * resale_value: 30–50% of estimated_purchase_price at end of life
      * disposal_cost: 1–3% of estimated_purchase_price
      * lifetime_years: 8–15
    - If supplier price signals exist, anchor estimated_purchase_price to them.
    - If specs are missing, infer a conservative mid‑range price for the category.
    - Round amounts to the nearest 1,000 DZD.

MACHINE: {machine_name}
ID: {machine.get('id', 'N/A')}
CATEGORY: {machine.get('category', 'N/A')}
MANUFACTURER: {machine.get('manufacturer', 'N/A')}

SPECIFICATIONS:
{specs_text}

IDENTIFIED SUPPLIERS:
{supplier_summary}

Estimate ALL the following costs in DZD:

1. ESTIMATED PURCHASE PRICE (Ci-purchase): New machine price
2. IMPLEMENTATION COSTS (Ci-implementation): Delivery, installation, training
3. ANNUAL OPERATING COSTS (Co): Energy, consumables, operators
4. ANNUAL MAINTENANCE COSTS (Cm): Preventive, corrective, spare parts
5. ANNUAL DOWNTIME COSTS (Cd): Productivity losses, breakdowns
6. RESIDUAL VALUE (Rv): Resale/recovery value at end of life
7. DISPOSAL COST: If Rv is negative

8. ESTIMATED LIFETIME: In years
9. CONFIDENCE LEVEL: "high", "medium", or "low"
10. NOTES: Justification of estimates (respond in {"French" if self._detected_language == "fr" else "English"})

Respond in JSON:
{{
    "estimated_purchase_price": <amount>,
    "implementation_cost": <amount>,
    "annual_operations_cost": <amount>,
    "annual_maintenance_cost": <amount>,
    "annual_downtime_cost": <amount>,
    "resale_value": <amount>,
    "disposal_cost": <amount>,
    "lifetime_years": <number>,
    "confidence": "<high|medium|low>",
    "notes": "<justification>"
}}"""

        machine_type = machine.get('category', '')
        
        # First attempt
        result, json_ok, raw_response = self.call_gemini(base_prompt, retry_strict=False)
        
        if json_ok and result:
            validated, schema_ok = self._validate_machine_estimate(result, machine)
            if schema_ok:
                logger.info("LLM estimation SUCCESS for machine: %s (json_ok=True, schema_ok=True, retry_count=0)", machine_name)
                return validated
            else:
                logger.warning("LLM parse failed for machine %s: schema validation failed, retrying", machine_name)
        else:
            logger.warning("LLM parse failed for machine %s: json_ok=%s, retrying", machine_name, json_ok)
            # Save raw response for debugging
            if raw_response:
                self._save_failed_response(machine_name, raw_response, "machine_attempt_1")
        
        # Retry once with strict prompt
        result, json_ok, raw_response = self.call_gemini(base_prompt, retry_strict=True)
        
        if json_ok and result:
            validated, schema_ok = self._validate_machine_estimate(result, machine)
            if schema_ok:
                logger.info("LLM estimation SUCCESS for machine: %s (json_ok=True, schema_ok=True, retry_count=1)", machine_name)
                return validated
            else:
                logger.warning("LLM retry failed for machine %s: schema validation failed after retry", machine_name)
        else:
            logger.warning("LLM retry failed for machine %s: json_ok=%s after retry", machine_name, json_ok)
            if raw_response:
                self._save_failed_response(machine_name, raw_response, "machine_attempt_2")
        
        # Fallback to heuristics
        logger.warning("Using heuristic fallback for machine: %s (confidence=low, source=heuristic)", machine_name)
        return get_heuristic_machine_estimate(machine_name, machine_type)
    
    def _save_failed_response(self, entity_name: str, raw_response: str, tag: str) -> None:
        """Save failed LLM response for debugging/replay."""
        try:
            debug_dir = Path("data/module_6/debug")
            debug_dir.mkdir(parents=True, exist_ok=True)
            safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', entity_name)[:50]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = debug_dir / f"{tag}_{safe_name}_{timestamp}.txt"
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(raw_response)
            logger.debug("Saved failed LLM response to %s", filepath)
        except Exception as e:
            logger.debug("Could not save failed response: %s", e)

    def estimate_machines_batch(
        self,
        machines: List[Dict[str, Any]],
        suppliers_map: Dict[str, List[Dict[str, Any]]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Estimate TCO for ALL machines in a single LLM call for better performance.
        Returns a dict mapping machine name/id to cost estimates.
        """
        if not machines:
            return {}
        
        suppliers_map = suppliers_map or {}
        
        # Build machines list for prompt
        machines_text = ""
        machine_keys = []
        for i, m in enumerate(machines, 1):
            name = m.get('name', f'Machine_{i}')
            machine_keys.append(name)
            category = m.get('category', 'Industrial Equipment')
            manufacturer = m.get('manufacturer', 'Unknown')
            specs = m.get('original_specs', {})
            if hasattr(specs, 'model_dump'):
                specs = specs.model_dump()
            
            # Get supplier info if available
            supplier_info = ""
            machine_suppliers = suppliers_map.get(name, [])
            if machine_suppliers:
                top = machine_suppliers[0]
                supplier_info = f"Supplier: {top.get('supplier_name', 'N/A')} ({top.get('region', 'N/A')})"
            
            specs_str = f"Capacity: {specs.get('capacite', 'N/A')}, Power: {specs.get('puissance', 'N/A')}"
            machines_text += f"{i}. {name}\n   Category: {category}, Manufacturer: {manufacturer}\n   Specs: {specs_str}\n   {supplier_info}\n\n"
        
        logger.info("Requesting BATCH LLM estimates for %d machines", len(machines))
        
        prompt = f"""Estimate TCO costs for ALL these industrial machines for a SMALL/MID-SIZE Algerian company.

MACHINES LIST:
{machines_text}

CRITICAL PRICE GUIDELINES (DZD) - USE THESE RANGES:
- Small/medium machines: 3,000,000 - 15,000,000 DZD
- Large/specialized machines: 15,000,000 - 35,000,000 DZD
- Production lines (multiple integrated): 25,000,000 - 60,000,000 DZD

COST RATIOS (as % of purchase price):
- implementation_cost: 6-10%
- annual_operations_cost: 5-8%
- annual_maintenance_cost: 3-5%
- annual_downtime_cost: 1-2%
- resale_value: 30-40% at end of life
- disposal_cost: 1-2%
- lifetime_years: 10-12

Return a JSON object with EXACT machine names as keys:
{{
    "Machine Name 1": {{
        "estimated_purchase_price": <number>,
        "implementation_cost": <number>,
        "annual_operations_cost": <number>,
        "annual_maintenance_cost": <number>,
        "annual_downtime_cost": <number>,
        "resale_value": <number>,
        "disposal_cost": <number>,
        "lifetime_years": <number>,
        "confidence": "medium"
    }},
    "Machine Name 2": {{ ... }},
    ...
}}

IMPORTANT: Include ALL {len(machines)} machines. Use EXACT names as keys. All values must be numbers in DZD."""

        # First attempt
        result, json_ok, raw_response = self.call_gemini(prompt)
        
        if json_ok and result and isinstance(result, dict):
            # Validate and normalize
            normalized = {}
            for key, val in result.items():
                validated, is_valid = self._validate_machine_estimate(val, {"name": key})
                if is_valid:
                    normalized[key] = validated
                else:
                    logger.warning("Invalid estimate for machine '%s' in batch, will use heuristic", key)
            
            if len(normalized) >= len(machines) * 0.7:  # At least 70% success
                logger.info("BATCH machine estimation SUCCESS (returned=%d/%d)", len(normalized), len(machines))
                return normalized
        
        if raw_response:
            self._save_failed_response("machines_batch", raw_response, "machines_batch_attempt_1")
        
        # Retry with stricter prompt
        logger.warning("Batch machine estimation incomplete, retrying with strict prompt")
        result, json_ok, raw_response = self.call_gemini(prompt, retry_strict=True)
        
        if json_ok and result and isinstance(result, dict):
            normalized = {}
            for key, val in result.items():
                validated, is_valid = self._validate_machine_estimate(val, {"name": key})
                if is_valid:
                    normalized[key] = validated
            
            if normalized:
                logger.info("BATCH machine estimation SUCCESS on retry (returned=%d/%d)", len(normalized), len(machines))
                return normalized
        
        if raw_response:
            self._save_failed_response("machines_batch", raw_response, "machines_batch_attempt_2")
        
        logger.warning("Batch machine estimation failed, returning empty (will use heuristics)")
        return {}

    def estimate_product_costs(
        self, 
        products: List[Dict[str, Any]], 
        avg_machine_annual: float,
        stage_1: Dict[str, Any] = None,
        stage_3: Dict[str, Any] = None,
    ) -> Dict[str, Dict[str, float]]:
        """
        Estimate product TCO components using LLM for realistic cost estimation.
        Returns a dict mapping product name to cost estimates.
        """
        if not products:
            return {}
        
        # Build product list for prompt
        products_text = ""
        product_names = []
        for i, p in enumerate(products, 1):
            nom = p.get("nom_produit", "Unknown")
            product_names.append(nom)
            categorie = p.get("categorie", "finished")
            quantite = p.get("quantite_annuelle", 0)
            products_text += f"{i}. {nom} (category: {categorie}, annual qty: {quantite})\n"
        
        company_info = ""
        if stage_1:
            info = stage_1.get("informations_generales", {})
            company_info = f"""
Company context:
- Company: {info.get("nom_entreprise", "Unknown")}
- Sector: {info.get("secteur_activite", "Manufacturing")}
- Size: Small to mid-size Algerian company
"""

        prompt = f"""Estimate product handling costs for a small/mid-size Algerian manufacturer:

{products_text}
{company_info}

Reference: Average annual machine TCO is {avg_machine_annual:,.0f} DZD.

CONSERVATIVE COST GUIDELINES (as % of avg_machine_annual):
- landing_cost: 1-3% (import duties, freight)
- holding_cost: 1-2% (storage, warehousing)
- quality_cost: 0.5-1.5% (testing, QC)
- administrative_cost: 0.5-1% (paperwork)

Use CONSERVATIVE estimates (lower end of ranges).

Return JSON with ALL products:
{{
    "Product Name": {{
        "landing_cost": <number>,
        "holding_cost": <number>,
        "quality_cost": <number>,
        "administrative_cost": <number>
    }},
    ...
}}
"""
        
        result, json_ok, _ = self.call_gemini(prompt)
        
        if not json_ok or not result:
            logger.warning("LLM did not return product cost estimates, using conservative defaults")
            # Return conservative defaults based on avg_machine_annual
            return {
                name: {
                    "landing_cost": avg_machine_annual * 0.02,
                    "holding_cost": avg_machine_annual * 0.015,
                    "quality_cost": avg_machine_annual * 0.01,
                    "administrative_cost": avg_machine_annual * 0.008,
                }
                for name in product_names
            }
        
        return result

    def estimate_raw_material_costs(
        self, 
        materials: List[Dict[str, Any]],
        use_llm: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Estimate costs for raw materials from RIBIF stage 2.
        Uses BATCH LLM call for all materials at once for better performance.
        Uses name normalization to match input ↔ output materials.
        """
        if not materials:
            return []
        
        # Build canonical name mapping
        canonical_to_original = {}
        for m in materials:
            nom = m.get("nom_materiau", "Unknown")
            canonical = canonicalize_name(nom)
            canonical_to_original[canonical] = nom
        
        # Get estimates - batch LLM or fallback for all at once
        if use_llm:
            estimates = self._estimate_materials_batch(materials)
        else:
            raise ValueError("LLM estimation disabled; cannot estimate raw materials without explicit inputs.")
        
        # Normalize returned estimate keys
        normalized_estimates = {}
        for key, val in estimates.items():
            canonical_key = canonicalize_name(key)
            normalized_estimates[canonical_key] = val
        
        results = []
        for material in materials:
            nom = material.get("nom_materiau", "Unknown")
            canonical_nom = canonicalize_name(nom)
            type_mat = material.get("type", "")
            quantite_info = material.get("quantite_estimee", {})
            quantite = float(quantite_info.get("valeur", 0) or 0)
            unite = quantite_info.get("unite", "tonnes")
            
            # Estimate quantity if missing or zero
            quantity_estimated = False
            if quantite <= 0:
                # Estimate based on material type - conservative annual consumption
                type_lower = (type_mat or nom).lower()
                if any(kw in type_lower for kw in ["colorant", "additif", "additive", "pigment"]):
                    quantite = 5  # Small quantity additives: 5 tonnes/year
                elif any(kw in type_lower for kw in ["resin", "résine", "epoxy", "specialty"]):
                    quantite = 20  # Specialty materials: 20 tonnes/year
                elif any(kw in type_lower for kw in ["polymer", "plastique", "plastic", "pp", "pe", "pvc", "abs"]):
                    quantite = 100  # Main polymers: 100 tonnes/year
                elif any(kw in type_lower for kw in ["metal", "métal", "steel", "acier", "aluminum"]):
                    quantite = 50  # Metals: 50 tonnes/year
                elif any(kw in type_lower for kw in ["glass", "verre"]):
                    quantite = 30  # Glass: 30 tonnes/year
                else:
                    quantite = 50  # Default: 50 tonnes/year
                quantity_estimated = True
                logger.info("Estimated quantity for material '%s': %.1f %s/year", nom, quantite, unite)
            
            # Look up estimate using canonical name
            estimate = normalized_estimates.get(canonical_nom)
            
            if not estimate:
                # Fallback to heuristics if not found
                logger.warning("No LLM estimate for material '%s' (canonical: '%s'), using heuristic", nom, canonical_nom)
                estimate = get_heuristic_material_estimate(nom)
            else:
                estimate, is_valid = self._validate_material_estimate(estimate, material)
                if not is_valid:
                    logger.warning("Invalid LLM estimate for material '%s', using heuristic", nom)
                    estimate = get_heuristic_material_estimate(nom)
            
            unit_price = float(estimate.get("unit_price"))
            annual_cost = quantite * unit_price
            transport_pct = float(estimate.get("transport_pct"))
            storage_pct = float(estimate.get("storage_pct"))
            wastage_pct = float(estimate.get("wastage_pct"))
            
            transport_cost = annual_cost * transport_pct
            storage_cost = annual_cost * storage_pct
            wastage_cost = annual_cost * wastage_pct
            
            total_tco = annual_cost + transport_cost + storage_cost + wastage_cost
            
            results.append({
                "nom_materiau": nom,
                "type_materiau": type_mat,
                "categorie": material.get("categorie", "Primaire"),
                "quantite_annuelle": quantite,
                "quantite_estimated": quantity_estimated,
                "unite": unite,
                "unit_price": round(unit_price, 2),
                "annual_cost": round(annual_cost, 2),
                "transport_cost": round(transport_cost, 2),
                "storage_cost": round(storage_cost, 2),
                "wastage_cost": round(wastage_cost, 2),
                "total_tco": round(total_tco, 2),
                "estimation_confidence": "low" if quantity_estimated else estimate.get("confidence", "medium"),
                "estimation_source": estimate.get("source", "llm"),
                "estimation_notes": ("Quantity estimated based on material type. " if quantity_estimated else "") + estimate.get("notes", "")
            })
        
        return results

    def _estimate_materials_batch(self, materials: List[Dict]) -> Dict[str, Dict]:
        """
        Estimate all raw material prices in a single LLM call for performance.
        Uses name normalization for matching.
        """
        if not materials:
            return {}
        
        # Build materials list for prompt
        materials_text = ""
        material_names = []
        canonical_to_original = {}
        for i, m in enumerate(materials, 1):
            nom = m.get("nom_materiau", "Unknown")
            canonical = canonicalize_name(nom)
            material_names.append(nom)
            canonical_to_original[canonical] = nom
            type_mat = m.get("type", "")
            quantite_info = m.get("quantite_estimee", {})
            quantite = quantite_info.get("valeur", 0)
            unite = quantite_info.get("unite", "tonnes")
            specs = m.get("specifications", "")
            materials_text += f"{i}. {nom} ({type_mat}) - {quantite} {unite}/year - {specs}\n"
        
        logger.info("Requesting LLM estimates for %d materials", len(material_names))
        
        prompt = f"""Estimate purchase prices for ALL these raw materials for industry in Algeria:

MATERIALS LIST:
{materials_text}

CONSERVATIVE PRICE GUIDELINES (DZD per tonne, CIF Algeria):
- Standard polymers (PP, PE, PVC): 150,000 - 200,000 DZD/tonne
- Engineering plastics (ABS, PC, Nylon): 200,000 - 300,000 DZD/tonne
- Specialty resins (epoxy, PU): 250,000 - 400,000 DZD/tonne
- Additives/colorants: 350,000 - 550,000 DZD/tonne
- Glass materials: 150,000 - 300,000 DZD/tonne
- Metal materials: 150,000 - 250,000 DZD/tonne
- Industrial solvents/chemicals: 100,000 - 250,000 DZD/tonne

OVERHEAD RATIOS (as fraction of material cost):
- transport_pct: 0.05 - 0.10 (5-10%)
- storage_pct: 0.01 - 0.03 (1-3%)
- wastage_pct: 0.01 - 0.02 (1-2%)

IMPORTANT: Use CONSERVATIVE estimates (middle-low of ranges). When uncertain, use LOWER values.

For EACH material, provide:
- unit_price: DZD per tonne (use middle of appropriate range)
- transport_pct: fraction 0.05-0.10
- storage_pct: fraction 0.01-0.03
- wastage_pct: fraction 0.01-0.02
- confidence: "medium"

Return JSON with ALL {len(materials)} materials. Use EXACT material names as keys:
{{
    "Material Name": {{"unit_price": <number>, "transport_pct": <0.05-0.10>, "storage_pct": <0.01-0.03>, "wastage_pct": <0.01-0.02>, "confidence": "medium"}},
    ...
}}"""

        # First attempt
        result, json_ok, raw_response = self.call_gemini(prompt)
        
        if json_ok and result and isinstance(result, dict):
            # Normalize returned keys for matching
            normalized_result = {}
            for key, val in result.items():
                normalized_result[canonicalize_name(key)] = val
                # Also keep original key
                normalized_result[key] = val
            
            # Check for missing materials using normalized names
            returned_canonical = set(canonicalize_name(k) for k in result.keys())
            requested_canonical = set(canonicalize_name(n) for n in material_names)
            missing_canonical = requested_canonical - returned_canonical
            
            if missing_canonical:
                # Map back to original names
                missing_original = [canonical_to_original.get(c, c) for c in missing_canonical]
                logger.warning("LLM did not return estimates for %d materials (after normalization): %s", 
                              len(missing_original), missing_original)
                
                # Retry with just the missing materials (max 1 retry)
                retry_materials = [m for m in materials 
                                  if canonicalize_name(m.get("nom_materiau", "")) in missing_canonical]
                if retry_materials:
                    logger.info("Retrying LLM estimation for %d missing materials (reason: missing_materials_after_norm)", 
                               len(retry_materials))
                    retry_result = self._estimate_materials_retry(retry_materials)
                    if retry_result:
                        for key, val in retry_result.items():
                            normalized_result[canonicalize_name(key)] = val
                            normalized_result[key] = val
            
            logger.info("BATCH LLM material estimation SUCCESS (json_ok=True, materials_returned=%d)", len(result))
            return normalized_result
        
        # If first attempt failed, retry once
        if raw_response:
            self._save_failed_response("materials_batch", raw_response, "materials_batch_attempt_1")
        
        logger.warning("Batch material estimation failed (json_ok=%s), retrying with strict prompt", json_ok)
        result, json_ok, raw_response = self.call_gemini(prompt, retry_strict=True)
        
        if json_ok and result and isinstance(result, dict):
            logger.info("BATCH LLM material estimation SUCCESS on retry (json_ok=True, materials_returned=%d)", len(result))
            # Normalize keys
            normalized_result = {}
            for key, val in result.items():
                normalized_result[canonicalize_name(key)] = val
                normalized_result[key] = val
            return normalized_result
        
        if raw_response:
            self._save_failed_response("materials_batch", raw_response, "materials_batch_attempt_2")
        
        # All attempts failed - return empty, let caller use heuristics
        logger.error("Batch material estimation failed after retry, will use heuristics")
        return {}

    def _estimate_materials_retry(self, materials: List[Dict]) -> Dict[str, Dict]:
        """Retry estimation for individual materials that failed in batch (max 1 retry)."""
        if not materials:
            return {}
        
        # Build a simpler batch prompt for missing materials
        materials_text = ""
        for i, m in enumerate(materials, 1):
            nom = m.get("nom_materiau", "Unknown")
            type_mat = m.get("type", "")
            quantite_info = m.get("quantite_estimee", {})
            quantite = quantite_info.get("valeur", 0)
            unite = quantite_info.get("unite", "tonnes")
            materials_text += f"{i}. {nom} ({type_mat}) - {quantite} {unite}/year\n"
        
        prompt = f"""Estimate purchase prices for these raw materials for industry in Algeria:

{materials_text}

RAW MATERIAL PRICE GUIDELINES (DZD per tonne, CIF Algeria):
- Standard polymers (PP, PE, PVC): 180,000 - 280,000 DZD/tonne
- Engineering plastics (ABS, PC): 280,000 - 400,000 DZD/tonne
- Specialty resins (epoxy, PU): 350,000 - 550,000 DZD/tonne
- Additives/colorants: 400,000 - 800,000 DZD/tonne
- Industrial solvents: 150,000 - 300,000 DZD/tonne
- Glass materials: 200,000 - 500,000 DZD/tonne

Return ONLY a JSON object with material names as keys:
{{
    "Material Name": {{"unit_price": <number>, "transport_pct": <0-1>, "storage_pct": <0-1>, "wastage_pct": <0-1>, "confidence": "<high/medium/low>"}},
    ...
}}"""
        
        result, json_ok, raw_response = self.call_gemini(prompt, retry_strict=True)
        
        if json_ok and result and isinstance(result, dict):
            logger.info("Retry estimation SUCCESS for %d missing materials", len(result))
            return result
        
        if raw_response:
            self._save_failed_response("materials_retry", raw_response, "materials_retry")
        
        logger.warning("Retry estimation failed for missing materials")
        return {}

    def _validate_material_estimate(self, result: Dict, material: Dict) -> Tuple[Dict, bool]:
        """
        Validate material estimate.
        Returns (validated_dict, is_valid) tuple.
        """
        required_keys = ["unit_price", "transport_pct", "storage_pct", "wastage_pct"]
        
        for key in required_keys:
            val = result.get(key)
            if val is None or val == "":
                return result, False
            try:
                float(val)
            except (TypeError, ValueError):
                return result, False

        return {
            "unit_price": result.get("unit_price"),
            "transport_pct": result.get("transport_pct"),
            "storage_pct": result.get("storage_pct"),
            "wastage_pct": result.get("wastage_pct"),
            "confidence": result.get("confidence", "medium"),
            "source": result.get("source", "llm"),
            "notes": result.get("notes", self._get_note("validated_material"))
        }, True

    def calculate_machine_tco(
        self,
        machine_input: Dict[str, Any],
        suppliers: List[Dict[str, Any]],
        use_llm: bool = True,
        precomputed_estimate: Dict[str, Any] = None
    ) -> MachineTCO:
        """
        Calculate TCO for a single machine from RIBIF input.
        
        Args:
            machine_input: Machine specification dict
            suppliers: List of supplier info dicts
            use_llm: Whether to call LLM for estimation (ignored if precomputed_estimate provided)
            precomputed_estimate: Pre-computed estimate dict (from batch call)
        """
        if precomputed_estimate:
            estimates = precomputed_estimate
        else:
            estimates = self.estimate_machine_tco(machine_input, suppliers, use_llm=use_llm)
        
        # Convert all values to float to handle LLM returning strings
        purchase_price = float(estimates["estimated_purchase_price"])
        implementation_cost = float(estimates["implementation_cost"])
        lifetime_years = int(estimates["lifetime_years"])
        
        annual_operations = float(estimates["annual_operations_cost"])
        annual_maintenance = float(estimates["annual_maintenance_cost"])
        annual_downtime = float(estimates["annual_downtime_cost"])
        
        resale_value = float(estimates["resale_value"])
        disposal_cost = float(estimates["disposal_cost"])
        
        initial_cost = purchase_price + implementation_cost
        total_operations = annual_operations * lifetime_years
        total_maintenance = annual_maintenance * lifetime_years
        total_downtime = annual_downtime * lifetime_years + disposal_cost
        
        total_tco = initial_cost + total_operations + total_maintenance + total_downtime - resale_value
        annual_tco = total_tco / lifetime_years if lifetime_years > 0 else total_tco
        
        total_costs = initial_cost + total_operations + total_maintenance + total_downtime
        cost_breakdown = CostBreakdown(
            initial_pct=round((initial_cost / total_costs * 100) if total_costs > 0 else 0, 2),
            operations_pct=round((total_operations / total_costs * 100) if total_costs > 0 else 0, 2),
            maintenance_pct=round((total_maintenance / total_costs * 100) if total_costs > 0 else 0, 2),
            downtime_pct=round((total_downtime / total_costs * 100) if total_costs > 0 else 0, 2),
            resale_offset_pct=round((resale_value / total_costs * 100) if total_costs > 0 else 0, 2)
        )
        
        return MachineTCO(
            machine_id=machine_input.get('id', 'unknown'),
            machine_name=machine_input.get('name', 'Unknown Machine'),
            category=machine_input.get('category', 'equipment'),
            manufacturer=machine_input.get('manufacturer', 'Unknown'),
            initial_cost=round(initial_cost, 2),
            operations_cost=round(total_operations, 2),
            maintenance_cost=round(total_maintenance, 2),
            downtime_cost=round(total_downtime, 2),
            resale_value=round(resale_value, 2),
            total_tco=round(total_tco, 2),
            annual_tco=round(annual_tco, 2),
            lifetime_years=lifetime_years,
            cost_breakdown=cost_breakdown,
            estimated_purchase_price=round(purchase_price, 2),
            estimation_confidence=estimates.get("confidence", "medium"),
            estimation_source=estimates.get("source", "llm"),
            estimation_notes=estimates.get("notes", "")
        )

    def calculate_product_tco(
        self,
        product: Dict[str, Any],
        machine_tco: MachineTCO
    ) -> ProductTCO:
        """
        Calculate TCO for a product category from RIBIF stage 3.
        """
        machine_summary = {
            "machine_name": machine_tco.machine_name,
            "total_tco": machine_tco.total_tco,
            "annual_tco": machine_tco.annual_tco
        }
        
        estimates = self.estimate_product_costs(product, machine_summary)
        
        # Convert to float to handle potential string values
        landing_cost = float(estimates.get("landing_cost", 0) or 0)
        holding_cost = float(estimates.get("holding_cost", 0) or 0)
        quality_cost = float(estimates.get("quality_cost", 0) or 0)
        administrative_cost = float(estimates.get("administrative_cost", 0) or 0)
        
        total_tco = landing_cost + holding_cost + quality_cost + administrative_cost
        
        return ProductTCO(
            nom_produit=product.get("nom_produit", "Unknown"),
            categorie=product.get("categorie"),
            landing_cost=round(landing_cost, 2),
            holding_cost=round(holding_cost, 2),
            quality_cost=round(quality_cost, 2),
            administrative_cost=round(administrative_cost, 2),
            total_tco=round(total_tco, 2)
        )

    def calculate_annual_tco(
        self,
        machine_tcos: List[MachineTCO],
        product_tcos: List[ProductTCO],
        raw_material_tcos: List[RawMaterialTCO] = None,
        years: int = 5
    ) -> List[AnnualTCOBreakdown]:
        """
        Calculate annual TCO breakdown over project lifetime.
        """
        annual_breakdowns = []
        cumulative = 0
        
        total_annual_machines = sum(m.annual_tco for m in machine_tcos)
        total_annual_products = sum(p.total_tco for p in product_tcos)
        total_annual_materials = sum(m.total_tco for m in (raw_material_tcos or []))
        
        for year in range(1, years + 1):
            inflation_factor = 1.07 ** (year - 1)
            
            machines_tco = total_annual_machines * inflation_factor
            products_tco = total_annual_products * inflation_factor
            materials_tco = total_annual_materials * inflation_factor
            total = machines_tco + products_tco + materials_tco
            cumulative += total
            
            annual_breakdowns.append(AnnualTCOBreakdown(
                year=year,
                machines_tco=round(machines_tco, 2),
                products_tco=round(products_tco, 2),
                raw_materials_tco=round(materials_tco, 2),
                total_tco=round(total, 2),
                cumulative_tco=round(cumulative, 2)
            ))
        
        return annual_breakdowns

    def _extract_ribif_info(self, input_data: TCOCalculationInput) -> Dict[str, Any]:
        """Extract company and project info from RIBIF stages."""
        stage_1 = input_data.stage_1_informations_generales or {}
        info_generales = stage_1.get("informations_generales", {})
        
        return {
            "company_name": info_generales.get("nom_entreprise", "Unknown Company"),
            "project_name": info_generales.get("nom_projet", "Unknown Project"),
            "sector": info_generales.get("secteur_activite", ""),
            "description": info_generales.get("description_projet", ""),
            "objectives": info_generales.get("objectifs_strategiques", [])
        }

    def _get_products_from_ribif(self, input_data: TCOCalculationInput) -> List[Dict[str, Any]]:
        """Extract products from RIBIF stage 3."""
        stage_3 = input_data.stage_3_produits_fabriques or {}
        return stage_3.get("produits_fabriques", [])

    def _get_raw_materials_from_ribif(self, input_data: TCOCalculationInput) -> List[Dict[str, Any]]:
        """Extract raw materials from RIBIF stage 2."""
        stage_2 = input_data.stage_2_matieres_premieres or {}
        return stage_2.get("matieres_premieres", [])

    def _build_output_stages(self, input_data: TCOCalculationInput) -> Dict[str, Dict[str, Any]]:
        """Build simplified RIBIF stages for output passthrough."""
        stage_1 = input_data.stage_1_informations_generales or {}
        info_gen = stage_1.get("informations_generales", {})
        stage_1_output = {
            "informations_generales": {
                "nom_projet": info_gen.get("nom_projet", ""),
                "nom_entreprise": info_gen.get("nom_entreprise", ""),
                "secteur_activite": info_gen.get("secteur_activite", ""),
                "description_projet": info_gen.get("description_projet", ""),
                "objectifs_strategiques": info_gen.get("objectifs_strategiques", [])
            }
        }
        
        stage_2 = input_data.stage_2_matieres_premieres or {}
        materials = stage_2.get("matieres_premieres", [])
        stage_2_output = {
            "matieres_premieres": [
                {
                    "nom_materiau": m.get("nom_materiau", "Unknown"),
                    "type": m.get("type", ""),
                    "quantite_estimee": m.get("quantite_estimee", {})
                }
                for m in materials[:20]
            ]
        }
        
        stage_3 = input_data.stage_3_produits_fabriques or {}
        products = stage_3.get("produits_fabriques", [])
        stage_3_output = {
            "produits_fabriques": [
                {"nom_produit": p.get("nom_produit", "Unknown")}
                for p in products[:10]
            ]
        }
        
        stage_6 = input_data.stage_6_informations_complementaires or {}
        aspects = stage_6.get("aspects_reglementaires", {})
        stage_6_output = {
            "aspects_reglementaires": {
                "certifications": aspects.get("certifications", [])
            }
        }
        
        return {
            "stage_1": stage_1_output,
            "stage_2": stage_2_output,
            "stage_3": stage_3_output,
            "stage_6": stage_6_output
        }

    def calculate_tco(self, input_data: TCOCalculationInput, use_llm: bool = True) -> TCOCalculationOutput:
        """
        Main TCO calculation function for RIBIF input.
        
        Args:
            input_data: Combined RIBIF data with machine and suppliers
            use_llm: Whether to use LLM for estimations
            
        Returns:
            Complete TCO calculation output
        """
        # Detect input language for matching output
        self.detect_language(input_data.model_dump())
        
        ribif_info = self._extract_ribif_info(input_data)
        
        machine_dict = input_data.machine_input.model_dump()
        suppliers_list = [s.model_dump() for s in input_data.suppliers]
        
        machine_tco = self.calculate_machine_tco(machine_dict, suppliers_list, use_llm=use_llm)
        machine_tcos = [machine_tco]
        total_machines_tco = sum(m.total_tco for m in machine_tcos)
        
        products = self._get_products_from_ribif(input_data)
        product_tcos = []
        
        if not products:
            raise ValueError("No products found in input; cannot compute product TCO or revenue metrics.")

        for product in products[:5]:
            product_tco = self.calculate_product_tco(product, machine_tco)
            product_tcos.append(product_tco)
        
        total_products_tco = sum(p.total_tco for p in product_tcos)
        
        raw_materials = self._get_raw_materials_from_ribif(input_data)
        raw_material_tco_list = []
        total_raw_materials_tco = 0.0
        
        if raw_materials:
            material_estimates = self.estimate_raw_material_costs(raw_materials, use_llm=use_llm)
            
            for estimate in material_estimates:
                raw_material_tco_list.append(RawMaterialTCO(**estimate))
            
            total_raw_materials_tco = sum(m.total_tco for m in raw_material_tco_list)
        
        annual_tco = self.calculate_annual_tco(machine_tcos, product_tcos, raw_material_tco_list, years=5)
        
        total_tco = total_machines_tco + (total_products_tco * 5) + (total_raw_materials_tco * 5)
        average_annual_tco = total_tco / 5
        
        estimated_revenue = None
        if input_data.ribif_metadata and isinstance(input_data.ribif_metadata, dict):
            estimated_revenue = input_data.ribif_metadata.get("estimated_revenue")
        if not estimated_revenue:
            estimated_revenue = input_data.estimated_revenue
        if not estimated_revenue or estimated_revenue <= 0:
            raise ValueError("Missing estimated_revenue; cannot compute tco_per_unit_revenue without real revenue input.")
        tco_per_unit_revenue = total_tco / float(estimated_revenue)
        
        output_stages = self._build_output_stages(input_data)
        
        return TCOCalculationOutput(
            company_name=ribif_info["company_name"],
            project_name=ribif_info["project_name"],
            calculation_date=date.today(),
            total_tco=round(total_tco, 2),
            average_annual_tco=round(average_annual_tco, 2),
            tco_per_unit_revenue=round(tco_per_unit_revenue, 4),
            machine_tco=machine_tcos,
            total_machines_tco=round(total_machines_tco, 2),
            product_tco=product_tcos,
            total_products_tco=round(total_products_tco, 2),
            raw_materials_tco=raw_material_tco_list,
            total_raw_materials_tco=round(total_raw_materials_tco, 2),
            annual_tco=annual_tco,
            stage_1_informations_generales=output_stages["stage_1"],
            stage_2_matieres_premieres=output_stages["stage_2"],
            stage_3_produits_fabriques=output_stages["stage_3"],
            stage_6_informations_complementaires=output_stages["stage_6"]
        )

    def process_input(self, input_data: Dict, output_dir: str = "data") -> Dict:
        """
        Process RIBIF input and return structured TCO calculation.
        
        Args:
            input_data: Dictionary with RIBIF input data
            output_dir: Directory to save output JSON
            
        Returns:
            TCO calculation result as dictionary
        """
        try:
            tco_input = TCOCalculationInput(**input_data)
        except Exception as e:
            return {"error": f"Invalid input format: {e}"}
        
        try:
            result = self.calculate_tco(tco_input)
        except Exception as e:
            return {"error": f"TCO calculation failed: {e}"}

        result_dict = result.model_dump()
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        json_file = output_path / f"tco_calculation_{date.today()}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(result_dict, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info("TCO calculation saved: %s", json_file)
        return result_dict


# ===== Example usage =====
# calculator = RIBIFModule6TCO()
# result = calculator.process_input(input_data)
# print(json.dumps(result, indent=2, ensure_ascii=False))
