"""
RIBIF Module 7: Business Plan Generator
Generates comprehensive 5-year financial business plans with Business Model Canvas.
Uses TCO output from Module 6 as input.

Output: Excel file with multiple sheets including:
- Business Model Canvas (9-block layout)
- Executive Summary
- Investment Details
- Revenue Projections
- Operating Costs
- ROI Analysis
"""

import os
import re
import json
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from enum import Enum

import numpy as np
import numpy_financial as npf
from google import genai
from google.genai import types

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


# ============================================
# PYDANTIC MODELS
# ============================================

class InvestmentCategory(str, Enum):
    EQUIPMENT = "equipment"
    INFRASTRUCTURE = "infrastructure"
    LICENSE = "license"
    VEHICLE = "vehicle"
    OTHER = "other"


class CostCategory(str, Enum):
    RAW_MATERIALS = "raw_materials"
    ENERGY = "energy"
    MAINTENANCE = "maintenance"
    PERSONNEL = "personnel"
    RENT = "rent"
    OTHER = "other"


class DepreciationMethod(str, Enum):
    LINEAR = "linear"
    DEGRESSIVE = "degressive"


class DetailedInvestment(BaseModel):
    category: InvestmentCategory = InvestmentCategory.EQUIPMENT
    name: str
    amount: float = 0
    description: str = ""
    depreciation_years: int = 5
    residual_value: float = 0


class RevenueStream(BaseModel):
    name: str
    initial_amount: float = 0
    growth_rates: List[float] = Field(default_factory=lambda: [0.05] * 5)
    probability: float = 1.0


class DetailedCost(BaseModel):
    name: str
    annual_amount: float = 0
    growth_rate: float = 0.02
    category: CostCategory = CostCategory.OTHER


class FinancialParams(BaseModel):
    discount_rate: float = 0.08
    tax_rate: float = 0.25
    inflation_rate: float = 0.02
    depreciation_method: DepreciationMethod = DepreciationMethod.LINEAR


class BusinessPlanInput(BaseModel):
    """Input for business plan - uses TCO output structure"""
    # Core info
    project_name: str
    company_name: str = "RIBIF Industries"
    
    # From TCO output (Module 6)
    total_tco: float = 0
    average_annual_tco: float = 0
    total_machines_tco: float = 0
    total_products_tco: float = 0
    total_raw_materials_tco: float = 0
    machine_tco: List[Dict[str, Any]] = []
    product_tco: List[Dict[str, Any]] = []
    raw_materials_tco: List[Dict[str, Any]] = []
    annual_tco: List[Dict[str, Any]] = []
    
    # RIBIF stages
    stage_1_informations_generales: Optional[Dict[str, Any]] = None
    stage_2_matieres_premieres: Optional[Dict[str, Any]] = None
    stage_3_produits_fabriques: Optional[Dict[str, Any]] = None
    stage_6_informations_complementaires: Optional[Dict[str, Any]] = None
    
    # Optional overrides
    investments: Dict[str, float] = Field(default_factory=dict)
    detailed_investments: List[DetailedInvestment] = []
    revenue_projections: List[float] = []
    revenue_streams: List[RevenueStream] = []
    operating_costs: Dict[str, float] = Field(default_factory=dict)
    detailed_costs: List[DetailedCost] = []
    financial_params: FinancialParams = Field(default_factory=FinancialParams)


class BusinessPlanOutput(BaseModel):
    """Output from business plan generation"""
    filename: str
    filepath: str
    format: str = "xlsx"
    size_bytes: int = 0
    created_at: str
    project_name: str
    company_name: str
    total_investment_dzd: float
    total_revenue_5y_dzd: float
    npv_dzd: float
    irr_percent: float
    payback_years: float
    sheets: List[str] = []
    download_url: str = ""
    bmc_content: Dict[str, Any] = {}
    capex_data: Dict[str, Any] = {}
    opex_data: Dict[str, Any] = {}
    pricing_data: Dict[str, Any] = {}
    financial_data: Dict[str, Any] = {}


# ============================================
# MODULE CLASS
# ============================================

