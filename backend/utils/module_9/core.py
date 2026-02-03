"""
RIBIF Module 9: Industrial Technical Catalog Generator
Rewritten to match the new API structure (Gemini via vertex_utils).
Generates PDF and HTML catalogs from Module 1 (and optional Module 4) outputs.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import re
import shutil
import tempfile
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from dotenv import load_dotenv
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph,
        Spacer, PageBreak, Image, Flowable
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    from PIL import Image as PILImage
except Exception as e:  # pragma: no cover - handled at runtime
    raise ImportError(
        "Missing PDF/image dependencies. Install reportlab and pillow."
    ) from e

from vertex_utils import generate_message


# ============================================
# PYDANTIC MODELS
# ============================================

class CatalogInput(BaseModel):
    """Input for catalog generation"""
    module1_data: Dict[str, Any]
    module4_data: Optional[Dict[str, Any]] = None
    images_config: Optional[Dict[str, Any]] = None
    output_dir: str = "data/catalogs"
    output_format: str = "both"  # pdf | html | both
    base_filename: Optional[str] = None
    image_base_path: str = "data"


class CatalogOutput(BaseModel):
    """Output from catalog generation"""
    created_at: str
    project_name: str
    company_name: str
    output_format: str
    pdf_filename: Optional[str] = None
    pdf_filepath: Optional[str] = None
    pdf_size_bytes: Optional[int] = None
    pdf_download_url: Optional[str] = None
    html_filename: Optional[str] = None
    html_filepath: Optional[str] = None
    html_size_bytes: Optional[int] = None
    html_download_url: Optional[str] = None


class ImagePlaceholder(Flowable):
    """Placeholder for missing images in PDF"""
    def __init__(self, width: float, height: float, text: str = "Image Not Available"):
        Flowable.__init__(self)
        self.width = width
        self.height = height
        self.text = text

    def draw(self):
        self.canv.setStrokeColor(colors.HexColor("#cccccc"))
        self.canv.setFillColor(colors.HexColor("#f5f5f5"))
        self.canv.rect(0, 0, self.width, self.height, fill=1)
        self.canv.setFillColor(colors.HexColor("#999999"))
        self.canv.setFont("Helvetica", 10)
        text_width = self.canv.stringWidth(self.text, "Helvetica", 10)
        self.canv.drawString((self.width - text_width) / 2, self.height / 2, self.text)


# ============================================
# MODULE CLASS
# ============================================

class RIBIFModule9Catalog:
    """
    Industrial catalog generator (PDF + HTML) with optional images.
    Uses Gemini (via vertex_utils.generate_message) for narrative content.
    """

    SYSTEM_PROMPT = (
        "You are a professional technical writer for industrial documentation. "
        "Write clear, precise content for technical catalogs."
    )

    def __init__(self, image_base_path: str = "data"):
        load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")
        self.image_base_path = image_base_path
        self.max_image_width = 16 * cm
        self.max_image_height = 12 * cm
        self.styles = getSampleStyleSheet()
        self._create_professional_styles()
        self.chapter_num = 0
        self.figure_num = 0
        self.table_num = 0

    # ==================== STYLES ====================

    def _create_professional_styles(self) -> None:
        self.styles.add(ParagraphStyle(
            name="BookTitle", parent=self.styles["Title"],
            fontSize=28, textColor=colors.HexColor("#1a1a1a"),
            spaceAfter=10, alignment=TA_CENTER, fontName="Helvetica-Bold"
        ))
        self.styles.add(ParagraphStyle(
            name="Subtitle", parent=self.styles["Normal"],
            fontSize=14, textColor=colors.HexColor("#4a4a4a"),
            spaceAfter=20, alignment=TA_CENTER
        ))
        self.styles.add(ParagraphStyle(
            name="ChapterTitle", parent=self.styles["Heading1"],
            fontSize=20, textColor=colors.HexColor("#1a1a1a"),
            spaceAfter=15, spaceBefore=30, fontName="Helvetica-Bold"
        ))
        self.styles.add(ParagraphStyle(
            name="SectionTitle", parent=self.styles["Heading2"],
            fontSize=14, textColor=colors.HexColor("#2a2a2a"),
            spaceAfter=10, spaceBefore=15, fontName="Helvetica-Bold"
        ))
        self.styles.add(ParagraphStyle(
            name="BookBody", parent=self.styles["Normal"],
            fontSize=10, leading=14, alignment=TA_JUSTIFY, spaceAfter=8
        ))
        self.styles.add(ParagraphStyle(
            name="FigureCaption", parent=self.styles["Normal"],
            fontSize=9, textColor=colors.HexColor("#4a4a4a"),
            alignment=TA_CENTER, spaceAfter=15, spaceBefore=5,
            fontName="Helvetica-Oblique"
        ))
        self.styles.add(ParagraphStyle(
            name="TableCaption", parent=self.styles["Normal"],
            fontSize=9, textColor=colors.HexColor("#4a4a4a"),
            alignment=TA_LEFT, spaceBefore=5, fontName="Helvetica-Bold"
        ))

    # ==================== IMAGE HANDLING ====================

    def resolve_image_path(self, image_path: str) -> Optional[str]:
        if not image_path:
            return None
        if os.path.isabs(image_path) and os.path.exists(image_path):
            return image_path
        if os.path.exists(image_path):
            return os.path.abspath(image_path)

        full_path = os.path.join(self.image_base_path, image_path)
        if os.path.exists(full_path):
            return os.path.abspath(full_path)

        subdirs = [
            "machines", "products", "processes", "3d_models", "2d_plans",
            "logos", "covers", "diagrams", "photos"
        ]
        for subdir in subdirs:
            candidate = os.path.join(self.image_base_path, subdir, image_path)
            if os.path.exists(candidate):
                return os.path.abspath(candidate)
            candidate = os.path.join(self.image_base_path, subdir, os.path.basename(image_path))
            if os.path.exists(candidate):
                return os.path.abspath(candidate)
        return None

    def get_image_for_pdf(self, image_path: str, max_width: float = None,
                          max_height: float = None, caption: str = None) -> List:
        elements = []
        max_width = max_width or self.max_image_width
        max_height = max_height or self.max_image_height
        resolved_path = self.resolve_image_path(image_path)

        if resolved_path:
            try:
                with PILImage.open(resolved_path) as img:
                    orig_width, orig_height = img.size
                width_ratio = max_width / orig_width
                height_ratio = max_height / orig_height
                scale = min(width_ratio, height_ratio, 1.0)
                new_width = orig_width * scale
                new_height = orig_height * scale

                rl_image = Image(resolved_path, width=new_width, height=new_height)
                rl_image.hAlign = "CENTER"
                elements.append(rl_image)
            except Exception:
                elements.append(ImagePlaceholder(
                    max_width * 0.5, max_height * 0.3,
                    f"Error: {os.path.basename(image_path)}"
                ))
        else:
            elements.append(ImagePlaceholder(
                max_width * 0.5, max_height * 0.3,
                f"[{os.path.basename(image_path) if image_path else 'No Image'}]"
            ))

        if caption:
            self.figure_num += 1
            elements.append(Paragraph(
                f"Figure {self.figure_num}: {caption}",
                self.styles["FigureCaption"]
            ))
        return elements

    def get_image_as_base64(self, image_path: str) -> Optional[str]:
        resolved_path = self.resolve_image_path(image_path)
        if resolved_path:
            try:
                with open(resolved_path, "rb") as f:
                    img_data = base64.b64encode(f.read()).decode()
                ext = os.path.splitext(resolved_path)[1].lower().strip(".")
                mime_types = {
                    "jpg": "jpeg", "jpeg": "jpeg", "png": "png",
                    "gif": "gif", "webp": "webp", "bmp": "bmp"
                }
                mime = mime_types.get(ext, "jpeg")
                return f"data:image/{mime};base64,{img_data}"
            except Exception:
                return None
        return None

    def get_html_image(self, image_path: str, alt: str = "",
                       css_class: str = "catalog-image") -> str:
        if not image_path:
            return f'<div class="image-placeholder">[{alt or "Image Not Available"}]</div>'
        base64_src = self.get_image_as_base64(image_path)
        if base64_src:
            return f'<img src="{base64_src}" alt="{alt}" class="{css_class}" onclick="openLightbox(this)">'
        return f'<div class="image-placeholder">[{alt or os.path.basename(image_path)}]</div>'

    # ==================== AI CONTENT ====================

    def call_gemini(self, prompt: str, temperature: float = 0.4) -> str:
        try:
            return generate_message(
                prompt=prompt,
                system_instruction=self.SYSTEM_PROMPT,
                temperature=temperature,
                top_p=0.95,
            )
        except Exception:
            return "[Content generation unavailable]"

    def generate_chapter_intro(self, chapter_name: str, context: str, data: Dict) -> str:
        prompt = (
            "Write a professional introduction (2-3 paragraphs) for this catalog chapter.\n\n"
            f"CHAPTER: {chapter_name}\n"
            f"CONTEXT: {context}\n"
            f"DATA: {json.dumps(data, ensure_ascii=False)[:2000]}\n\n"
            "Requirements:\n"
            "- Formal technical tone\n"
            "- Introduce the topic clearly\n"
            "- Explain industrial significance\n"
            "- Same language as data (French/English)\n"
            "- No chapter numbers in response"
        )
        return self.call_gemini(prompt, temperature=0.4)

    # ==================== DATA ====================

    def _merge_images_config(self, data: Dict, images_config: Dict) -> None:
        if "catalog_images" in images_config:
            data["catalog_images"] = images_config["catalog_images"]

        def _merge_map(section: str):
            if section in images_config:
                for key, val in images_config[section].items():
                    data.setdefault(section, {})
                    if isinstance(val, dict):
                        data[section].setdefault(key, {}).update(val)
                    else:
                        data[section][key] = val

        _merge_map("machines")
        _merge_map("products")
        _merge_map("processes")

    # ==================== LATEX TEMPLATE PDF ====================

    def _escape_latex(self, text: str) -> str:
        if not text:
            return ""
        replacements = [
            ("\\", "\\textbackslash{}"),
            ("&", "\\&"),
            ("%", "\\%"),
            ("$", "\\$"),
            ("#", "\\#"),
            ("_", "\\_"),
            ("{", "\\{"),
            ("}", "\\}"),
            ("~", "\\textasciitilde{}"),
            ("^", "\\textasciicircum{}"),
        ]
        for old, new in replacements:
            text = text.replace(old, new)
        return text

    def _download_image(self, url: str, save_path: str) -> bool:
        import requests
        from io import BytesIO
        try:
            response = requests.get(url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            if response.status_code == 200:
                img = PILImage.open(BytesIO(response.content))
                if img.mode in ("RGBA", "P", "LA"):
                    img = img.convert("RGB")
                png_path = save_path.rsplit(".", 1)[0] + ".png"
                img.save(png_path, "PNG")
                return True
        except Exception:
            return False
        return False

    def _generate_machine_cards_latex(self, machines: List[Dict], images_folder: str = None) -> str:
        cards = []
        for idx, machine in enumerate(machines, 1):
            name = self._escape_latex(machine.get("name", f"Machine {idx}"))
            model = self._escape_latex(machine.get("model", "N/A"))
            count = machine.get("count", 1)
            use = self._escape_latex(machine.get("use", "N/A"))
            width = machine.get("width", "N/A")
            height = machine.get("height", "N/A")
            image_url = machine.get("image", "")

            image_latex = "\\placeholder{4.5cm}{3cm}{ASSET PHOTO}"
            if images_folder and image_url and image_url.startswith("http"):
                img_filename = f"machine_{idx:02d}.png"
                img_path = os.path.join(images_folder, f"machine_{idx:02d}.jpg")
                if self._download_image(image_url, img_path):
                    image_latex = f"\\includegraphics[width=4.5cm, height=3cm, keepaspectratio]{{images/{img_filename}}}"

            card = f"""
