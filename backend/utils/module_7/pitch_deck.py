"""
RIBIF Module 8: Pitch Deck Generator
Generates investor pitch decks using Presenton API (v3).
Uses same input structure as Module 7 (Business Plan).

Output: PDF presentation file via Presenton cloud API.
"""

import os
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from utils.logger import get_logger

logger = get_logger(__name__)

# ============================================
# PYDANTIC MODELS (same as Module 7)
# ============================================

class PitchDeckInput(BaseModel):
    """Input for pitch deck - uses same structure as BusinessPlanInput"""
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
    stage_4_machines_equipements: Optional[Dict[str, Any]] = None
    stage_5_processus_production: Optional[Dict[str, Any]] = None
    stage_6_informations_complementaires: Optional[Dict[str, Any]] = None
    
    # Presenter info (optional)
    presenter_name: str = ""
    presenter_title: str = ""


class PitchDeckOutput(BaseModel):
    """Output from pitch deck generation"""
    # PDF file (primary)
    filename: str
    filepath: str
    format: str = "pdf"
    size_bytes: int = 0
    # PDF file (duplicate for compatibility)
    pdf_filename: str = ""
    pdf_filepath: str = ""
    pdf_size_bytes: int = 0
    # Common
    created_at: str
    project_name: str
    company_name: str
    presentation_id: str = ""
    edit_url: str = ""
    download_url: str = ""
    pdf_download_url: str = ""
    n_slides: int = 10
    credits_consumed: int = 0


# ============================================
# MODULE CLASS
# ============================================