class RIBIFModule7BusinessPlan:
    """
    Business Plan Generator Module for RIBIF.
    Uses Gemini for AI-generated BMC content with language detection.
    """
    
    FRENCH_KEYWORDS = [
        "projet", "entreprise", "investissement", "matériau", "machine",
        "fabrication", "production", "algérie", "industriel", "polymère",
        "équipement", "secteur", "année", "coût", "revenu"
    ]
    
    SYSTEM_PROMPT = """You are a strategic business consultant expert in Business Model Canvas, 
specialized in the ALGERIAN market. You know:
- Algerian aid programs (ANDI, ANADE, CNAC, ANGEM)
- Algerian banks (BNA, BEA, CPA, BADR, etc.)
- Algerian commercial regulations
- B2B and B2C practices in Algeria
- Challenges and opportunities of the Algerian market
- Industrial zones and economic hubs

Generate personalized BMC adapted to Algerian context.
Respond ONLY with the requested JSON, no explanatory text."""

    def __init__(self, api_key: str = None):
        load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("❌ Error: GOOGLE_API_KEY not found.")
        
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = "gemini-2.5-flash"
        self._detected_language = "en"
        print(f"✅ Gemini initialized for Business Plan Module: {self.model_name}")

    def detect_language(self, text: str) -> str:
        """Detect if the input text is French or English"""
        if not text:
            return "fr"
        text_lower = text.lower()
        french_count = sum(1 for kw in self.FRENCH_KEYWORDS if kw in text_lower)
        if french_count >= 3:
            self._detected_language = "fr"
            return "fr"
        self._detected_language = "en"
        return "en"

    def call_gemini(self, prompt: str) -> Dict:
        """Call Gemini API and extract JSON from response."""
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.SYSTEM_PROMPT,
                    temperature=0.7,
                    top_p=0.95,
                    top_k=64,
                ),
            )
            if hasattr(response, "text") and response.text:
                content = response.text.strip()
                
                # Strip markdown code fences if present
                if content.startswith("```"):
                    first_newline = content.find('\n')
                    if first_newline != -1:
                        content = content[first_newline + 1:]
                if "```" in content:
                    content = content.split("```")[0].strip()
                
                # Extract JSON
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    return json.loads(content[json_start:json_end])
            return {}
        except Exception as e:
            print(f"❌ Gemini API Error: {e}")
            return {}

    def generate_business_plan(
        self,
        input_data: BusinessPlanInput,
        output_dir: str = "data/7_business_plan",
        base_url: str = "http://localhost:5000"
    ) -> BusinessPlanOutput:
        """Generate a comprehensive Business Plan Excel file."""
        if xlsxwriter is None:
            raise ImportError("xlsxwriter is required. Install with: pip install xlsxwriter")

        if not input_data.project_name or not input_data.company_name:
            raise ValueError("Missing required project or company name for business plan generation.")
        if input_data.total_tco <= 0 or input_data.average_annual_tco <= 0:
            raise ValueError("Missing or invalid TCO inputs; cannot generate business plan without real TCO output.")
        
        # Detect language from input
        stage1 = input_data.stage_1_informations_generales or {}
        info_gen = stage1.get("informations_generales", {})
        combined_text = f"{input_data.project_name} {input_data.company_name} {info_gen.get('description_projet', '')}"
        self.detect_language(combined_text)
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c if c.isalnum() else "_" for c in input_data.project_name)
        filename = f"BusinessPlan_{safe_name}_{timestamp}.xlsx"
        filepath = os.path.join(output_dir, filename)
        
        # Get LLM-based estimations for CapEx, OpEx, and Pricing
        capex_data = self._estimate_capex_with_llm(input_data)
        opex_data = self._estimate_opex_with_llm(input_data)
        pricing_data = self._estimate_pricing_with_llm(input_data)

        if not capex_data or "total_capex" not in capex_data:
            raise ValueError("CapEx estimate missing required 'total_capex'.")
        if not opex_data or "total_annual_opex" not in opex_data:
            raise ValueError("OpEx estimate missing required 'total_annual_opex'.")
        if not pricing_data or ("revenue_projections_5y" not in pricing_data and "total_annual_revenue_year1" not in pricing_data):
            raise ValueError("Pricing estimate missing required revenue projections.")
        
        # Calculate financial data using LLM estimates
        financial_data = self._calculate_financials_with_estimates(input_data, capex_data, opex_data, pricing_data)
        
        # Generate BMC content with LLM (without investment mentions)
        bmc_content = self._generate_bmc_with_llm(input_data, financial_data)
        
        # Create Excel workbook
        workbook = xlsxwriter.Workbook(filepath)
        formats = self._create_formats(workbook)
        
        sheets_created = []
        
        # Add sheets
        self._add_bmc_sheet(workbook, input_data, financial_data, bmc_content, formats)
        sheets_created.append("Business Model Canvas")
        
        self._add_capex_sheet(workbook, input_data, capex_data, formats)
        sheets_created.append("CapEx")
        
        self._add_opex_sheet(workbook, opex_data, formats)
        sheets_created.append("OpEx")
        
        self._add_pricing_sheet(workbook, pricing_data, formats)
        sheets_created.append("Pricing")
        
        self._add_roi_sheet(workbook, financial_data, formats)
        sheets_created.append("Analyse ROI" if self._detected_language == "fr" else "ROI Analysis")
        
        workbook.close()
        
        # Get file stats
        file_stat = os.stat(filepath)
        
        return BusinessPlanOutput(
            filename=filename,
            filepath=filepath,
            size_bytes=file_stat.st_size,
            created_at=datetime.now().isoformat(),
            project_name=input_data.project_name,
            company_name=input_data.company_name,
            total_investment_dzd=financial_data["total_investment"],
            total_revenue_5y_dzd=sum(financial_data["revenues"]),
            npv_dzd=financial_data["npv"],
            irr_percent=financial_data["irr"] * 100,
            payback_years=financial_data["payback"],
            sheets=sheets_created,
            download_url=f"{base_url}/download/{filename}",
            bmc_content=bmc_content,
            capex_data=capex_data,
            opex_data=opex_data,
            pricing_data=pricing_data,
            financial_data=financial_data
        )

    def _calculate_financials_with_estimates(self, input_data: BusinessPlanInput, 
                                               capex_data: Dict, opex_data: Dict, pricing_data: Dict) -> Dict[str, Any]:
        """Calculate all financial projections using LLM-estimated CapEx, OpEx, Pricing."""
        years = 5
        
        # Total investment from LLM CapEx estimate
        if "total_capex" not in capex_data or capex_data.get("total_capex") is None:
            raise ValueError("CapEx estimate missing 'total_capex'.")
        total_investment = float(capex_data.get("total_capex"))
        
        # Revenues from LLM Pricing estimate
        revenues = pricing_data.get("revenue_projections_5y", [])
        if not revenues or len(revenues) < years:
            raise ValueError("Pricing estimate missing 5-year revenue projections.")
        revenues = [float(r) for r in revenues[:years]]
        
        # Operating costs from LLM OpEx estimate
        if "total_annual_opex" not in opex_data or opex_data.get("total_annual_opex") is None:
            raise ValueError("OpEx estimate missing 'total_annual_opex'.")
        base_opex = float(opex_data.get("total_annual_opex"))
        operating_costs = []
        for year in range(years):
            year_cost = base_opex * ((1 + input_data.financial_params.inflation_rate) ** year)
            operating_costs.append(year_cost)

        # Post-LLM clamps: ensure realistic revenue coverage of OpEx and non-negative growth
        min_margin_year1 = 0.15
        min_margin_year5 = 0.25
        if revenues[0] <= 0:
            revenues[0] = max(base_opex * 1.2, 1.0)
        for i in range(1, years):
            if revenues[i] <= 0:
                revenues[i] = revenues[i - 1] * 1.02
        required_rev_year1 = operating_costs[0] / max(1 - min_margin_year1, 0.05)
        required_rev_year5 = operating_costs[-1] / max(1 - min_margin_year5, 0.05)
        scale_factor = max(required_rev_year1 / max(revenues[0], 1.0), required_rev_year5 / max(revenues[-1], 1.0))
        if scale_factor > 1.0:
            revenues = [r * scale_factor for r in revenues]
        
        # Depreciation
        depreciation = self._calculate_depreciation(input_data, years, total_investment)
        
        # P&L calculations
        ebitda = [revenues[i] - operating_costs[i] for i in range(years)]
        ebit = [ebitda[i] - depreciation[i] for i in range(years)]
        tax = [max(0, ebit[i] * input_data.financial_params.tax_rate) for i in range(years)]
        net_income = [ebit[i] - tax[i] for i in range(years)]
        
        # Cash flows
        operating_cf = [net_income[i] + depreciation[i] for i in range(years)]
        cash_flows = [-total_investment] + operating_cf
        
        # NPV and IRR
        discount_rate = input_data.financial_params.discount_rate
        npv = npf.npv(discount_rate, cash_flows)
        
        try:
            irr = npf.irr(cash_flows)
            if np.isnan(irr):
                irr = 0.0
        except:
            irr = 0.0
        
        # Payback period
        cumulative = 0
        payback = float(years)
        for i, cf in enumerate(cash_flows):
            cumulative += cf
            if cumulative >= 0 and payback == years:
                if i > 0:
                    prev = cumulative - cf
                    payback = i - 1 + abs(prev) / cf if cf > 0 else float(i)
                break
        
        return {
            "years": years,
            "total_investment": total_investment,
            "revenues": revenues,
            "operating_costs": operating_costs,
            "depreciation": depreciation,
            "ebitda": ebitda,
            "ebit": ebit,
            "tax": tax,
            "net_income": net_income,
            "cash_flows": cash_flows,
            "npv": float(npv),
            "irr": float(irr),
            "payback": float(payback),
            "discount_rate": discount_rate
        }

    def _calculate_depreciation(self, input_data: BusinessPlanInput, years: int, total_investment: float) -> List[float]:
        """Calculate annual depreciation."""
        total_depreciable = 0
        avg_life = 10
        
        for inv in input_data.detailed_investments:
            if inv.category in [InvestmentCategory.EQUIPMENT, InvestmentCategory.INFRASTRUCTURE]:
                total_depreciable += inv.amount - inv.residual_value
                avg_life = inv.depreciation_years
        
        # Add from machines TCO as depreciable
        if input_data.total_machines_tco and input_data.total_machines_tco > 0:
            total_depreciable += input_data.total_machines_tco * 0.9
        else:
            raise ValueError("Missing total_machines_tco; cannot compute depreciation without real machine TCO.")
        
        if total_depreciable == 0:
            return [0.0] * years
        
        if input_data.financial_params.depreciation_method == DepreciationMethod.LINEAR:
            annual_dep = total_depreciable / avg_life
            return [annual_dep] * min(years, avg_life) + [0.0] * max(0, years - avg_life)
        else:
            rate = 2.0 / avg_life
            remaining = total_depreciable
            depreciation = []
            for _ in range(years):
                dep = remaining * rate
                depreciation.append(dep)
                remaining -= dep
            return depreciation

    def _estimate_capex_with_llm(self, input_data: BusinessPlanInput) -> Dict[str, Any]:
        """Estimate Capital Expenditures using LLM."""
        stage1 = input_data.stage_1_informations_generales or {}
        info_gen = stage1.get("informations_generales", {})
        stage3 = input_data.stage_3_produits_fabriques or {}
        
        secteur = info_gen.get("secteur_activite", "industrie")
        produits = [p.get("nom_produit", "") for p in stage3.get("produits_fabriques", [])]
        machines = [m.get("machine_name", "") for m in input_data.machine_tco]
        
        lang = "French" if self._detected_language == "fr" else "English"
        
        prompt = f"""Estimate Capital Expenditures (CapEx) for this industrial project in ALGERIA.
Respond in {lang}.

**Sector:** {secteur}
**Products:** {', '.join(produits[:5]) if produits else 'Industrial products'}
**Machines (if known):** {', '.join(machines[:5]) if machines else 'To be determined'}

Provide a CapEx breakdown with estimated costs in DZD (Algerian Dinar).
Consider: equipment, infrastructure, vehicles, licenses, working capital.

Respond in JSON:
{{
    "equipment": {{"items": ["machine 1", "machine 2"], "total": <amount in DZD>}},
    "infrastructure": {{"items": ["building", "utilities"], "total": <amount in DZD>}},
    "vehicles": {{"items": ["transport vehicle"], "total": <amount in DZD>}},
    "licenses": {{"items": ["business license", "certifications"], "total": <amount in DZD>}},
    "working_capital": <amount in DZD>,
    "total_capex": <total amount in DZD>,
    "confidence": "high|medium|low"
}}"""

        try:
            result = self.call_gemini(prompt)
            if result:
                print(f"✅ LLM CapEx estimation SUCCESS")
                return result
        except Exception as e:
            print(f"⚠️ CapEx estimation error: {e}")
        
        # Fallback
        return {
            "equipment": {"items": ["Production equipment"], "total": 40000000},
            "infrastructure": {"items": ["Industrial building"], "total": 15000000},
            "vehicles": {"items": ["Delivery vehicle"], "total": 5000000},
            "licenses": {"items": ["Business licenses"], "total": 2000000},
            "working_capital": 8000000,
            "total_capex": 70000000,
            "confidence": "low"
        }

    def _estimate_opex_with_llm(self, input_data: BusinessPlanInput) -> Dict[str, Any]:
        """Estimate Operating Expenses using LLM."""
        stage1 = input_data.stage_1_informations_generales or {}
        info_gen = stage1.get("informations_generales", {})
        stage2 = input_data.stage_2_matieres_premieres or {}
        
        secteur = info_gen.get("secteur_activite", "industrie")
        materials = [m.get("nom_materiau", "") for m in stage2.get("matieres_premieres", [])]
        
        lang = "French" if self._detected_language == "fr" else "English"
        
        prompt = f"""Estimate Annual Operating Expenses (OpEx) for this industrial project in ALGERIA.
Respond in {lang}.

**Sector:** {secteur}
**Raw Materials (if known):** {', '.join(materials[:5]) if materials else 'Industrial raw materials'}

Provide an OpEx breakdown with ANNUAL costs in DZD (Algerian Dinar).
Consider: raw materials, energy, personnel, maintenance, rent, insurance, marketing, administrative.

Respond in JSON:
{{
    "raw_materials": {{"description": "main raw materials", "annual_cost": <amount in DZD>}},
    "energy": {{"description": "electricity, gas, fuel", "annual_cost": <amount in DZD>}},
    "personnel": {{"description": "salaries and benefits", "annual_cost": <amount in DZD>}},
    "maintenance": {{"description": "equipment maintenance", "annual_cost": <amount in DZD>}},
    "rent": {{"description": "facility rent", "annual_cost": <amount in DZD>}},
    "insurance": {{"description": "business insurance", "annual_cost": <amount in DZD>}},
    "marketing": {{"description": "marketing and sales", "annual_cost": <amount in DZD>}},
    "administrative": {{"description": "admin and overhead", "annual_cost": <amount in DZD>}},
    "total_annual_opex": <total annual amount in DZD>,
    "confidence": "high|medium|low"
}}"""

        try:
            result = self.call_gemini(prompt)
            if result:
                print(f"✅ LLM OpEx estimation SUCCESS")
                return result
        except Exception as e:
            print(f"⚠️ OpEx estimation error: {e}")
        
        # Fallback
        return {
            "raw_materials": {"description": "Raw materials", "annual_cost": 15000000},
            "energy": {"description": "Energy costs", "annual_cost": 5000000},
            "personnel": {"description": "Personnel costs", "annual_cost": 12000000},
            "maintenance": {"description": "Maintenance", "annual_cost": 3000000},
            "rent": {"description": "Facility rent", "annual_cost": 4000000},
            "insurance": {"description": "Insurance", "annual_cost": 1000000},
            "marketing": {"description": "Marketing", "annual_cost": 2000000},
            "administrative": {"description": "Administrative", "annual_cost": 3000000},
            "total_annual_opex": 45000000,
            "confidence": "low"
        }

    def _estimate_pricing_with_llm(self, input_data: BusinessPlanInput) -> Dict[str, Any]:
        """Estimate Product Pricing using LLM."""
        stage1 = input_data.stage_1_informations_generales or {}
        info_gen = stage1.get("informations_generales", {})
        stage3 = input_data.stage_3_produits_fabriques or {}
        
        secteur = info_gen.get("secteur_activite", "industrie")
        produits = stage3.get("produits_fabriques", [])
        
        lang = "French" if self._detected_language == "fr" else "English"
        
        products_text = ""
        for i, p in enumerate(produits[:5], 1):
            nom = p.get("nom_produit", f"Product {i}")
            products_text += f"{i}. {nom}\n"
        
        if not products_text:
            products_text = "1. Main industrial product\n"
        
        prompt = f"""Estimate Product Pricing for this industrial project in ALGERIA.
Respond in {lang}.

**Sector:** {secteur}
**Products:**
{products_text}

For each product, estimate:
- Unit price in DZD
- Annual production volume
- Annual revenue projection
- 5-year growth rate

Respond in JSON:
{{
    "products": [
        {{
            "name": "product name",
            "unit_price_dzd": <price>,
            "annual_volume": <units>,
            "annual_revenue": <revenue in DZD>,
            "growth_rate": <fraction 0-1>
        }}
    ],
    "total_annual_revenue_year1": <total in DZD>,
    "revenue_projections_5y": [<year1>, <year2>, <year3>, <year4>, <year5>],
    "pricing_strategy": "description",
    "confidence": "high|medium|low"
}}"""

        try:
            result = self.call_gemini(prompt)
            if result:
                print(f"✅ LLM Pricing estimation SUCCESS")
                return result
        except Exception as e:
            print(f"⚠️ Pricing estimation error: {e}")
        
        # Fallback
        return {
            "products": [{"name": "Main Product", "unit_price_dzd": 50000, "annual_volume": 1000, "annual_revenue": 50000000, "growth_rate": 0.08}],
            "total_annual_revenue_year1": 50000000,
            "revenue_projections_5y": [50000000, 54000000, 58320000, 62986000, 68025000],
            "pricing_strategy": "Cost-plus pricing with market adjustment",
            "confidence": "low"
        }

    def _generate_bmc_with_llm(self, input_data: BusinessPlanInput, financial_data: Dict) -> Dict[str, str]:
        """Generate all BMC sections using Gemini LLM."""
        # Extract context
        stage1 = input_data.stage_1_informations_generales or {}
        info_gen = stage1.get("informations_generales", {})
        stage3 = input_data.stage_3_produits_fabriques or {}
        stage6 = input_data.stage_6_informations_complementaires or {}
        
        projet = info_gen.get("nom_projet", input_data.project_name)
        entreprise = info_gen.get("nom_entreprise", input_data.company_name)
        secteur = info_gen.get("secteur_activite", "industrie")
        description = info_gen.get("description_projet", "")
        objectifs = info_gen.get("objectifs_strategiques", [])
        produits = [p.get("nom_produit", "") for p in stage3.get("produits_fabriques", [])]
        certifications = stage6.get("aspects_reglementaires", {}).get("certifications", [])
        
        lang = "French" if self._detected_language == "fr" else "English"
        
        prompt = f"""Generate a complete Business Model Canvas (BMC) for this project in ALGERIA.
Respond in {lang}.

**Project:** {projet}
**Company:** {entreprise}
**Sector:** {secteur}
**Description:** {description}
**Strategic Objectives:** {', '.join(objectifs) if objectifs else 'Not specified'}
**Products:** {', '.join(produits[:5]) if produits else 'Not specified'}
**Certifications:** {', '.join(certifications) if certifications else 'Not specified'}

Generate JSON with these sections (3-5 bullet points each):
{{
    "partners": ["key partner 1", "key partner 2", ...],
    "activities": ["key activity 1", "key activity 2", ...],
    "resources": ["key resource 1", "key resource 2", ...],
    "value_propositions": ["value prop 1", "value prop 2", ...],
    "relationships": ["relationship type 1", ...],
    "channels": ["channel 1", "channel 2", ...],
    "segments": ["customer segment 1", ...],
    "cost_structure": ["cost type 1", "cost type 2", ...],
    "revenue_streams": ["revenue source 1", ...]
}}

IMPORTANT for Algerian context:
- Mention local partners (ANDI, ANADE, Algerian banks)
- Consider local regulations for {secteur}
- Adapt to local business practices"""

        try:
            result = self.call_gemini(prompt)
            if result:
                print(f"✅ BATCH LLM BMC generation SUCCESS")
                # Format as bullet points
                formatted = {}
                for key, items in result.items():
                    if isinstance(items, list):
                        formatted[key] = "\n".join([f"• {item}" for item in items])
                    else:
                        formatted[key] = str(items)
                return formatted
        except Exception as e:
            print(f"⚠️ BMC generation error: {e}")
        
        # Fallback content
        return self._get_default_bmc_content(input_data, financial_data)

    def _get_default_bmc_content(self, input_data: BusinessPlanInput, financial_data: Dict) -> Dict[str, str]:
        """Generate default BMC content when LLM fails."""
        is_french = self._detected_language == "fr"
        
        if is_french:
            return {
                "partners": "• ANDI (Agence Nationale de Développement de l'Investissement)\n• Banques algériennes (BNA, BEA, CPA)\n• Fournisseurs locaux certifiés\n• Chambre de Commerce et d'Industrie",
                "activities": "• Opérations de production\n• Gestion de la qualité\n• Développement commercial\n• Relations administratives",
                "resources": "• Capital d'investissement\n• Équipe locale qualifiée\n• Équipements et installations\n• Licences et autorisations",
                "value_propositions": "• Qualité locale compétitive\n• Prix en DZD\n• Service après-vente de proximité\n• Made in Algeria",
                "relationships": "• Accompagnement personnalisé\n• Support technique local\n• Service client bilingue",
                "channels": "• Vente directe\n• Distributeurs régionaux\n• Plateformes locales\n• Salons professionnels",
                "segments": "• Entreprises algériennes\n• Secteur public\n• PME/PMI locales\n• Export Maghreb",
                "cost_structure": f"• Investissement initial: {financial_data['total_investment']:,.0f} DZD\n• Coûts opérationnels annuels\n• Amortissement équipements",
                "revenue_streams": f"• Ventes produits principaux\n• Revenus Année 1: {financial_data['revenues'][0]:,.0f} DZD\n• Croissance prévue: 8%/an"
            }
        else:
            return {
                "partners": "• ANDI (National Investment Development Agency)\n• Algerian banks (BNA, BEA, CPA)\n• Certified local suppliers\n• Chamber of Commerce",
                "activities": "• Production operations\n• Quality management\n• Business development\n• Administrative relations",
                "resources": "• Investment capital\n• Qualified local team\n• Equipment and facilities\n• Licenses and permits",
                "value_propositions": "• Competitive local quality\n• Local currency pricing (DZD)\n• Proximity after-sales service\n• Made in Algeria",
                "relationships": "• Personalized support\n• Local technical assistance\n• Bilingual customer service",
                "channels": "• Direct sales\n• Regional distributors\n• Local platforms\n• Trade shows",
                "segments": "• Algerian companies\n• Public sector\n• Local SMEs\n• Maghreb export",
                "cost_structure": f"• Initial investment: {financial_data['total_investment']:,.0f} DZD\n• Annual operating costs\n• Equipment depreciation",
                "revenue_streams": f"• Main product sales\n• Year 1 Revenue: {financial_data['revenues'][0]:,.0f} DZD\n• Projected growth: 8%/year"
            }

    def _create_formats(self, workbook) -> Dict[str, Any]:
        """Create Excel cell formats."""
        formats = {}
        
        formats["title"] = workbook.add_format({
            "bold": True, "font_size": 18, "font_color": "#1F4E79",
            "align": "center", "valign": "vcenter"
        })
        formats["subtitle"] = workbook.add_format({
            "bold": True, "font_size": 14, "font_color": "#2E75B6",
            "align": "center", "valign": "vcenter"
        })
        formats["section_header"] = workbook.add_format({
            "bold": True, "font_size": 12, "bg_color": "#1F4E79",
            "font_color": "white", "align": "center", "valign": "vcenter", "border": 1
        })
        formats["header"] = workbook.add_format({
            "bold": True, "bg_color": "#D6DCE4", "border": 1,
            "align": "center", "valign": "vcenter"
        })
        formats["text"] = workbook.add_format({
            "align": "left", "valign": "vcenter", "text_wrap": True, "border": 1
        })
        formats["number"] = workbook.add_format({
            "num_format": "#,##0", "align": "right", "valign": "vcenter", "border": 1
        })
        formats["currency"] = workbook.add_format({
            "num_format": '#,##0" DZD"', "align": "right", "valign": "vcenter", "border": 1
        })
        formats["percent"] = workbook.add_format({
            "num_format": "0.00%", "align": "right", "valign": "vcenter", "border": 1
        })
        formats["total_label"] = workbook.add_format({
            "bold": True, "bg_color": "#FFC000", "border": 1,
            "align": "left", "valign": "vcenter"
        })
        formats["total_currency"] = workbook.add_format({
            "bold": True, "bg_color": "#FFC000", "num_format": '#,##0" DZD"',
            "align": "right", "valign": "vcenter", "border": 1
        })
        formats["bmc_header"] = workbook.add_format({
            "bold": True, "font_size": 11, "bg_color": "#1F4E79",
            "font_color": "white", "align": "center", "valign": "vcenter",
            "border": 2, "text_wrap": True
        })
        formats["bmc_content"] = workbook.add_format({
            "font_size": 10, "bg_color": "#F2F2F2", "align": "left",
            "valign": "top", "border": 1, "text_wrap": True
        })
        
        return formats

    def _add_bmc_sheet(self, workbook, input_data: BusinessPlanInput, 
                       financial_data: Dict, bmc_content: Dict, formats: Dict):
        """Add Business Model Canvas sheet."""
        sheet = workbook.add_worksheet("Business Model Canvas")
        
        for col in range(7):
            sheet.set_column(col, col, 20)
        
        # Title
        sheet.merge_range(0, 0, 0, 6, f"BUSINESS MODEL CANVAS - {input_data.project_name}", formats["title"])
        sheet.merge_range(1, 0, 1, 6, input_data.company_name, formats["subtitle"])
        
        row = 3
        
        # Headers
        sheet.write(row, 0, "Partenaires Clés" if self._detected_language == "fr" else "Key Partners", formats["bmc_header"])
        sheet.write(row, 1, "Activités Clés" if self._detected_language == "fr" else "Key Activities", formats["bmc_header"])
        sheet.merge_range(row, 2, row, 3, "Propositions de Valeur" if self._detected_language == "fr" else "Value Propositions", formats["bmc_header"])
        sheet.write(row, 4, "Relations Clients" if self._detected_language == "fr" else "Customer Relationships", formats["bmc_header"])
        sheet.merge_range(row, 5, row, 6, "Segments Clients" if self._detected_language == "fr" else "Customer Segments", formats["bmc_header"])
        
        row += 1
        
        # Content
        sheet.merge_range(row, 0, row + 3, 0, bmc_content.get("partners", ""), formats["bmc_content"])
        sheet.merge_range(row, 1, row + 1, 1, bmc_content.get("activities", ""), formats["bmc_content"])
        
        sheet.write(row + 2, 1, "Ressources Clés" if self._detected_language == "fr" else "Key Resources", formats["bmc_header"])
        sheet.write(row + 3, 1, bmc_content.get("resources", ""), formats["bmc_content"])
        
        sheet.merge_range(row, 2, row + 3, 3, bmc_content.get("value_propositions", ""), formats["bmc_content"])
        
        sheet.merge_range(row, 4, row + 1, 4, bmc_content.get("relationships", ""), formats["bmc_content"])
        sheet.write(row + 2, 4, "Canaux" if self._detected_language == "fr" else "Channels", formats["bmc_header"])
        sheet.write(row + 3, 4, bmc_content.get("channels", ""), formats["bmc_content"])
        
        sheet.merge_range(row, 5, row + 3, 6, bmc_content.get("segments", ""), formats["bmc_content"])
        
        # Bottom section
        row += 5
        sheet.merge_range(row, 0, row, 3, "Structure de Coûts" if self._detected_language == "fr" else "Cost Structure", formats["bmc_header"])
        sheet.merge_range(row, 4, row, 6, "Flux de Revenus" if self._detected_language == "fr" else "Revenue Streams", formats["bmc_header"])
        
        row += 1
        sheet.merge_range(row, 0, row + 2, 3, bmc_content.get("cost_structure", ""), formats["bmc_content"])
        sheet.merge_range(row, 4, row + 2, 6, bmc_content.get("revenue_streams", ""), formats["bmc_content"])

    def _add_executive_summary_sheet(self, workbook, input_data: BusinessPlanInput, 
                                     financial_data: Dict, formats: Dict):
        """Add Executive Summary sheet."""
        is_fr = self._detected_language == "fr"
        title = "Resume Executif" if is_fr else "Executive Summary"
        sheet = workbook.add_worksheet(title)
        
        sheet.set_column(0, 0, 30)
        sheet.set_column(1, 1, 25)
        
        sheet.merge_range(0, 0, 0, 1, f"{title.upper()} - {input_data.project_name}", formats["title"])
        
        row = 2
        metrics = [
            ("Investissement Total" if is_fr else "Total Investment", financial_data["total_investment"]),
            ("Revenus 5 ans" if is_fr else "5-Year Revenue", sum(financial_data["revenues"])),
            ("VAN (NPV)" if is_fr else "NPV", financial_data["npv"]),
            ("TRI (IRR)", f"{financial_data['irr']*100:.1f}%"),
            ("Période de Récupération" if is_fr else "Payback Period", f"{financial_data['payback']:.1f} {'ans' if is_fr else 'years'}"),
        ]
        
        for label, value in metrics:
            sheet.write(row, 0, label, formats["header"])
            if isinstance(value, (int, float)):
                sheet.write(row, 1, value, formats["currency"])
            else:
                sheet.write(row, 1, value, formats["text"])
            row += 1

    def _add_capex_sheet(self, workbook, input_data: BusinessPlanInput,
                          capex_data: Dict, formats: Dict):
        """Add CapEx sheet with LLM-generated data."""
        is_fr = self._detected_language == "fr"
        sheet = workbook.add_worksheet("CapEx")
        
        sheet.set_column(0, 0, 35)
        sheet.set_column(1, 1, 25)
        
        title = "CAPITAL EXPENDITURES (CapEx)"
        sheet.merge_range(0, 0, 0, 1, title, formats["title"])
        
        row = 2
        sheet.write(row, 0, "Catégorie" if is_fr else "Category", formats["header"])
        sheet.write(row, 1, "Montant (DZD)" if is_fr else "Amount (DZD)", formats["header"])
        row += 1
        
        # Equipment
        equip = capex_data.get("equipment", {})
        sheet.write(row, 0, "Équipements" if is_fr else "Equipment", formats["text"])
        sheet.write(row, 1, float(equip.get("total", 0) or 0), formats["currency"])
        row += 1
        
        # Infrastructure
        infra = capex_data.get("infrastructure", {})
        sheet.write(row, 0, "Infrastructure", formats["text"])
        sheet.write(row, 1, float(infra.get("total", 0) or 0), formats["currency"])
        row += 1
        
        # Vehicles
        vehicles = capex_data.get("vehicles", {})
        sheet.write(row, 0, "Véhicules" if is_fr else "Vehicles", formats["text"])
        sheet.write(row, 1, float(vehicles.get("total", 0) or 0), formats["currency"])
        row += 1
        
        # Licenses
        licenses = capex_data.get("licenses", {})
        sheet.write(row, 0, "Licences", formats["text"])
        sheet.write(row, 1, float(licenses.get("total", 0) or 0), formats["currency"])
        row += 1
        
        # Working capital
        wc = capex_data.get("working_capital", 0)
        sheet.write(row, 0, "Fonds de roulement" if is_fr else "Working Capital", formats["text"])
        sheet.write(row, 1, float(wc or 0), formats["currency"])
        row += 1
        
        # Total
        total = float(capex_data.get("total_capex", 0) or 0)
        sheet.write(row, 0, "TOTAL CAPEX", formats["total_label"])
        sheet.write(row, 1, total, formats["total_currency"])
        
        row += 2
        confidence = capex_data.get("confidence", "medium")
        sheet.write(row, 0, f"Confidence: {confidence}")

    def _add_opex_sheet(self, workbook, opex_data: Dict, formats: Dict):
        """Add OpEx sheet with LLM-generated data."""
        is_fr = self._detected_language == "fr"
        sheet = workbook.add_worksheet("OpEx")
        
        sheet.set_column(0, 0, 35)
        sheet.set_column(1, 1, 25)
        
        title = "OPERATING EXPENSES (OpEx) - " + ("Annuel" if is_fr else "Annual")
        sheet.merge_range(0, 0, 0, 1, title, formats["title"])
        
        row = 2
        sheet.write(row, 0, "Catégorie" if is_fr else "Category", formats["header"])
        sheet.write(row, 1, "Coût Annuel (DZD)" if is_fr else "Annual Cost (DZD)", formats["header"])
        row += 1
        
        categories = [
            ("raw_materials", "Matières Premières" if is_fr else "Raw Materials"),
            ("energy", "Énergie" if is_fr else "Energy"),
            ("personnel", "Personnel"),
            ("maintenance", "Maintenance"),
            ("rent", "Loyer" if is_fr else "Rent"),
            ("insurance", "Assurance" if is_fr else "Insurance"),
            ("marketing", "Marketing"),
            ("administrative", "Administratif" if is_fr else "Administrative")
        ]
        
        for key, label in categories:
            cat_data = opex_data.get(key, {})
            cost = cat_data.get("annual_cost", 0) if isinstance(cat_data, dict) else 0
            sheet.write(row, 0, label, formats["text"])
            sheet.write(row, 1, float(cost or 0), formats["currency"])
            row += 1
        
        # Total
        total = float(opex_data.get("total_annual_opex", 0) or 0)
        sheet.write(row, 0, "TOTAL OPEX ANNUEL" if is_fr else "TOTAL ANNUAL OPEX", formats["total_label"])
        sheet.write(row, 1, total, formats["total_currency"])
        
        row += 2
        confidence = opex_data.get("confidence", "medium")
        sheet.write(row, 0, f"Confidence: {confidence}")

    def _add_pricing_sheet(self, workbook, pricing_data: Dict, formats: Dict):
        """Add Pricing sheet with LLM-generated data."""
        is_fr = self._detected_language == "fr"
        sheet = workbook.add_worksheet("Pricing")
        
        sheet.set_column(0, 0, 30)
        sheet.set_column(1, 1, 18)
        sheet.set_column(2, 2, 15)
        sheet.set_column(3, 3, 20)
        
        title = "STRATÉGIE DE TARIFICATION" if is_fr else "PRICING STRATEGY"
        sheet.merge_range(0, 0, 0, 3, title, formats["title"])
        
        row = 2
        sheet.write(row, 0, "Produit" if is_fr else "Product", formats["header"])
        sheet.write(row, 1, "Prix Unit. (DZD)" if is_fr else "Unit Price (DZD)", formats["header"])
        sheet.write(row, 2, "Volume/An" if is_fr else "Volume/Year", formats["header"])
        sheet.write(row, 3, "CA Annuel (DZD)" if is_fr else "Annual Revenue (DZD)", formats["header"])
        row += 1
        
        products = pricing_data.get("products", [])
        for p in products:
            if isinstance(p, dict):
                sheet.write(row, 0, p.get("name", "Product"), formats["text"])
                sheet.write(row, 1, float(p.get("unit_price_dzd", 0) or 0), formats["currency"])
                sheet.write(row, 2, float(p.get("annual_volume", 0) or 0), formats["number"])
                sheet.write(row, 3, float(p.get("annual_revenue", 0) or 0), formats["currency"])
                row += 1
        
        # Revenue totals
        row += 1
        total_rev = float(pricing_data.get("total_annual_revenue_year1", 0) or 0)
        sheet.write(row, 0, "TOTAL ANNÉE 1" if is_fr else "TOTAL YEAR 1", formats["total_label"])
        sheet.merge_range(row, 1, row, 3, total_rev, formats["total_currency"])
        
        # 5-year projections
        row += 2
        sheet.write(row, 0, "Projections 5 ans" if is_fr else "5-Year Projections", formats["section_header"])
        row += 1
        
        projections = pricing_data.get("revenue_projections_5y", [])
        for i, proj in enumerate(projections[:5], 1):
            sheet.write(row, 0, f"Année {i}" if is_fr else f"Year {i}", formats["text"])
            sheet.write(row, 1, float(proj or 0), formats["currency"])
            row += 1
        
        # Strategy
        row += 1
        strategy = pricing_data.get("pricing_strategy", "")
        sheet.write(row, 0, "Stratégie" if is_fr else "Strategy", formats["header"])
        sheet.merge_range(row, 1, row, 3, strategy, formats["text"])

    def _add_roi_sheet(self, workbook, financial_data: Dict, formats: Dict):
        """Add ROI Analysis sheet."""
        is_fr = self._detected_language == "fr"
        title = "Analyse ROI" if is_fr else "ROI Analysis"
        sheet = workbook.add_worksheet(title)
        
        sheet.set_column(0, 0, 35)
        sheet.set_column(1, 1, 25)
        
        sheet.merge_range(0, 0, 0, 1, title.upper(), formats["title"])
        
        row = 2
        metrics = [
            ("Valeur Actuelle Nette (VAN)" if is_fr else "Net Present Value (NPV)", financial_data["npv"], "currency"),
            ("Taux de Rentabilité Interne (TRI)" if is_fr else "Internal Rate of Return (IRR)", financial_data["irr"], "percent"),
            ("Période de Récupération" if is_fr else "Payback Period", financial_data["payback"], "years"),
            ("Taux d'Actualisation" if is_fr else "Discount Rate", financial_data["discount_rate"], "percent"),
            ("Investissement Total" if is_fr else "Total Investment", financial_data["total_investment"], "currency"),
        ]
        
        for label, value, fmt_type in metrics:
            sheet.write(row, 0, label, formats["header"])
            if fmt_type == "currency":
                sheet.write(row, 1, value, formats["currency"])
            elif fmt_type == "percent":
                sheet.write(row, 1, value, formats["percent"])
            elif fmt_type == "years":
                years_label = "ans" if is_fr else "years"
                sheet.write(row, 1, f"{value:.1f} {years_label}", formats["text"])
            row += 1


# ============================================
# HELPER FUNCTIONS
# ============================================

def _safe_number(value, default=0):
    """Convert value to safe number for Excel."""
    if value is None:
        return default
    try:
        num = float(value)
        if np.isnan(num) or np.isinf(num):
            return default
        return num
    except (TypeError, ValueError):
        return default
