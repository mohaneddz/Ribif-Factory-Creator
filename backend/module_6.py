"""
RIBIF Module 6: TCO (Total Cost of Ownership) Calculation
Consolidated module following ribif_module_1 structure
Uses Gemini API for cost estimations

TCO Formula: TCO = Ci + Co + Cm + Cd - Rv
Where:
- Ci (Initial Costs): Purchase price + implementation
- Co (Operating Costs): Costs to run over lifespan
- Cm (Maintenance Costs): Repairs and upgrades
- Cd (Downtime/Hidden Costs): Productivity loss
- Rv (Residual Value): Resale/salvage value
"""
import os
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import date
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from google import genai
from google.genai import types


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
    """
    
    SYSTEM_PROMPT = """You are an expert in financial analysis and industrial cost estimation in Algeria.
You must estimate the acquisition, operating, maintenance, and disposal costs of industrial equipment.

IMPORTANT ALGERIAN CONTEXT:
- Labor costs: relatively low (average technician salary: 50,000-80,000 DZD/month)
- Energy costs: subsidized electricity (~5 DZD/kWh industrial)
- Spare parts: often imported, 30-50% markup on international prices
- Preventive maintenance: less common, tendency for corrective maintenance
- Exchange rate: consider ~135 DZD for 1 EUR
- Inflation: approximately 7-9% annually
- Logistics costs: high for imports (Algiers port, customs)
- Skilled labor: limited availability, training required
- Equipment lifespan: generally 10-15 years for industrial machines
- Used machines: 40-60% of new price

Respond ONLY with valid JSON containing estimates in DZD."""

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
        load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("❌ Error: GOOGLE_API_KEY not found.")

        self.client = genai.Client(api_key=self.api_key)
        self.model_name = "gemini-2.5-flash"
        self._detected_language = "en"  # Default to English
        print(f"✅ Gemini initialized for TCO Module: {self.model_name}")

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

    def call_gemini(self, prompt: str) -> Dict:
        """
        Call Gemini API and extract JSON from response.
        """
        try:
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
                
                # Strip markdown code fences if present
                if content.startswith("```"):
                    # Remove opening fence (```json or ```)
                    first_newline = content.find('\n')
                    if first_newline != -1:
                        content = content[first_newline + 1:]
                # Remove closing fence if present (may be at end or not)
                if "```" in content:
                    content = content.split("```")[0].strip()
                
                # Debug: Print content after cleanup
                print(f"📄 Content after cleanup (first 150 chars): {content[:150]}")
                
                # Extract JSON from response
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    try:
                        return json.loads(content[json_start:json_end])
                    except json.JSONDecodeError as je:
                        print(f"❌ JSON parse error: {je}")
                        print(f"   Raw content: {content[:300]}")
                else:
                    print(f"❌ No JSON braces found. json_start={json_start}, json_end={json_end}")
                    print(f"   Content: {content[:200]}")
            else:
                if hasattr(response, 'prompt_feedback'):
                    print(f"❌ Response blocked: {response.prompt_feedback}")
                else:
                    print(f"❌ Empty response from Gemini")
            return {}
        except Exception as e:
            print(f"❌ Gemini API Error: {e}")
            return {}

    def _get_defaults_by_capacity(self, capacite: str, manufacturer: str) -> Dict:
        """Get default price estimates based on machine capacity"""
        try:
            numbers = re.findall(r'(\d+)', capacite)
            if len(numbers) >= 2:
                min_cap = int(numbers[0])
                max_cap = int(numbers[1])
                avg_cap = (min_cap + max_cap) / 2
            elif len(numbers) == 1:
                avg_cap = int(numbers[0])
            else:
                avg_cap = 500
        except:
            avg_cap = 500
        
        if avg_cap <= 200:
            price_eur = 200000
        elif avg_cap <= 500:
            price_eur = 400000
        elif avg_cap <= 1000:
            price_eur = 700000
        elif avg_cap <= 2000:
            price_eur = 1200000
        elif avg_cap <= 3000:
            price_eur = 2000000
        else:
            price_eur = 3000000
        
        price_dzd = price_eur * 135
        
        if manufacturer.lower() in ['engel', 'arburg']:
            price_dzd *= 0.95
        elif manufacturer.lower() in ['haitian', 'chen hsong']:
            price_dzd *= 0.60
        
        return {"price": price_dzd}

    def _validate_machine_estimate(self, result: Dict, machine: Dict) -> Dict:
        """Validate required values in the estimate and fail if missing."""
        required_keys = [
            "estimated_purchase_price",
            "implementation_cost",
            "annual_operations_cost",
            "annual_maintenance_cost",
            "annual_downtime_cost",
            "resale_value",
            "disposal_cost",
            "lifetime_years",
            "confidence",
            "notes",
        ]
        missing = [k for k in required_keys if k not in result or result.get(k) is None]
        if missing:
            raise ValueError(
                f"Missing required machine estimate fields {missing} for {machine.get('name', 'Unknown')}"
            )

        return {
            "estimated_purchase_price": result.get("estimated_purchase_price"),
            "implementation_cost": result.get("implementation_cost"),
            "annual_operations_cost": result.get("annual_operations_cost"),
            "annual_maintenance_cost": result.get("annual_maintenance_cost"),
            "annual_downtime_cost": result.get("annual_downtime_cost"),
            "resale_value": result.get("resale_value"),
            "disposal_cost": result.get("disposal_cost"),
            "lifetime_years": result.get("lifetime_years"),
            "confidence": result.get("confidence"),
            "notes": result.get("notes"),
        }

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
        
        prompt = f"""Estimate the complete TCO for this industrial machine in Algeria:

MACHINE: {machine.get('name', 'Unknown')}
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

        try:
            result = self.call_gemini(prompt)
            if result:
                print(f"✅ LLM estimation SUCCESS for machine: {machine.get('name', 'Unknown')}")
                return self._validate_machine_estimate(result, machine)
            raise ValueError(f"Empty LLM response for machine: {machine.get('name', 'Unknown')}")
        except Exception as e:
            raise ValueError(f"LLM estimation failed for machine {machine.get('name', 'Unknown')}: {e}")

    def estimate_product_costs(
        self, 
        product: Dict[str, Any], 
        machine_tco: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Estimate product TCO components.
        """
        raise ValueError("Product TCO estimation requires explicit inputs; fallback estimation is disabled.")

    def estimate_raw_material_costs(
        self, 
        materials: List[Dict[str, Any]],
        use_llm: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Estimate costs for raw materials from RIBIF stage 2.
        Uses BATCH LLM call for all materials at once for better performance.
        """
        if not materials:
            return []
        
        # Get estimates - batch LLM or fallback for all at once
        if use_llm:
            estimates = self._estimate_materials_batch(materials)
        else:
            raise ValueError("LLM estimation disabled; cannot estimate raw materials without explicit inputs.")
        
        results = []
        for material in materials:
            nom = material.get("nom_materiau", "Unknown")
            type_mat = material.get("type", "")
            quantite_info = material.get("quantite_estimee", {})
            quantite = float(quantite_info.get("valeur", 0) or 0)
            unite = quantite_info.get("unite", "tonnes")
            
            # Get estimate for this material (fallback if not in batch result)
            if nom not in estimates:
                raise ValueError(f"Missing LLM estimate for material: {nom}")
            estimate = estimates.get(nom)
            
            estimate = self._validate_material_estimate(estimate, material)
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
                "unite": unite,
                "unit_price": round(unit_price, 2),
                "annual_cost": round(annual_cost, 2),
                "transport_cost": round(transport_cost, 2),
                "storage_cost": round(storage_cost, 2),
                "wastage_cost": round(wastage_cost, 2),
                "total_tco": round(total_tco, 2),
                "estimation_confidence": estimate.get("confidence"),
                "estimation_notes": estimate.get("notes", "")
            })
        
        return results

    def _estimate_materials_batch(self, materials: List[Dict]) -> Dict[str, Dict]:
        """Estimate all raw material prices in a single LLM call for performance"""
        # Build materials list for prompt
        materials_text = ""
        for i, m in enumerate(materials, 1):
            nom = m.get("nom_materiau", "Unknown")
            type_mat = m.get("type", "")
            quantite_info = m.get("quantite_estimee", {})
            quantite = quantite_info.get("valeur", 0)
            unite = quantite_info.get("unite", "tonnes")
            specs = m.get("specifications", "")
            materials_text += f"{i}. {nom} ({type_mat}) - {quantite} {unite}/year - {specs}\n"
        
        prompt = f"""Estimate purchase prices for ALL these raw materials for industry in Algeria:

MATERIALS LIST:
{materials_text}

ALGERIAN CONTEXT:
- Polymers and resins are generally imported (Europe, China, Middle East)
- Exchange rate: ~135 DZD for 1 EUR
- Import/customs fees: 15-30% depending on product
- Maritime + land transport: varies by origin

For EACH material, estimate:
- unit_price: DZD per tonne (CIF Algeria)
- transport_pct: logistics fraction (0-1)
- storage_pct: storage fraction (0-1)  
- wastage_pct: loss fraction (0-1)
- confidence: "high", "medium", or "low"

Respond in JSON with EXACT material names as keys:
{{
    "Polyuréthane (PU)": {{"unit_price": 350000, "transport_pct": 0.15, "storage_pct": 0.03, "wastage_pct": 0.02, "confidence": "medium"}},
    "Résines époxy": {{"unit_price": 280000, "transport_pct": 0.12, "storage_pct": 0.02, "wastage_pct": 0.02, "confidence": "medium"}},
    ...
}}"""

        try:
            result = self.call_gemini(prompt)
            if result and isinstance(result, dict):
                print(f"✅ BATCH LLM estimation SUCCESS for {len(result)} materials")
                return result
            raise ValueError("Empty batch LLM response for materials")
        except Exception as e:
            raise ValueError(f"Batch material estimation failed: {e}")

    def _validate_material_estimate(self, result: Dict, material: Dict) -> Dict:
        """Validate material estimate and fail if missing."""
        required_keys = ["unit_price", "transport_pct", "storage_pct", "wastage_pct"]
        missing = [k for k in required_keys if k not in result or result.get(k) is None]
        if missing:
            raise ValueError(f"Missing material estimate fields {missing} for {material.get('nom_materiau', 'Unknown')}")

        return {
            "unit_price": result.get("unit_price"),
            "transport_pct": result.get("transport_pct"),
            "storage_pct": result.get("storage_pct"),
            "wastage_pct": result.get("wastage_pct"),
            "confidence": result.get("confidence"),
            "notes": result.get("notes", self._get_note("validated_material"))
        }

    def calculate_machine_tco(
        self,
        machine_input: Dict[str, Any],
        suppliers: List[Dict[str, Any]],
        use_llm: bool = True
    ) -> MachineTCO:
        """
        Calculate TCO for a single machine from RIBIF input.
        """
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
            estimation_confidence=estimates.get("confidence"),
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
        
        print(f"✅ TCO calculation saved: {json_file}")
        return result_dict


# ===== Example usage =====
# calculator = RIBIFModule6TCO()
# result = calculator.process_input(input_data)
# print(json.dumps(result, indent=2, ensure_ascii=False))