\\vspace{{0.5cm}}

% ASSET {idx:02d}
\\begin{{assetcard}}{{{name}}}{{{model}}}
    {image_latex}
    \\tcblower
    \\begin{{tblr}}{{colspec={{X[l] X[r]}}, rowsep=3pt, coltext=BrandText}}
        \\textbf{{Count}} & {count} \\\\
        \\textbf{{Dimensions}} & {width}m x {height}m \\\\
        \\textbf{{Status}} & \\textbf{{Operational}} \\\\
    \\end{{tblr}}
    \\vspace{{0.3cm}}
    {use}
\\end{{assetcard}}
"""
            cards.append(card)
            # Add page break after every 2 machines to prevent overflow
            if idx % 2 == 0 and idx < len(machines):
                cards.append("\\clearpage")
        return "\n".join(cards)

    def _generate_product_table_latex(self, product: Dict, ribif_products: List[Dict]) -> str:
        rows = []
        if product:
            name = self._escape_latex(str(product.get("name", "N/A")))
            unit = self._escape_latex(str(product.get("output_unit", "units")))
            target = self._escape_latex(str(product.get("target_output_per_hour", "N/A")))
            rows.append(f"    \\textbf{{P-001}} & \\textbf{{{name}}} & {target} {unit}/hr & Primary \\\\")
        for idx, prod in enumerate(ribif_products[:5], 2):
            name = self._escape_latex(prod.get("nom_produit", "N/A")[:40])
            cat = self._escape_latex(prod.get("categorie", "N/A"))
            vol = prod.get("volume_production", {})
            cap = self._escape_latex(str(vol.get("capacite", "N/A")))
            rows.append(f"    \\textbf{{P-{idx:03d}}} & \\textbf{{{name}}} & {cap} & {cat.title()} \\\\")
        return "\n".join(rows)

    def _generate_objectives_latex(self, objectives: List[str]) -> str:
        items = []
        for obj in objectives[:5]:
            items.append(f"        \\item {self._escape_latex(obj.title())}")
        return "\n".join(items)

    def _parse_dimensions_m(self, dimensions: Any) -> tuple:
        if isinstance(dimensions, dict):
            length = dimensions.get("longueur") or dimensions.get("length")
            width = dimensions.get("largeur") or dimensions.get("width")
            height = dimensions.get("hauteur") or dimensions.get("height")
            return self._to_m(length), self._to_m(width or height)
        if isinstance(dimensions, str):
            nums = re.findall(r"\d+\.?\d*", dimensions)
            if len(nums) >= 2:
                return self._to_m(nums[0]), self._to_m(nums[1])
        return "N/A", "N/A"

    def _to_m(self, value: Any) -> str:
        try:
            num = float(str(value).strip())
        except Exception:
            return "N/A"
        if num > 30:
            num = num / 1000.0
        return f"{num:.2f}".rstrip("0").rstrip(".")

    def _build_template_input(self, module1_data: Dict, module4_data: Optional[Dict]) -> Dict[str, Any]:
        product_src = (module1_data.get("stage_3_produits_fabriques", {})
                       .get("produits_fabriques", []))
        product_src = product_src[0] if product_src else {}
        volume = product_src.get("volume_production", {}) if isinstance(product_src, dict) else {}
        product = {
            "name": str(product_src.get("nom_produit", "Industrial Product")),
            "output_unit": str(volume.get("unite", "units")),
            "target_output_per_hour": str(volume.get("capacite", "N/A")),
        }

        enriched_lookup = {}
        if module4_data and isinstance(module4_data, dict):
            for item in module4_data.get("machines_enriched", []):
                machine_input = item.get("machine_input", {})
                name = (machine_input.get("nom_machine") or "").lower().strip()
                if name:
                    enriched_lookup[name] = machine_input

        machines = []
        for m in module1_data.get("stage_4_machines_equipements", {}).get("machines_production", []):
            name = m.get("nom_machine", "Machine")
            lookup = enriched_lookup.get(str(name).lower().strip(), {})
            image_url = lookup.get("best_image_url")
            if not image_url or not str(image_url).startswith("http"):
                assets = lookup.get("assets", {}) if isinstance(lookup, dict) else {}
                urls = assets.get("image_urls", []) if isinstance(assets, dict) else []
                image_url = urls[0] if urls else ""

            specs = m.get("specifications", {}) if isinstance(m, dict) else {}
            width, height = self._parse_dimensions_m(specs.get("dimensions", ""))
            machines.append({
                "name": name,
                "model": m.get("type", m.get("fabricant_recommande", "N/A")),
                "count": m.get("quantite_necessaire", 1),
                "use": m.get("use", "N/A"),
                "width": width,
                "height": height,
                "image": image_url if isinstance(image_url, str) else "",
            })

        return {"product": product, "machines": machines}

    def _generate_pdf_from_template(self, module1_data: Dict, module4_data: Optional[Dict],
                                    output_path: str, template_path: str) -> Optional[str]:
        project_info = module1_data.get("stage_1_informations_generales", {}).get("informations_generales", {})
        ribif_products = module1_data.get("stage_3_produits_fabriques", {}).get("produits_fabriques", [])
        input_data = self._build_template_input(module1_data, module4_data)

        company_name = project_info.get("nom_entreprise", "COMPANY NAME")
        project_name = project_info.get("nom_projet", "Industrial Project")
        description = project_info.get("description_projet", "")
        objectives = project_info.get("objectifs_strategiques", [])

        machines = input_data.get("machines", [])
        product = input_data.get("product", {})

        with open(template_path, "r", encoding="utf-8") as f:
            template = f.read()
        
        # Normalize line endings to Unix-style (LF only)
        template = template.replace("\r\n", "\n").replace("\r", "\n")

        product_rows = self._generate_product_table_latex(product, ribif_products)
        objectives_items = self._generate_objectives_latex(objectives)
        short_desc = self._escape_latex(description[:500] + "..." if len(description) > 500 else description)

        template = template.replace("ALLO MAISON IND.", self._escape_latex(company_name.upper()[:25]))
        template = template.replace("DEC 2025", datetime.now().strftime("%b %Y").upper())
        template = template.replace(
            r"\textbf{ALLO MAISON}",
            "\\textbf{" + self._escape_latex(company_name.split()[0].upper()) + "}"
        )
        template = template.replace(
            r"\lipsum[1][1-5] % REPLACE WITH YOUR PROJECT DESCRIPTION",
            short_desc if short_desc else "Industrial production facility overview."
        )

        old_objectives = r"""        \item \lipsum[2][1]
        \item \lipsum[2][2]
        \item \lipsum[2][3]"""
        new_objectives = objectives_items if objectives_items else "        \\item High-quality production\n        \\item Operational efficiency\n        \\item Market leadership"
        template = template.replace(old_objectives, new_objectives)

        old_machines = "% ASSET 01\n" \
            "\\begin{assetcard}{MACHINE REF-01}{CATEGORY A}\n" \
            "    \\placeholder{4.5cm}{3cm}{ASSET PHOTO}\n" \
            "    \\tcblower\n" \
            "    \\begin{tblr}{colspec={X[l] X[r]}, rowsep=3pt, coltext=BrandText}\n" \
            "        \\textbf{Manufacturer} & Brand Name \\\\\n" \
            "        \\textbf{Capacity} & 000 Units/Hr \\\\\n" \
            "        \\textbf{Power} & 00 kW \\\\\n" \
            "        \\textbf{Status} & \\textbf{Operational} \\\\\n" \
            "    \\end{tblr}\n" \
            "    \\vspace{0.3cm}\n" \
            "    \\lipsum[7][1-2]\n" \
            "\\end{assetcard}\n\n" \
            "\\vspace{0.5cm}\n\n" \
            "% ASSET 02\n" \
            "\\begin{assetcard}{MACHINE REF-02}{CATEGORY B}\n" \
            "    \\placeholder{4.5cm}{3cm}{ASSET PHOTO}\n" \
            "    \\tcblower\n" \
            "    \\begin{tblr}{colspec={X[l] X[r]}, rowsep=3pt, coltext=BrandText}\n" \
            "        \\textbf{Manufacturer} & Brand Name \\\\\n" \
            "        \\textbf{Capacity} & 000 Units/Hr \\\\\n" \
            "        \\textbf{Power} & 00 kW \\\\\n" \
            "        \\textbf{Status} & \\textbf{Maintenance} \\\\\n" \
            "    \\end{tblr}\n" \
            "    \\vspace{0.3cm}\n" \
            "    \\lipsum[8][1-2]\n" \
            "\\end{assetcard}"

        # Replace product table rows
        old_products = """    \\textbf{A-001} & \\textbf{Product Name Alpha} & Lorem Ipsum Material & Type A \\\\
    \\textbf{B-002} & \\textbf{Product Name Beta} & Dolor Sit Amet & Type B \\\\
    \\textbf{C-003} & \\textbf{Product Name Gamma} & Consectetur Adipiscing & Type C \\\\
    \\textbf{D-004} & \\textbf{Product Name Delta} & Elit Sed Do & Type D \\\\"""
        if product_rows:
            template = template.replace(old_products, product_rows.rstrip())

        lipsum_replacements = [
            (r"\lipsum[3][1-2]", "Automated systems ensure consistent quality and reduced cycle times."),
            (r"\lipsum[3][3-4]", "Integrated IoT sensors provide real-time monitoring and data analytics."),
            (r"\lipsum[3][5-6]", "Energy-efficient processes minimize environmental impact."),
            (r"\lipsum[4][1-4]", "The production workflow follows a sequential process flow optimized for throughput and quality control."),
            (r"\lipsum[5][1-3]", "Each stage is monitored for quality assurance and process optimization."),
            (r"\lipsum[6][1-2]", f"This facility operates {len(machines)} primary production assets."),
            (r"\lipsum[9][1-3]", f"Primary product: {self._escape_latex(str(product.get('name', 'Industrial Product')))} with target output of {self._escape_latex(str(product.get('target_output_per_hour', 'N/A')))} {self._escape_latex(str(product.get('output_unit', 'units')))}/hour."),
            # NOTE: lipsum[10] and lipsum[11] are intentionally NOT replaced to preserve the multicols layout
        ]
        for old, new in lipsum_replacements:
            template = template.replace(old, new)

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmpdir:
            images_folder = os.path.join(tmpdir, "images")
            os.makedirs(images_folder, exist_ok=True)

            machine_cards = self._generate_machine_cards_latex(machines, images_folder)
            template = template.replace(old_machines, machine_cards)

            short_project_name = self._escape_latex(project_name[:30] if len(project_name) > 30 else project_name)
            template = template.replace(
                r"{\fontsize{45}{50}\selectfont \textbf{DIGITAL TWIN}}",
                "{\\fontsize{45}{50}\\selectfont \\textbf{" + short_project_name.upper()[:25] + "}}"
            )
            template = template.replace(
                r"{\fontsize{45}{50}\selectfont \textbf{\& PROCESS}}",
                "{\\fontsize{45}{50}\\selectfont \\textbf{PRODUCTION}}"
            )

            tex_file = os.path.join(tmpdir, "catalog.tex")
            with open(tex_file, "w", encoding="utf-8") as f:
                f.write(template)

            for _ in range(2):
                subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", "-output-directory", tmpdir, tex_file],
                    capture_output=True,
                    text=True,
                    cwd=tmpdir
                )

            pdf_file = os.path.join(tmpdir, "catalog.pdf")
            if os.path.exists(pdf_file):
                shutil.copy(pdf_file, output_path)
                return output_path
        return None

    # ==================== PDF GENERATION ====================

    def generate_pdf_catalog(self, module1_data: Dict, module4_data: Dict = None,
                             output_path: str = "data/catalogs/industrial_catalog.pdf") -> str:
        template_path = str(Path(__file__).resolve().parent / "main.tex")
        generated = self._generate_pdf_from_template(
            module1_data=module1_data,
            module4_data=module4_data,
            output_path=output_path,
            template_path=template_path,
        )
        if not generated:
            raise RuntimeError("PDF generation failed. Ensure pdflatex is installed and template is valid.")
        return generated

    # ==================== HTML GENERATION ====================

    def generate_web_catalog(self, module1_data: Dict, module4_data: Dict = None,
                             output_path: str = "data/catalogs/industrial_catalog.html") -> str:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        project_info = module1_data.get('stage_1_informations_generales', {}).get('informations_generales', {})
        catalog_images = module1_data.get('catalog_images', {})
        machines = module1_data.get('stage_4_machines_equipements', {}).get('machines_production', [])
        products = module1_data.get('stage_3_produits_fabriques', {}).get('produits_fabriques', [])
        processes = module1_data.get('stage_5_processus_production', {}).get('processus_production', [])

        project_name = project_info.get('nom_projet', 'Industrial Project')
        company_name = project_info.get('nom_entreprise', 'Company')
        sector = project_info.get('secteur_activite', 'Industrial')

        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project_name} - Industrial Catalog</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: Georgia, serif; line-height: 1.8; color: #2c3e50; background: #ecf0f1; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; box-shadow: 0 0 30px rgba(0,0,0,0.15); }}
        
        /* Cover */
        .cover {{ min-height: 100vh; display: flex; flex-direction: column; justify-content: center; 
                  align-items: center; background: linear-gradient(135deg, #2c3e50, #34495e); 
                  color: white; padding: 3rem; text-align: center; }}
        .cover h1 {{ font-size: 2.5rem; margin-bottom: 1rem; letter-spacing: 2px; }}
        .cover h2 {{ font-size: 1.8rem; margin-bottom: 2rem; font-weight: 300; }}
        .cover-logo {{ max-width: 150px; margin-bottom: 2rem; }}
        .cover-image {{ max-width: 70%; max-height: 250px; margin: 2rem 0; border-radius: 8px; }}
        
        /* Navigation */
        .nav-toggle {{ position: fixed; top: 15px; left: 15px; background: #2c3e50; color: white;
                       border: none; padding: 10px 15px; cursor: pointer; z-index: 101; border-radius: 5px; }}
        .sidebar {{ position: fixed; left: 0; top: 0; width: 260px; height: 100vh; background: #34495e;
                    color: white; overflow-y: auto; padding: 2rem 0; z-index: 100;
                    transform: translateX(-260px); transition: transform 0.3s; }}
        .sidebar.active {{ transform: translateX(0); }}
        .sidebar h3 {{ padding: 0 1.5rem 1rem; font-size: 1.1rem; }}
        .sidebar a {{ display: block; padding: 0.6rem 1.5rem; color: #bdc3c7; text-decoration: none;
                      border-left: 3px solid transparent; transition: all 0.2s; }}
        .sidebar a:hover {{ background: #2c3e50; color: white; border-left-color: #3498db; }}
        .sidebar .chapter {{ font-weight: bold; color: white; margin-top: 0.8rem; }}
        
        /* Content */
        .content {{ padding: 2rem 3rem; }}
        .content.shifted {{ margin-left: 260px; }}
        .chapter-title {{ font-size: 2rem; color: #2c3e50; margin: 2rem 0 1rem; padding-bottom: 0.5rem;
                          border-bottom: 3px solid #2c3e50; }}
        .chapter-num {{ display: block; font-size: 1rem; color: #7f8c8d; }}
        .section-title {{ font-size: 1.5rem; color: #34495e; margin: 1.5rem 0 0.8rem; }}
        .body-text {{ text-align: justify; margin-bottom: 1rem; }}
        
        /* Images */
        .catalog-image {{ max-width: 100%; height: auto; display: block; margin: 1rem auto;
                          border-radius: 4px; box-shadow: 0 3px 10px rgba(0,0,0,0.1); cursor: pointer; }}
        .image-placeholder {{ background: #f5f5f5; border: 2px dashed #ccc; padding: 2rem;
                              text-align: center; color: #999; margin: 1rem 0; border-radius: 4px; }}
        .figure-caption {{ text-align: center; font-style: italic; color: #666; margin: 0.5rem 0 1.5rem; }}
        .image-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; margin: 1rem 0; }}
        .image-grid img {{ width: 100%; height: 180px; object-fit: contain; background: #f9f9f9; border-radius: 4px; }}
        
        /* Cards */
        .card {{ background: white; border: 1px solid #e0e0e0; border-radius: 8px; padding: 1.5rem;
                 margin: 1rem 0; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }}
        .card h4 {{ color: #2c3e50; margin-bottom: 1rem; padding-bottom: 0.5rem; border-bottom: 2px solid #3498db; }}
        
        /* Tables */
        table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
        th {{ background: #34495e; color: white; padding: 0.7rem; text-align: left; }}
        td {{ padding: 0.6rem; border-bottom: 1px solid #ddd; }}
        tr:nth-child(even) {{ background: #f8f9fa; }}
        
        /* Lightbox */
        .lightbox {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                     background: rgba(0,0,0,0.9); z-index: 1000; justify-content: center; align-items: center; }}
        .lightbox.active {{ display: flex; }}
        .lightbox img {{ max-width: 90%; max-height: 90%; }}
        .lightbox-close {{ position: absolute; top: 20px; right: 30px; color: white; font-size: 2rem; cursor: pointer; }}
        
        /* Search */
        .search-box {{ position: sticky; top: 0; background: white; padding: 1rem 0; border-bottom: 2px solid #ecf0f1; z-index: 50; }}
        .search-box input {{ width: 100%; padding: 0.7rem 1rem; border: 2px solid #bdc3c7; border-radius: 5px; font-size: 1rem; }}
        
        /* Footer */
        .footer {{ background: #2c3e50; color: white; text-align: center; padding: 2rem; margin-top: 2rem; }}
        
        @media (max-width: 768px) {{
            .content {{ padding: 1rem; }}
            .cover h1 {{ font-size: 1.8rem; }}
            .image-grid {{ grid-template-columns: 1fr; }}
        }}
        @media print {{
            .sidebar, .nav-toggle, .search-box, .lightbox {{ display: none !important; }}
            .content {{ margin-left: 0 !important; }}
        }}
    </style>
</head>
<body>
    <button class="nav-toggle" onclick="toggleNav()">☰ Menu</button>
    
    <div class="lightbox" id="lightbox" onclick="closeLightbox()">
        <span class="lightbox-close">&times;</span>
        <img src="" id="lightbox-img">
    </div>
    
    <nav class="sidebar" id="sidebar">
        <h3>Contents</h3>
        <a href="#cover">Cover</a>
        <a href="#ch1" class="chapter">1. Industry Overview</a>
        <a href="#ch2" class="chapter">2. Process Architecture</a>
        <a href="#ch3" class="chapter">3. Machine Families</a>
        <a href="#ch4" class="chapter">4. Product Families</a>
        <a href="#ch5" class="chapter">5. Supply Chain</a>
        <a href="#ch6" class="chapter">6. Digital Twin</a>
    </nav>
    
    <div class="container">
        <section id="cover" class="cover">
            {self.get_html_image(catalog_images.get('company_logo'), 'Logo', 'cover-logo')}
            <h1>INDUSTRIAL TECHNICAL CATALOG</h1>
            <h2>{project_name}</h2>
            <p>{sector}</p>
            {self.get_html_image(catalog_images.get('cover_image'), 'Cover', 'cover-image')}
            <p style="margin-top:2rem; font-size:1.3rem;">{company_name}</p>
            <p style="margin-top:2rem; opacity:0.8;">Edition 1.0 | {datetime.now().strftime('%B %Y')}</p>
        </section>
        
        <div class="content" id="content">
            <div class="search-box">
                <input type="text" placeholder="🔍 Search catalog..." onkeyup="searchCatalog(this.value)">
            </div>
            
            <!-- Chapter 1 -->
            <section id="ch1">
                <h1 class="chapter-title"><span class="chapter-num">CHAPTER 1</span>INDUSTRY OVERVIEW</h1>
                {self.get_html_image(catalog_images.get('site_overview'), 'Site Overview')}
                <p class="figure-caption">Industrial Site Overview</p>
                <table>
                    <tr><th>Parameter</th><th>Value</th></tr>
                    <tr><td>Project</td><td>{project_name}</td></tr>
                    <tr><td>Company</td><td>{company_name}</td></tr>
                    <tr><td>Sector</td><td>{sector}</td></tr>
                    <tr><td>Location</td><td>{project_info.get('localisation', {}).get('ville', 'N/A')}</td></tr>
                </table>
            </section>
            
            <!-- Chapter 2 -->
            <section id="ch2">
                <h1 class="chapter-title"><span class="chapter-num">CHAPTER 2</span>PROCESS ARCHITECTURE</h1>
                {self.get_html_image(catalog_images.get('process_flow'), 'Process Flow')}
                <p class="figure-caption">Process Flow Diagram</p>
'''

        # Process steps
        for idx, step in enumerate(processes, 1):
            step_img = step.get('images', {}).get('workflow') or step.get('image', '')
            html += f'''
                <div class="card">
                    <h4>2.{idx} {step.get('nom_etape', 'Step')}</h4>
                    {self.get_html_image(step_img, f"Step {idx}")}
                    <p><strong>Type:</strong> {step.get('type_operation', 'N/A')}</p>
                    <p>{step.get('description', 'N/A')}</p>
                </div>
'''

        html += '''
            </section>
            
            <!-- Chapter 3 -->
            <section id="ch3">
                <h1 class="chapter-title"><span class="chapter-num">CHAPTER 3</span>MACHINE FAMILIES</h1>
'''

        # Machines
        for idx, machine in enumerate(machines, 1):
            m_imgs = machine.get('images', {})
            specs = machine.get('specifications', {})

            main_img = m_imgs.get('photo') or m_imgs.get('main') or machine.get('image', '')
            model_3d = m_imgs.get('3d_model') or m_imgs.get('model_3d', '')
            plan_2d = m_imgs.get('2d_plan') or m_imgs.get('plan_2d', '')

            html += f'''
                <div class="card">
                    <h4>3.{idx} {machine.get('nom_machine', 'Machine')}</h4>
                    <div class="image-grid">
                        <div>{self.get_html_image(main_img, 'Photo')}<p class="figure-caption">Photo</p></div>
                        <div>{self.get_html_image(model_3d, '3D Model')}<p class="figure-caption">3D Model</p></div>
                        <div>{self.get_html_image(plan_2d, '2D Plan')}<p class="figure-caption">Technical Drawing</p></div>
                    </div>
                    <table>
                        <tr><th>Spec</th><th>Value</th></tr>
                        <tr><td>Manufacturer</td><td>{machine.get('fabricant_recommande', 'N/A')}</td></tr>
                        <tr><td>Capacity</td><td>{specs.get('capacite', 'N/A')}</td></tr>
                        <tr><td>Power</td><td>{specs.get('puissance', 'N/A')}</td></tr>
                    </table>
                </div>
'''

        html += '''
            </section>
            
            <!-- Chapter 4 -->
            <section id="ch4">
                <h1 class="chapter-title"><span class="chapter-num">CHAPTER 4</span>PRODUCT FAMILIES</h1>
'''

        # Products
        for idx, product in enumerate(products, 1):
            p_imgs = product.get('images', {})
            prod_img = p_imgs.get('photo') or p_imgs.get('main') or product.get('image', '')
            schematic = p_imgs.get('schematic', '')

            html += f'''
                <div class="card">
                    <h4>4.{idx} {product.get('nom_produit', 'Product')}</h4>
                    <div class="image-grid">
                        <div>{self.get_html_image(prod_img, 'Product')}<p class="figure-caption">Product Photo</p></div>
                        <div>{self.get_html_image(schematic, 'Schematic')}<p class="figure-caption">Schematic</p></div>
                    </div>
                    <p>{product.get('description', 'N/A')}</p>
                </div>
'''

        html += f'''
            </section>
            
            <!-- Chapter 5 -->
            <section id="ch5">
                <h1 class="chapter-title"><span class="chapter-num">CHAPTER 5</span>SUPPLY CHAIN</h1>
                {self.get_html_image(catalog_images.get('supply_chain_diagram'), 'Supply Chain')}
                <p class="figure-caption">Supply Chain Network</p>
            </section>
            
            <!-- Chapter 6 -->
            <section id="ch6">
                <h1 class="chapter-title"><span class="chapter-num">CHAPTER 6</span>DIGITAL TWIN</h1>
                {self.get_html_image(catalog_images.get('digital_twin_architecture'), 'DT Architecture')}
                <p class="figure-caption">Digital Twin Architecture</p>
                {self.get_html_image(catalog_images.get('factory_3d'), '3D Factory')}
                <p class="figure-caption">3D Virtual Factory</p>
                {self.get_html_image(catalog_images.get('dashboard'), 'Dashboard')}
                <p class="figure-caption">KPI Dashboard</p>
            </section>
        </div>
        
        <div class="footer">
            <h3>{project_name}</h3>
            <p>&copy; {datetime.now().year} {company_name}</p>
            <p style="margin-top:1rem; opacity:0.7;">Generated by RIBIF Module 9</p>
        </div>
    </div>
    
    <script>
        function toggleNav() {{
            document.getElementById('sidebar').classList.toggle('active');
            document.getElementById('content').classList.toggle('shifted');
        }}
        function openLightbox(img) {{
            document.getElementById('lightbox-img').src = img.src;
            document.getElementById('lightbox').classList.add('active');
        }}
        function closeLightbox() {{
            document.getElementById('lightbox').classList.remove('active');
        }}
        function searchCatalog(query) {{
            const q = query.toLowerCase();
            document.querySelectorAll('.card, section').forEach(el => {{
                el.style.display = el.textContent.toLowerCase().includes(q) ? '' : 'none';
            }});
        }}
        document.querySelectorAll('.sidebar a').forEach(a => {{
            a.addEventListener('click', e => {{
                e.preventDefault();
                document.querySelector(a.getAttribute('href')).scrollIntoView({{ behavior: 'smooth' }});
            }});
        }});
    </script>
</body>
</html>'''

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        return output_path

    # ==================== MAIN GENERATION ====================

    def generate_catalog(self, input_data: CatalogInput, base_url: str = "http://localhost:5000") -> CatalogOutput:
        module1_data = input_data.module1_data
        module4_data = input_data.module4_data

        if input_data.images_config:
            self._merge_images_config(module1_data, input_data.images_config)

        output_dir = input_data.output_dir
        os.makedirs(output_dir, exist_ok=True)

        project_info = module1_data.get("stage_1_informations_generales", {}).get("informations_generales", {})
        project_name = project_info.get("nom_projet", "Industrial Project")
        company_name = project_info.get("nom_entreprise", "Company")

        base_name = input_data.base_filename or project_name or "catalog"
        base_name = re.sub(r"[^A-Za-z0-9_-]+", "_", base_name).strip("_") or "catalog"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = f"{base_name}_{timestamp}"

        pdf_path = None
        html_path = None

        fmt = input_data.output_format.lower()
        if fmt in ("both", "pdf"):
            pdf_path = os.path.join(output_dir, f"{base}.pdf")
            try:
                pdf_path = self.generate_pdf_catalog(module1_data, module4_data, pdf_path)
            except Exception as e:
                logger.warning(f"PDF generation failed (pdflatex may not be installed): {e}")
                pdf_path = None
                # If PDF was requested and failed, fall back to HTML
                if fmt == "pdf":
                    fmt = "html"
        if fmt in ("both", "html") or pdf_path is None:
            html_path = os.path.join(output_dir, f"{base}.html")
            html_path = self.generate_web_catalog(module1_data, module4_data, html_path)

        def _size(path: Optional[str]) -> Optional[int]:
            if path and os.path.exists(path):
                return os.path.getsize(path)
            return None

        result = CatalogOutput(
            created_at=datetime.utcnow().isoformat(),
            project_name=project_name,
            company_name=company_name,
            output_format=fmt,
            pdf_filename=os.path.basename(pdf_path) if pdf_path else None,
            pdf_filepath=pdf_path,
            pdf_size_bytes=_size(pdf_path),
            pdf_download_url=f"{base_url}/download/{os.path.basename(pdf_path)}" if pdf_path else None,
            html_filename=os.path.basename(html_path) if html_path else None,
            html_filepath=html_path,
            html_size_bytes=_size(html_path),
            html_download_url=f"{base_url}/download/{os.path.basename(html_path)}" if html_path else None,
        )
        return result