class RIBIFModule8PitchDeck:
    """
    Pitch Deck Generator Module for RIBIF.
    Uses Presenton API (Docker port 5001) for presentation generation.
    Uses same input structure as Module 7 (Business Plan).
    """
    
    FRENCH_KEYWORDS = [
        "projet", "entreprise", "investissement", "matériau", "machine",
        "fabrication", "production", "algérie", "industriel", "polymère",
        "équipement", "secteur", "année", "coût", "revenu"
    ]
    
    def __init__(self):
        load_dotenv()
        self.presenton_url = os.getenv("PRESENTON_API_BASE_URL", "https://api.presenton.ai")
        self.presenton_api_key = os.getenv("PRESENTON_API_KEY", "").strip()
        self._detected_language = "en"
        logger.info("Presenton API configured at: %s", self.presenton_url)

    def detect_language(self, data: Dict[str, Any]) -> str:
        """Detect input language (French/English)."""
        # Check for French field names
        data_str = str(data).lower()
        french_indicators = [
            "stage_1_informations_generales", "matieres_premieres",
            "produits_fabriques", "nom_projet", "nom_entreprise",
            "secteur_activite", "description_projet"
        ]
        french_count = sum(1 for ind in french_indicators if ind in data_str)
        
        # Check description for French words  
        stage_1 = data.get("stage_1_informations_generales", {})
        info_gen = stage_1.get("informations_generales", {})
        description = info_gen.get("description_projet", "")
        
        if description:
            french_words = ["le", "la", "les", "une", "des", "pour", "dans", "avec", "projet", "entreprise"]
            desc_words = description.lower().split()
            if sum(1 for w in desc_words if w in french_words) > 3:
                self._detected_language = "fr"
                return "French"
        
        if french_count >= 3:
            self._detected_language = "fr"
            return "French"
        
        self._detected_language = "en"
        return "English"

    def format_currency(self, amount: float) -> str:
        """Format number as currency."""
        if amount >= 1_000_000_000:
            return f"{amount / 1_000_000_000:.1f}B DZD"
        elif amount >= 1_000_000:
            return f"{amount / 1_000_000:.1f}M DZD"
        elif amount >= 1_000:
            return f"{amount / 1_000:.0f}K DZD"
        return f"{amount:.0f} DZD"

    def build_pitch_content(self, input_data: PitchDeckInput) -> str:
        """Build 10-slide pitch narrative from input data."""
        is_french = self._detected_language == "fr"

        if not input_data.project_name or not input_data.company_name:
            raise ValueError("Missing required project or company name for pitch deck content.")
        if input_data.total_tco <= 0 or input_data.average_annual_tco <= 0:
            raise ValueError("Missing or invalid TCO inputs; cannot build pitch content without real data.")
        
        # Extract data from stages
        stage_1 = input_data.stage_1_informations_generales or {}
        info_gen = stage_1.get("informations_generales", {})
        stage_3 = input_data.stage_3_produits_fabriques or {}
        stage_4 = input_data.stage_4_machines_equipements or {}
        stage_5 = input_data.stage_5_processus_production or {}
        stage_6 = input_data.stage_6_informations_complementaires or {}
        
        # Core info
        company = input_data.company_name
        project = input_data.project_name
        sector = info_gen.get("secteur_activite", "industrie" if is_french else "manufacturing")
        description = info_gen.get("description_projet", "")
        objectives = info_gen.get("objectifs_strategiques", [])
        
        # Products
        products = stage_3.get("produits_fabriques", [])
        product_names = [p.get("nom_produit", "") for p in products if p.get("nom_produit")]
        
        # Machines
        machines = stage_4.get("machines_production", [])
        machine_names = [m.get("nom_machine", "") for m in machines if m.get("nom_machine")]
        
        # Processes
        processes = stage_5.get("processus_production", [])
        process_names = [p.get("nom_etape", "") for p in processes if p.get("nom_etape")]
        
        # Regulatory
        reglementaires = stage_6.get("aspects_reglementaires", {})
        certifications = reglementaires.get("certifications", [])
        
        # TCO data
        total_tco = input_data.total_tco
        avg_annual_tco = input_data.average_annual_tco
        
        def ensure_length(text: str, min_len: int = 100, max_len: int = 300) -> str:
            """Ensure text meets Presenton length requirements."""
            text = text.strip()
            if len(text) < min_len:
                padding = " Notre projet s'inscrit dans une vision stratégique de développement industriel local avec un fort potentiel de croissance." if is_french else " This project aligns with a strategic vision for local industrial development with strong growth potential."
                text = text + padding
            if len(text) > max_len:
                text = text[:max_len-3] + "..."
            return text
        
        # SLIDE 1: Title
        tagline = description[:60] if description else f"{'Complexe industriel innovant' if is_french else 'Innovative industrial complex'} - {sector}"
        presenter = f"{input_data.presenter_name}, {input_data.presenter_title}" if input_data.presenter_name else ("Équipe de Direction" if is_french else "Management Team")
        slide_1 = ensure_length(f"{company}. {tagline}. {'Présenté par' if is_french else 'Presented by'} {presenter}.")
        
        # SLIDE 2: The Problem
        if is_french:
            pain = f"Le marché {sector} souffre d'un manque de production locale de qualité"
            reality = "Alternatives importées onéreuses et délais de livraison longs"
            impact = f"Investissement de {self.format_currency(total_tco)} pour combler ce déficit"
            slide_2 = ensure_length(f"Le Problème. {pain}. Réalité actuelle : {reality}. Impact économique : {impact}.")
        else:
            pain = f"The {sector} market suffers from lack of quality local production"
            reality = "Expensive imported alternatives and long delivery times"
            impact = f"Investment of {self.format_currency(total_tco)} to bridge this gap"
            slide_2 = ensure_length(f"The Problem. {pain}. Current reality: {reality}. Economic impact: {impact}.")
        
        # SLIDE 3: The Solution
        if product_names:
            products_text = ", ".join(product_names[:4])
            solution = f"{'Nous fabriquons localement' if is_french else 'We manufacture locally'}: {products_text}"
        else:
            solution = f"{'Production locale de haute qualité dans le secteur' if is_french else 'High-quality local production in the'} {sector}"
        
        value_prop = ", ".join(str(o) for o in objectives[:3]) if objectives else ("Substitution aux importations, création de valeur locale" if is_french else "Import substitution, local value creation")
        benefits = f"{'Réduction des coûts de 30-40%, délais réduits à 2-4 semaines' if is_french else '30-40% cost reduction, lead times reduced to 2-4 weeks'}"
        slide_3 = ensure_length(f"{'Notre Solution' if is_french else 'Our Solution'}. {solution}. {'Proposition de valeur' if is_french else 'Value proposition'}: {value_prop}. {'Bénéfices' if is_french else 'Benefits'}: {benefits}.")
        
        # SLIDE 4: Market Size
        tam = self.format_currency(total_tco * 20)
        sam = self.format_currency(total_tco * 8)
        som = self.format_currency(total_tco * 2)
        trends = "Politique de substitution aux importations, croissance industrielle" if is_french else "Import substitution policy, industrial growth"
        slide_4 = ensure_length(f"{'Taille du Marché' if is_french else 'Market Size'}. TAM: {tam}. SAM: {sam}. SOM: {som}. {'Pourquoi maintenant' if is_french else 'Why now'}: {trends}.")
        
        # SLIDE 5: The Product
        if machine_names:
            features = f"{'Équipements' if is_french else 'Equipment'}: {', '.join(machine_names[:3])}"
        else:
            features = "Production automatisée de haute précision" if is_french else "Automated high-precision production"
        
        if process_names:
            diff = f"{'Processus intégré' if is_french else 'Integrated process'}: {' → '.join(process_names[:4])}"
        else:
            diff = "Chaîne de production verticalement intégrée" if is_french else "Vertically integrated production chain"
        
        slide_5 = ensure_length(f"{'Notre Production' if is_french else 'Our Production'}. {features}. {diff}. {'Technologie de pointe' if is_french else 'State-of-the-art technology'}.")
        
        # SLIDE 6: Business Model
        revenue_estimate = avg_annual_tco * 1.5 if avg_annual_tco > 0 else total_tco * 0.3
        mrr = revenue_estimate / 12
        slide_6 = ensure_length(f"{'Modèle Économique' if is_french else 'Business Model'}. {'Ventes B2B directes, Contrats industriels' if is_french else 'Direct B2B sales, Industrial contracts'}. {'CA annuel projeté' if is_french else 'Projected annual revenue'}: {self.format_currency(revenue_estimate)}. MRR: {self.format_currency(mrr)}.")
        
        # SLIDE 7: Traction
        if certifications:
            proof = f"{'Certifications visées' if is_french else 'Target certifications'}: {', '.join(certifications[:3])}"
        else:
            proof = "Normes ISO 9001 et ISO 14001 en cours" if is_french else "ISO 9001 and ISO 14001 certification in progress"
        
        roadmap = f"{'Capacité' if is_french else 'Capacity'}: {len(machine_names)} {'machines' if is_french else 'machines'}, {len(product_names)} {'gammes de produits' if is_french else 'product lines'}"
        slide_7 = ensure_length(f"Traction. {proof}. {roadmap}. {'Équipe expérimentée' if is_french else 'Experienced team'}.")
        
        # SLIDE 8: Go-to-Market
        acquisition = "Ventes directes aux industriels, Participation aux salons" if is_french else "Direct industrial sales, Trade fair participation"
        distribution = "Production locale, livraison nationale sous 2 semaines" if is_french else "Local production, nationwide delivery within 2 weeks"
        slide_8 = ensure_length(f"{'Stratégie Commerciale' if is_french else 'Go-to-Market Strategy'}. {acquisition}. {distribution}. {'Cycle de vente B2B 2-4 mois' if is_french else 'B2B sales cycle 2-4 months'}.")
        
        # SLIDE 9: Competition
        competitors = "Importateurs de Chine/Europe, producteurs locaux fragmentés" if is_french else "Importers from China/Europe, fragmented local producers"
        positioning = "Production locale haute qualité à prix compétitif" if is_french else "High-quality local production at competitive prices"
        advantage = "Expertise locale, partenariats technologiques, proximité client" if is_french else "Local expertise, technology partnerships, customer proximity"
        slide_9 = ensure_length(f"{'Concurrence' if is_french else 'Competition'}. {'Face à' if is_french else 'Against'}: {competitors}. Positionnement: {positioning}. {'Avantage' if is_french else 'Advantage'}: {advantage}.")
        
        # SLIDE 10: Closing
        vision = objectives[0] if objectives else (f"Devenir le leader du secteur {sector} en Algérie" if is_french else f"Become the leader in {sector} sector in Algeria")
        slide_10 = ensure_length(f"{'Merci. Merci pour votre attention' if is_french else 'Thank You. Thank you for your attention'}. {'Notre vision' if is_french else 'Our vision'}: {vision}. {'Investissement total' if is_french else 'Total investment'}: {self.format_currency(total_tco)}.")
        
        return f"""
{slide_1}

{slide_2}

{slide_3}

{slide_4}

{slide_5}

{slide_6}

{slide_7}

{slide_8}

{slide_9}

{slide_10}
""".strip()

    def generate_pitch_deck(
        self,
        input_data: PitchDeckInput,
        output_dir: str = "data/7_pitch_deck",
        base_url: str = "http://localhost:5000"
    ) -> PitchDeckOutput:
        """Generate pitch deck using Presenton API."""
        if not self.presenton_api_key:
            raise ValueError("Missing PRESENTON_API_KEY in environment.")
        if not input_data.project_name or not input_data.company_name:
            raise ValueError("Missing required project or company name for pitch deck generation.")
        if input_data.total_tco <= 0 or input_data.average_annual_tco <= 0:
            raise ValueError("Missing or invalid TCO inputs; cannot generate pitch deck without real data.")
        # Detect language
        data_dict = input_data.model_dump()
        language = self.detect_language(data_dict)
        is_french = self._detected_language == "fr"
        
        # Build pitch content
        pitch_content = self.build_pitch_content(input_data)
        logger.info("Built pitch content (%s chars), Language: %s", len(pitch_content), language)
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c if c.isalnum() else "_" for c in input_data.project_name)
        filename = f"PitchDeck_{safe_name}_{timestamp}.pdf"
        filepath = os.path.join(output_dir, filename)
        
        # Build Presenton API request (v3)
        payload = {
            "tone": "default",
            "verbosity": "concise",
            "image_type": "stock",
            "language": "French (Français)" if is_french else "English",
            "export_as": "pdf",
            "content_generation": "condense",
            "theme": "professional-blue",
            "standard_template": "general",
            "instructions": "Research and create and pitch deck on given company",
            "markdown_emphasis": False,
            "include_table_of_contents": False,
            "include_title_slide": True,
            "allow_access_to_user_info": False,
            "content": pitch_content
        }
        
        generate_endpoint = f"{self.presenton_url}/api/v3/presentation/generate"
        
        try:
            logger.info("Calling Presenton API: %s", generate_endpoint)
            logger.info("API Key present: %s", bool(self.presenton_api_key))
            response = requests.post(
                generate_endpoint,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self.presenton_api_key}"
                },
                timeout=180
            )
            
            logger.info("Presenton API response status: %s", response.status_code)
            if response.status_code != 200:
                logger.error("Presenton API error response: %s", response.text[:1000] if response.text else "empty")
                raise Exception(f"Presenton API error ({response.status_code}): {response.text}")
            
            result = response.json()
            logger.info("Presenton response: %s", result)
            
            presentation_id = result.get("presentation_id", "")
            presenton_path = result.get("path", "")
            edit_path = result.get("edit_path", "")
            credits_consumed = int(result.get("credits_consumed", 0) or 0)
            
            # Download the file
            if presenton_path:
                file_url = presenton_path if presenton_path.startswith("http") else f"{self.presenton_url}{presenton_path}"
                logger.info("Downloading from: %s", file_url)
                
                # Don't use Authorization header for S3 pre-signed URLs
                download_headers = {"Accept": "application/pdf"}
                # Only add auth header if it's a Presenton URL, not S3/cloud storage
                if "presenton" in file_url.lower() and "s3" not in file_url.lower() and "amazonaws" not in file_url.lower():
                    download_headers["Authorization"] = f"Bearer {self.presenton_api_key}"
                
                download_response = requests.get(
                    file_url,
                    headers=download_headers,
                    timeout=60
                )
                
                if download_response.status_code == 200:
                    with open(filepath, "wb") as f:
                        f.write(download_response.content)
                    logger.info("Saved to: %s", filepath)
                else:
                    logger.error("Failed to download PDF from Presenton: status=%s, body=%s", download_response.status_code, download_response.text[:500])
            else:
                logger.warning("Presenton API returned empty 'path' - no PDF to download. Full response: %s", result)
            
            # Get PDF file stats
            size_bytes = 0
            if os.path.exists(filepath):
                size_bytes = os.stat(filepath).st_size
            
            pdf_filename = filename
            pdf_filepath = filepath
            pdf_size_bytes = size_bytes
            
            return PitchDeckOutput(
                filename=filename,
                filepath=filepath,
                size_bytes=size_bytes,
                pdf_filename=pdf_filename if pdf_size_bytes > 0 else "",
                pdf_filepath=pdf_filepath if pdf_size_bytes > 0 else "",
                pdf_size_bytes=pdf_size_bytes,
                created_at=datetime.now().isoformat(),
                project_name=input_data.project_name,
                company_name=input_data.company_name,
                presentation_id=presentation_id,
                edit_url=edit_path if edit_path.startswith("http") else f"{self.presenton_url}{edit_path}" if edit_path else "",
                download_url=f"{base_url}/download/{filename}",
                pdf_download_url=f"{base_url}/download/{pdf_filename}" if pdf_size_bytes > 0 else "",
                n_slides=10,
                credits_consumed=credits_consumed
            )
            
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"Cannot connect to Presenton API at {self.presenton_url}."
            )
        except requests.exceptions.Timeout:
            raise TimeoutError(
                "Presenton API request timed out. The presentation generation is taking too long."
            )
