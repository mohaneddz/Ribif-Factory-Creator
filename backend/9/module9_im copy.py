"""
RIBIF Module 9: Professional Industrial Technical Catalog Generator
WITH FULL IMAGE SUPPORT
- Machine images (photos, 3D models, 2D plans)
- Product images
- Process diagrams
- Company logos

Generates book-like catalogs (PDF + Web)
"""

from openai import OpenAI
from dotenv import load_dotenv
import os
import json
from pathlib import Path
from typing import Dict, List, Optional
import time
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, 
    Spacer, PageBreak, Image, KeepTogether, Flowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from datetime import datetime
from PIL import Image as PILImage
import base64


class ImagePlaceholder(Flowable):
    """Placeholder for missing images in PDF"""
    def __init__(self, width, height, text="Image Not Available"):
        Flowable.__init__(self)
        self.width = width
        self.height = height
        self.text = text
    
    def draw(self):
        self.canv.setStrokeColor(colors.HexColor('#cccccc'))
        self.canv.setFillColor(colors.HexColor('#f5f5f5'))
        self.canv.rect(0, 0, self.width, self.height, fill=1)
        self.canv.setFillColor(colors.HexColor('#999999'))
        self.canv.setFont('Helvetica', 10)
        text_width = self.canv.stringWidth(self.text, 'Helvetica', 10)
        self.canv.drawString((self.width - text_width) / 2, self.height / 2, self.text)


class IndustrialCatalogGenerator:
    """
    Professional Industrial Catalog Generator with Full Image Support
    
    Supports images in JSON data in these formats:
    
    1. Direct in machine/product data:
       {
         "nom_machine": "CNC Machine",
         "image": "path/to/photo.jpg",
         "images": {
           "photo": "machines/cnc_photo.jpg",
           "3d_model": "machines/cnc_3d.png",
           "2d_plan": "machines/cnc_plan.pdf"
         }
       }
    
    2. Separate images config file:
       {
         "catalog_images": {
           "company_logo": "logos/company.png",
           "cover_image": "covers/factory.jpg"
         },
         "machines": {
           "CNC Machine": {
             "photo": "machines/cnc.jpg",
             "3d_model": "machines/cnc_3d.png"
           }
         }
       }
    """
    
    def __init__(self, image_base_path: str = "data/images"):
        """Initialize catalog generator with image support"""
        load_dotenv()
        api_key = os.getenv('GROQ_API_KEY')
        
        if not api_key:
            raise ValueError("❌ No GROQ_API_KEY found in .env file")
        
        # Initialize Groq client
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1"
        )
        self.model_name = "llama-3.3-70b-versatile"
        
        # Setup PDF styles
        self.styles = getSampleStyleSheet()
        self._create_professional_styles()
        
        # Counters
        self.chapter_num = 0
        self.figure_num = 0
        self.table_num = 0
        
        # Image settings
        self.image_base_path = image_base_path
        self.max_image_width = 16 * cm
        self.max_image_height = 12 * cm
        self.supported_formats = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
        
        print("✅ Industrial Catalog Generator initialized")
        print(f"🖼️  Image base path: {image_base_path}")
        print("📘 PDF + Web generation ready\n")
    
    def _create_professional_styles(self):
        """Create professional PDF styles"""
        
        self.styles.add(ParagraphStyle(
            name='BookTitle', parent=self.styles['Title'],
            fontSize=28, textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=10, alignment=TA_CENTER, fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='Subtitle', parent=self.styles['Normal'],
            fontSize=14, textColor=colors.HexColor('#4a4a4a'),
            spaceAfter=20, alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            name='ChapterTitle', parent=self.styles['Heading1'],
            fontSize=20, textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=15, spaceBefore=30, fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionTitle', parent=self.styles['Heading2'],
            fontSize=14, textColor=colors.HexColor('#2a2a2a'),
            spaceAfter=10, spaceBefore=15, fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='Subsection', parent=self.styles['Heading3'],
            fontSize=12, textColor=colors.HexColor('#3a3a3a'),
            spaceAfter=8, spaceBefore=10, fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='BookBody', parent=self.styles['Normal'],
            fontSize=10, leading=14, alignment=TA_JUSTIFY, spaceAfter=8
        ))
        
        self.styles.add(ParagraphStyle(
            name='FigureCaption', parent=self.styles['Normal'],
            fontSize=9, textColor=colors.HexColor('#4a4a4a'),
            alignment=TA_CENTER, spaceAfter=15, spaceBefore=5,
            fontName='Helvetica-Oblique'
        ))
        
        self.styles.add(ParagraphStyle(
            name='TableCaption', parent=self.styles['Normal'],
            fontSize=9, textColor=colors.HexColor('#4a4a4a'),
            alignment=TA_LEFT, spaceBefore=5, fontName='Helvetica-Bold'
        ))
    
    # ==================== IMAGE HANDLING ====================
    
    def resolve_image_path(self, image_path: str) -> Optional[str]:
        """
        Resolve image path - checks multiple locations
        
        Args:
            image_path: Relative or absolute path to image
            
        Returns:
            Absolute path if found, None otherwise
        """
        if not image_path:
            return None
        
        # Already absolute and exists
        if os.path.isabs(image_path) and os.path.exists(image_path):
            return image_path
        
        # Check relative to current directory
        if os.path.exists(image_path):
            return os.path.abspath(image_path)
        
        # Check in image base path
        full_path = os.path.join(self.image_base_path, image_path)
        if os.path.exists(full_path):
            return os.path.abspath(full_path)
        
        # Check common subdirectories
        subdirs = ['machines', 'products', 'processes', '3d_models', '2d_plans', 
                   'logos', 'covers', 'diagrams', 'photos']
        for subdir in subdirs:
            full_path = os.path.join(self.image_base_path, subdir, image_path)
            if os.path.exists(full_path):
                return os.path.abspath(full_path)
            
            # Also check without subdir in base path
            full_path = os.path.join(self.image_base_path, subdir, os.path.basename(image_path))
            if os.path.exists(full_path):
                return os.path.abspath(full_path)
        
        return None
    
    def get_image_for_pdf(self, image_path: str, max_width: float = None,
                          max_height: float = None, caption: str = None) -> List:
        """
        Get image flowable(s) for PDF
        
        Args:
            image_path: Path to image file
            max_width: Maximum width in points
            max_height: Maximum height in points
            caption: Optional figure caption
            
        Returns:
            List of flowable elements (image + caption)
        """
        elements = []
        max_width = max_width or self.max_image_width
        max_height = max_height or self.max_image_height
        
        resolved_path = self.resolve_image_path(image_path)
        
        if resolved_path:
            try:
                # Get original dimensions
                with PILImage.open(resolved_path) as img:
                    orig_width, orig_height = img.size
                
                # Calculate scaling
                width_ratio = max_width / orig_width
                height_ratio = max_height / orig_height
                scale = min(width_ratio, height_ratio, 1.0)
                
                new_width = orig_width * scale
                new_height = orig_height * scale
                
                # Create ReportLab image
                rl_image = Image(resolved_path, width=new_width, height=new_height)
                rl_image.hAlign = 'CENTER'
                elements.append(rl_image)
                
                print(f"      ✅ Image added: {os.path.basename(resolved_path)}")
                
            except Exception as e:
                print(f"      ⚠️  Error loading {image_path}: {e}")
                elements.append(ImagePlaceholder(
                    max_width * 0.5, max_height * 0.3,
                    f"Error: {os.path.basename(image_path)}"
                ))
        else:
            # Placeholder for missing image
            if image_path:
                print(f"      ⚠️  Not found: {image_path}")
            elements.append(ImagePlaceholder(
                max_width * 0.5, max_height * 0.3,
                f"[{os.path.basename(image_path) if image_path else 'No Image'}]"
            ))
        
        # Add caption
        if caption:
            self.figure_num += 1
            elements.append(Paragraph(
                f"Figure {self.figure_num}: {caption}",
                self.styles['FigureCaption']
            ))
        
        return elements
    
    def get_image_as_base64(self, image_path: str) -> Optional[str]:
        """Convert image to base64 for HTML embedding"""
        resolved_path = self.resolve_image_path(image_path)
        
        if resolved_path:
            try:
                with open(resolved_path, 'rb') as f:
                    img_data = base64.b64encode(f.read()).decode()
                
                ext = os.path.splitext(resolved_path)[1].lower().strip('.')
                mime_types = {
                    'jpg': 'jpeg', 'jpeg': 'jpeg', 'png': 'png',
                    'gif': 'gif', 'webp': 'webp', 'bmp': 'bmp'
                }
                mime = mime_types.get(ext, 'jpeg')
                
                return f"data:image/{mime};base64,{img_data}"
            except:
                return None
        return None
    
    def get_html_image(self, image_path: str, alt: str = "", 
                       css_class: str = "catalog-image") -> str:
        """Get HTML img tag with embedded base64 or placeholder"""
        if not image_path:
            return f'<div class="image-placeholder">[{alt or "Image Not Available"}]</div>'
        
        base64_src = self.get_image_as_base64(image_path)
        
        if base64_src:
            return f'<img src="{base64_src}" alt="{alt}" class="{css_class}" onclick="openLightbox(this)">'
        else:
            return f'<div class="image-placeholder">[{alt or os.path.basename(image_path)}]</div>'
    
    # ==================== AI CONTENT ====================
    
    def call_groq(self, prompt: str, temperature: float = 0.3) -> str:
        """Call Groq AI for content generation"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a professional technical writer for industrial documentation. Write clear, precise content for technical catalogs."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                    max_tokens=4096
                )
                return response.choices[0].message.content.strip()
                
            except Exception as e:
                if "rate" in str(e).lower() and attempt < max_retries - 1:
                    time.sleep(5 * (attempt + 1))
                else:
                    return "[Content generation unavailable]"
        
        return "[Max retries exceeded]"
    
    def generate_chapter_intro(self, chapter_name: str, context: str, data: Dict) -> str:
        """Generate AI chapter introduction"""
        print(f"   🤖 Generating intro: {chapter_name}...")
        
        prompt = f"""Write a professional introduction (2-3 paragraphs) for this catalog chapter:

CHAPTER: {chapter_name}
CONTEXT: {context}
DATA: {json.dumps(data, ensure_ascii=False)[:2000]}

Requirements:
- Formal technical tone
- Introduce the topic clearly
- Explain industrial significance
- Same language as data (French/English)
- No chapter numbers in response"""

        return self.call_groq(prompt, temperature=0.4)
    
    # ==================== DATA LOADING ====================
    
    def load_data(self, module1_path: str, module4_path: str = None,
                  images_config_path: str = None) -> tuple:
        """
        Load industrial data and images configuration
        
        Args:
            module1_path: Path to Module 1 extracted data JSON
            module4_path: Optional path to Module 4 suppliers JSON
            images_config_path: Optional path to separate images config JSON
        """
        print("📂 Loading data...")
        
        with open(module1_path, 'r', encoding='utf-8') as f:
            module1_data = json.load(f)
        print(f"   ✅ Module 1: {module1_path}")
        
        module4_data = None
        if module4_path and os.path.exists(module4_path):
            with open(module4_path, 'r', encoding='utf-8') as f:
                module4_data = json.load(f)
            print(f"   ✅ Module 4: {module4_path}")
        
        images_config = None
        if images_config_path and os.path.exists(images_config_path):
            with open(images_config_path, 'r', encoding='utf-8') as f:
                images_config = json.load(f)
            print(f"   ✅ Images config: {images_config_path}")
            
            # Merge images into module1 data
            self._merge_images_config(module1_data, images_config)
        
        return module1_data, module4_data
    
    def _merge_images_config(self, data: Dict, images_config: Dict):
        """Merge external images config into main data"""
        
        # Catalog-level images
        if 'catalog_images' in images_config:
            data['catalog_images'] = images_config['catalog_images']
        
        # Machine images
        machine_images = images_config.get('machines', {})
        machines = data.get('stage_4_machines_equipements', {}).get('machines_production', [])
        
        for machine in machines:
            name = machine.get('nom_machine', '')
            if name in machine_images:
                machine.setdefault('images', {}).update(machine_images[name])
        
        # Product images
        product_images = images_config.get('products', {})
        products = data.get('stage_3_produits_fabriques', {}).get('produits_fabriques', [])
        
        for product in products:
            name = product.get('nom_produit', '')
            if name in product_images:
                product.setdefault('images', {}).update(product_images[name])
        
        # Process images
        process_images = images_config.get('processes', {})
        processes = data.get('stage_5_processus_production', {}).get('processus_production', [])
        
        for process in processes:
            name = process.get('nom_etape', '')
            if name in process_images:
                process.setdefault('images', {}).update(process_images[name])
    
    # ==================== LATEX TEMPLATE PDF GENERATION ====================
    
    def load_template_data(self, ribif_path: str, input_path: str) -> tuple:
        """
        Load both JSON files for template filling
        
        Args:
            ribif_path: Path to FICHE_IDENTITE_INDUSTRIELLE_ribif_extracted.json
            input_path: Path to input.json with machines and product
        """
        print("📂 Loading template data...")
        
        with open(ribif_path, 'r', encoding='utf-8') as f:
            ribif_data = json.load(f)
        print(f"   ✅ RIBIF data: {ribif_path}")
        
        with open(input_path, 'r', encoding='utf-8') as f:
            input_data = json.load(f)
        print(f"   ✅ Input data: {input_path}")
        
        return ribif_data, input_data
    
    def _escape_latex(self, text: str) -> str:
        """Escape special LaTeX characters"""
        if not text:
            return ""
        # Order matters - escape backslash first
        replacements = [
            ('\\', '\\textbackslash{}'),
            ('&', '\\&'),
            ('%', '\\%'),
            ('$', '\\$'),
            ('#', '\\#'),
            ('_', '\\_'),
            ('{', '\\{'),
            ('}', '\\}'),
            ('~', '\\textasciitilde{}'),
            ('^', '\\textasciicircum{}'),
        ]
        for old, new in replacements:
            text = text.replace(old, new)
        return text
    
    def _generate_machine_cards_latex(self, machines: List[Dict]) -> str:
        """Generate LaTeX code for ALL machine cards"""
        cards = []
        
        for idx, machine in enumerate(machines, 1):
            name = self._escape_latex(machine.get('name', f'Machine {idx}'))
            model = self._escape_latex(machine.get('model', 'N/A'))
            count = machine.get('count', 1)
            use = self._escape_latex(machine.get('use', 'N/A'))
            width = machine.get('width', 'N/A')
            height = machine.get('height', 'N/A')
            
            # Use single backslashes - they get written correctly to .tex file
            card = f"""
\\vspace{{0.5cm}}

% ASSET {idx:02d}
\\begin{{assetcard}}{{{name}}}{{{model}}}
    \\placeholder{{4.5cm}}{{3cm}}{{ASSET PHOTO}}
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
        
        return "\n".join(cards)
    
    def _generate_product_table_latex(self, product: Dict, ribif_products: List[Dict]) -> str:
        """Generate LaTeX product table rows"""
        rows = []
        
        # Add main product from input.json
        if product:
            name = self._escape_latex(product.get('name', 'N/A'))
            unit = self._escape_latex(product.get('output_unit', 'units'))
            target = product.get('target_output_per_hour', 'N/A')
            rows.append(f"    \\textbf{{P-001}} & \\textbf{{{name}}} & {target} {unit}/hr & Primary \\\\")
        
        # Add products from ribif data (up to 5)
        for idx, prod in enumerate(ribif_products[:5], 2):
            name = self._escape_latex(prod.get('nom_produit', 'N/A')[:40])
            cat = self._escape_latex(prod.get('categorie', 'N/A'))
            vol = prod.get('volume_production', {})
            cap = self._escape_latex(str(vol.get('capacite', 'N/A')))
            rows.append(f"    \\textbf{{P-{idx:03d}}} & \\textbf{{{name}}} & {cap} & {cat.title()} \\\\")
        
        return "\n".join(rows)
    
    def _generate_objectives_latex(self, objectives: List[str]) -> str:
        """Generate LaTeX itemize content for objectives"""
        items = []
        for obj in objectives[:5]:
            items.append(f"        \\item {self._escape_latex(obj.title())}")
        return "\n".join(items)
    
    def generate_pdf_from_template(self, ribif_path: str, input_path: str,
                                    output_path: str = "data/catalogs/catalog_output.pdf",
                                    template_path: str = "main.tex"):
        """
        Generate PDF by filling LaTeX template with data
        
        Args:
            ribif_path: Path to RIBIF extracted JSON
            input_path: Path to input.json
            output_path: Output PDF path
            template_path: Path to main.tex template
        """
        import subprocess
        import tempfile
        import shutil
        
        print("\n" + "="*60)
        print("📘 GENERATING PDF FROM LATEX TEMPLATE")
        print("="*60 + "\n")
        
        # Load data
        ribif_data, input_data = self.load_template_data(ribif_path, input_path)
        
        # Extract data
        project_info = ribif_data.get('stage_1_informations_generales', {}).get('informations_generales', {})
        ribif_products = ribif_data.get('stage_3_produits_fabriques', {}).get('produits_fabriques', [])
        
        company_name = project_info.get('nom_entreprise', 'COMPANY NAME')
        project_name = project_info.get('nom_projet', 'Industrial Project')
        description = project_info.get('description_projet', '')
        objectives = project_info.get('objectifs_strategiques', [])
        
        machines = input_data.get('machines', [])
        product = input_data.get('product', {})
        
        print(f"   📊 Company: {company_name}")
        print(f"   📊 Machines: {len(machines)}")
        print(f"   📊 Product: {product.get('name', 'N/A')}")
        
        # Read template
        print(f"\n📄 Reading template: {template_path}")
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
        
        # Generate dynamic content
        machine_cards = self._generate_machine_cards_latex(machines)
        product_rows = self._generate_product_table_latex(product, ribif_products)
        objectives_items = self._generate_objectives_latex(objectives)
        
        # Truncate description to ~300 chars for cleaner display
        short_desc = self._escape_latex(description[:500] + "..." if len(description) > 500 else description)
        
        # Replace placeholders in template
        print("🔧 Filling template placeholders...")
        
        # Cover page - PROJECT and DATE
        template = template.replace(
            "ALLO MAISON IND.",
            self._escape_latex(company_name.upper()[:25])
        )
        template = template.replace(
            "DEC 2025",
            datetime.now().strftime('%b %Y').upper()
        )
        
        # Footer
        template = template.replace(
            r"\textbf{ALLO MAISON}",
            "\\textbf{" + self._escape_latex(company_name.split()[0].upper()) + "}"
        )
        
        # Section 01 - Replace lipsum with actual description
        template = template.replace(
            r"\lipsum[1][1-5] % REPLACE WITH YOUR PROJECT DESCRIPTION",
            short_desc if short_desc else "Industrial production facility overview."
        )
        
        # Section 01 - Replace KEY OBJECTIVES items
        old_objectives = r"""        \item \lipsum[2][1]
        \item \lipsum[2][2]
        \item \lipsum[2][3]"""
        new_objectives = objectives_items if objectives_items else "        \\item High-quality production\n        \\item Operational efficiency\n        \\item Market leadership"
        template = template.replace(old_objectives, new_objectives)
        
        # Section 03 - Replace machine cards (both ASSET 01 and ASSET 02)
        old_machines = r"""% ASSET 01
\begin{assetcard}{MACHINE REF-01}{CATEGORY A}
    \placeholder{4.5cm}{3cm}{ASSET PHOTO}
    \tcblower
    \begin{tblr}{colspec={X[l] X[r]}, rowsep=3pt, coltext=BrandText}
        \textbf{Manufacturer} & Brand Name \\
        \textbf{Capacity} & 000 Units/Hr \\
        \textbf{Power} & 00 kW \\
        \textbf{Status} & \textbf{Operational} \\
    \end{tblr}
    \vspace{0.3cm}
    \lipsum[7][1-2]
\end{assetcard}

\vspace{0.5cm}

% ASSET 02
\begin{assetcard}{MACHINE REF-02}{CATEGORY B}
    \placeholder{4.5cm}{3cm}{ASSET PHOTO}
    \tcblower
    \begin{tblr}{colspec={X[l] X[r]}, rowsep=3pt, coltext=BrandText}
        \textbf{Manufacturer} & Brand Name \\
        \textbf{Capacity} & 000 Units/Hr \\
        \textbf{Power} & 00 kW \\
        \textbf{Status} & \textbf{Maintenance} \\
    \end{tblr}
    \vspace{0.3cm}
    \lipsum[8][1-2]
\end{assetcard}"""
        
        template = template.replace(old_machines, machine_cards)
        
        # Section 04 - Replace product table rows
        old_products = r"""    \textbf{A-001} & \textbf{Product Name Alpha} & Lorem Ipsum Material & Type A \\
    \textbf{B-002} & \textbf{Product Name Beta} & Dolor Sit Amet & Type B \\
    \textbf{C-003} & \textbf{Product Name Gamma} & Consectetur Adipiscing & Type C \\
    \textbf{D-004} & \textbf{Product Name Delta} & Elit Sed Do & Type D \\"""
        
        template = template.replace(old_products, product_rows)
        
        # Replace remaining lipsum calls with generic text
        lipsum_replacements = [
            (r"\lipsum[3][1-2]", "Automated systems ensure consistent quality and reduced cycle times."),
            (r"\lipsum[3][3-4]", "Integrated IoT sensors provide real-time monitoring and data analytics."),
            (r"\lipsum[3][5-6]", "Energy-efficient processes minimize environmental impact."),
            (r"\lipsum[4][1-4]", "The production workflow follows a sequential process flow optimized for throughput and quality control."),
            (r"\lipsum[5][1-3]", "Each stage is monitored for quality assurance and process optimization."),
            (r"\lipsum[6][1-2]", f"This facility operates {len(machines)} primary production assets."),
            (r"\lipsum[9][1-3]", f"Primary product: {self._escape_latex(product.get('name', 'Industrial Product'))} with target output of {product.get('target_output_per_hour', 'N/A')} {product.get('output_unit', 'units')}/hour."),
            (r"\lipsum[10][1-3]", "Raw materials are sourced from certified suppliers following quality protocols."),
            (r"\lipsum[11][1-3]", "Finished products are dispatched through optimized logistics channels."),
        ]
        
        for old, new in lipsum_replacements:
            template = template.replace(old, new)
        
        # Create temp directory and compile
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tex_file = os.path.join(tmpdir, "catalog.tex")
            
            # Write filled template
            with open(tex_file, 'w', encoding='utf-8') as f:
                f.write(template)
            
            print(f"📝 Wrote filled template to temp file")
            
            # Compile with pdflatex (run twice for TOC/refs)
            print("🔨 Compiling with pdflatex...")
            
            for run in range(2):
                result = subprocess.run(
                    ['pdflatex', '-interaction=nonstopmode', '-output-directory', tmpdir, tex_file],
                    capture_output=True,
                    text=True,
                    cwd=tmpdir
                )
                
                if result.returncode != 0 and run == 1:
                    print(f"   ⚠️ pdflatex warnings (may be non-fatal)")
                    # Print last 10 lines of log for debugging
                    log_file = os.path.join(tmpdir, "catalog.log")
                    if os.path.exists(log_file):
                        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()
                            for line in lines[-10:]:
                                if 'error' in line.lower() or 'fatal' in line.lower():
                                    print(f"      {line.strip()}")
            
            # Copy PDF to output
            pdf_file = os.path.join(tmpdir, "catalog.pdf")
            if os.path.exists(pdf_file):
                shutil.copy(pdf_file, output_path)
                print(f"\n✅ PDF generated: {output_path}")
                return output_path
            else:
                print(f"\n❌ PDF generation failed - check LaTeX syntax")
                return None
    
    # ==================== PDF GENERATION ====================

    
    def generate_pdf_catalog(self, module1_data: Dict, module4_data: Dict = None,
                            output_path: str = "data/catalogs/industrial_catalog.pdf"):
        """Generate professional PDF catalog with images"""
        print("\n" + "="*60)
        print("📘 GENERATING PDF CATALOG")
        print("="*60 + "\n")
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Reset counters
        self.chapter_num = 0
        self.figure_num = 0
        self.table_num = 0
        
        # Create PDF
        doc = SimpleDocTemplate(
            output_path, pagesize=A4,
            rightMargin=2.5*cm, leftMargin=2.5*cm,
            topMargin=2*cm, bottomMargin=2*cm
        )
        
        story = []
        
        # Extract data
        project_info = module1_data.get('stage_1_informations_generales', {}).get('informations_generales', {})
        catalog_images = module1_data.get('catalog_images', {})
        machines = module1_data.get('stage_4_machines_equipements', {}).get('machines_production', [])
        products = module1_data.get('stage_3_produits_fabriques', {}).get('produits_fabriques', [])
        materials = module1_data.get('stage_2_matieres_premieres', {}).get('matieres_premieres', [])
        processes = module1_data.get('stage_5_processus_production', {}).get('processus_production', [])
        
        project_name = project_info.get('nom_projet', 'Industrial Project')
        company_name = project_info.get('nom_entreprise', 'Company')
        sector = project_info.get('secteur_activite', 'Industrial')
        
        # ========== COVER PAGE ==========
        print("📄 Building cover page...")
        story.append(Spacer(1, 2*cm))
        
        # Company logo
        logo = catalog_images.get('company_logo') or catalog_images.get('logo')
        if logo:
            story.extend(self.get_image_for_pdf(logo, max_width=6*cm, max_height=4*cm))
            story.append(Spacer(1, 1*cm))
        
        story.append(Paragraph("INDUSTRIAL TECHNICAL CATALOG", self.styles['BookTitle']))
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph(project_name, self.styles['Heading1']))
        story.append(Paragraph(sector, self.styles['Subtitle']))
        
        # Cover image
        cover_img = catalog_images.get('cover_image') or catalog_images.get('hero_image')
        if cover_img:
            story.extend(self.get_image_for_pdf(cover_img, max_width=14*cm, max_height=8*cm))
        
        story.append(Spacer(1, 1*cm))
        story.append(Paragraph(company_name, self.styles['Heading2']))
        story.append(Spacer(1, 2*cm))
        story.append(Paragraph(
            f"Edition 1.0 | {datetime.now().strftime('%B %Y')}<br/><i>Generated by RIBIF Module 9</i>",
            self.styles['Normal']
        ))
        story.append(PageBreak())
        
        # ========== TABLE OF CONTENTS ==========
        print("📄 Building table of contents...")
        story.append(Paragraph("TABLE OF CONTENTS", self.styles['ChapterTitle']))
        story.append(Spacer(1, 0.5*cm))
        
        toc_items = [
            ("1", "Industry Overview"),
            ("2", "Process Architecture"),
            ("3", "Machine Families"),
            ("4", "Technical Product Families"),
            ("5", "Supply Chain"),
            ("6", "Digital Twin"),
            ("7", "Annexes")
        ]
        
        toc_data = [["Chapter", "Title"]] + toc_items
        toc_table = Table(toc_data, colWidths=[2*cm, 14*cm])
        toc_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ]))
        story.append(toc_table)
        story.append(PageBreak())
        
        # ========== CHAPTER 1: INDUSTRY OVERVIEW ==========
        self.chapter_num += 1
        print(f"📄 Chapter {self.chapter_num}: Industry Overview...")
        
        story.append(Paragraph(f"CHAPTER {self.chapter_num}", self.styles['ChapterTitle']))
        story.append(Paragraph("INDUSTRY OVERVIEW", self.styles['ChapterTitle']))
        story.append(Spacer(1, 0.5*cm))
        
        intro = self.generate_chapter_intro("Industry Overview", 
                                            "Industrial domain and positioning", project_info)
        story.append(Paragraph(intro, self.styles['BookBody']))
        
        # Site overview image
        site_img = catalog_images.get('site_overview')
        if site_img:
            story.extend(self.get_image_for_pdf(site_img, caption="Industrial Site Overview"))
        
        # Industrial identification table
        self.table_num += 1
        story.append(Paragraph(f"Table {self.table_num}: Industrial Identification", self.styles['TableCaption']))
        
        id_data = [
            ["Parameter", "Value"],
            ["Project Name", project_name],
            ["Company", company_name],
            ["Sector", sector], 
            ["Location", f"{project_info.get('localisation', {}).get('ville', 'N/A')}, {project_info.get('localisation', {}).get('pays', 'N/A')}"],
            ["Scale", project_info.get('taille_projet', {}).get('echelle', 'N/A')],
        ]
        
        id_table = Table(id_data, colWidths=[6*cm, 10*cm])
        id_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
        ]))
        story.append(id_table)
        story.append(PageBreak())
        
        # ========== CHAPTER 2: PROCESS ARCHITECTURE ==========
        self.chapter_num += 1
        print(f"📄 Chapter {self.chapter_num}: Process Architecture...")
        
        story.append(Paragraph(f"CHAPTER {self.chapter_num}", self.styles['ChapterTitle']))
        story.append(Paragraph("PROCESS ARCHITECTURE", self.styles['ChapterTitle']))
        story.append(Spacer(1, 0.5*cm))
        
        intro = self.generate_chapter_intro("Process Architecture",
                                            "Production workflows", {"steps": len(processes)})
        story.append(Paragraph(intro, self.styles['BookBody']))
        
        # Process flow diagram
        flow_img = catalog_images.get('process_flow')
        if flow_img:
            story.extend(self.get_image_for_pdf(flow_img, caption="Complete Process Flow Diagram"))
        
        # Process steps
        for idx, step in enumerate(processes, 1):
            story.append(Paragraph(f"2.{idx} {step.get('nom_etape', 'Step')}", self.styles['SectionTitle']))
            story.append(Paragraph(
                f"<b>Type:</b> {step.get('type_operation', 'N/A')}<br/>"
                f"<b>Description:</b> {step.get('description', 'N/A')}",
                self.styles['BookBody']
            ))
            
            # Step image
            step_img = step.get('images', {}).get('workflow') or step.get('image')
            if step_img:
                story.extend(self.get_image_for_pdf(step_img, max_width=12*cm, max_height=8*cm,
                                                     caption=f"{step.get('nom_etape', 'Step')} Workflow"))
            story.append(Spacer(1, 0.3*cm))
        
        story.append(PageBreak())
        
        # ========== CHAPTER 3: MACHINE FAMILIES ==========
        self.chapter_num += 1
        print(f"📄 Chapter {self.chapter_num}: Machine Families...")
        
        story.append(Paragraph(f"CHAPTER {self.chapter_num}", self.styles['ChapterTitle']))
        story.append(Paragraph("MACHINE FAMILIES", self.styles['ChapterTitle']))
        story.append(Spacer(1, 0.5*cm))
        
        intro = self.generate_chapter_intro("Machine Families",
                                            "Production equipment", {"count": len(machines)})
        story.append(Paragraph(intro, self.styles['BookBody']))
        
        for idx, machine in enumerate(machines, 1):
            machine_name = machine.get('nom_machine', 'Machine')
            machine_images = machine.get('images', {})
            specs = machine.get('specifications', {})
            perf = machine.get('performance', {})
            
            story.append(Paragraph(f"3.{idx} {machine_name}", self.styles['SectionTitle']))
            
            # Main machine photo
            main_img = machine_images.get('photo') or machine_images.get('main') or machine.get('image')
            if main_img:
                story.extend(self.get_image_for_pdf(main_img, max_width=14*cm, max_height=10*cm,
                                                     caption=f"{machine_name} - Equipment Overview"))
            
            # Specifications table
            self.table_num += 1
            story.append(Paragraph(f"Table {self.table_num}: {machine_name} Specifications", self.styles['TableCaption']))
            
            spec_data = [
                ["Specification", "Value"],
                ["Manufacturer", machine.get('fabricant_recommande', 'N/A')],
                ["Quantity", str(machine.get('quantite_necessaire', 'N/A'))],
                ["Capacity", specs.get('capacite', 'N/A')],
                ["Power", specs.get('puissance', 'N/A')],
                ["Production Rate", perf.get('cadence', 'N/A')],
                ["Efficiency", perf.get('rendement', 'N/A')],
            ]
            
            spec_table = Table(spec_data, colWidths=[6*cm, 10*cm])
            spec_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ecf0f1')])
            ]))
            story.append(spec_table)
            
            # 3D Model
            model_3d = machine_images.get('3d_model') or machine_images.get('model_3d')
            if model_3d:
                story.extend(self.get_image_for_pdf(model_3d, max_width=12*cm, max_height=9*cm,
                                                     caption=f"{machine_name} - 3D Model View"))
            
            # 2D Plan
            plan_2d = machine_images.get('2d_plan') or machine_images.get('plan_2d') or machine_images.get('technical_drawing')
            if plan_2d:
                story.extend(self.get_image_for_pdf(plan_2d, max_width=14*cm, max_height=10*cm,
                                                     caption=f"{machine_name} - Technical Drawing"))
            
            story.append(Spacer(1, 0.5*cm))
        
        story.append(PageBreak())
        
        # ========== CHAPTER 4: PRODUCTS ==========
        self.chapter_num += 1
        print(f"📄 Chapter {self.chapter_num}: Product Families...")
        
        story.append(Paragraph(f"CHAPTER {self.chapter_num}", self.styles['ChapterTitle']))
        story.append(Paragraph("TECHNICAL PRODUCT FAMILIES", self.styles['ChapterTitle']))
        story.append(Spacer(1, 0.5*cm))
        
        for idx, product in enumerate(products, 1):
            product_name = product.get('nom_produit', 'Product')
            product_images = product.get('images', {})
            specs = product.get('specifications_techniques', {})
            
            story.append(Paragraph(f"4.{idx} {product_name}", self.styles['SectionTitle']))
            
            # Product photo
            prod_img = product_images.get('photo') or product_images.get('main') or product.get('image')
            if prod_img:
                story.extend(self.get_image_for_pdf(prod_img, max_width=12*cm, max_height=9*cm,
                                                     caption=f"{product_name} - Product Overview"))
            
            story.append(Paragraph(product.get('description', 'N/A'), self.styles['BookBody']))
            
            # Product schematic
            schematic = product_images.get('schematic') or product_images.get('technical_drawing')
            if schematic:
                story.extend(self.get_image_for_pdf(schematic, max_width=14*cm, max_height=10*cm,
                                                     caption=f"{product_name} - Technical Schematic"))
            
            story.append(Spacer(1, 0.5*cm))
        
        story.append(PageBreak())
        
        # ========== CHAPTER 5: SUPPLY CHAIN ==========
        self.chapter_num += 1
        print(f"📄 Chapter {self.chapter_num}: Supply Chain...")
        
        story.append(Paragraph(f"CHAPTER {self.chapter_num}", self.styles['ChapterTitle']))
        story.append(Paragraph("SUPPLY CHAIN", self.styles['ChapterTitle']))
        story.append(Spacer(1, 0.5*cm))
        
        # Supply chain diagram
        sc_img = catalog_images.get('supply_chain_diagram')
        if sc_img:
            story.extend(self.get_image_for_pdf(sc_img, caption="Supply Chain Network"))
        
        # Materials table
        if materials:
            self.table_num += 1
            story.append(Paragraph(f"Table {self.table_num}: Raw Materials", self.styles['TableCaption']))
            
            mat_data = [["Material", "Type", "Category"]]
            for mat in materials[:10]:
                mat_data.append([
                    mat.get('nom_materiau', 'N/A')[:30],
                    mat.get('type', 'N/A'),
                    mat.get('categorie', 'N/A')
                ])
            
            mat_table = Table(mat_data, colWidths=[6*cm, 5*cm, 5*cm])
            mat_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d35400')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            story.append(mat_table)
        
        story.append(PageBreak())
        
        # ========== CHAPTER 6: DIGITAL TWIN ==========
        self.chapter_num += 1
        print(f"📄 Chapter {self.chapter_num}: Digital Twin...")
        
        story.append(Paragraph(f"CHAPTER {self.chapter_num}", self.styles['ChapterTitle']))
        story.append(Paragraph("DIGITAL TWIN", self.styles['ChapterTitle']))
        story.append(Spacer(1, 0.5*cm))
        
        # Digital twin images
        dt_arch = catalog_images.get('digital_twin_architecture')
        if dt_arch:
            story.extend(self.get_image_for_pdf(dt_arch, caption="Digital Twin Architecture"))
        
        dt_3d = catalog_images.get('factory_3d') or catalog_images.get('digital_twin_3d')
        if dt_3d:
            story.extend(self.get_image_for_pdf(dt_3d, caption="3D Virtual Factory"))
        
        dashboard = catalog_images.get('dashboard') or catalog_images.get('kpi_dashboard')
        if dashboard:
            story.extend(self.get_image_for_pdf(dashboard, caption="Real-Time KPI Dashboard"))
        
        story.append(PageBreak())
        
        # ========== CHAPTER 7: ANNEXES ==========
        self.chapter_num += 1
        print(f"📄 Chapter {self.chapter_num}: Annexes...")
        
        story.append(Paragraph(f"CHAPTER {self.chapter_num}", self.styles['ChapterTitle']))
        story.append(Paragraph("ANNEXES", self.styles['ChapterTitle']))
        story.append(Spacer(1, 0.5*cm))
        
        story.append(Paragraph("Technical Abbreviations", self.styles['SectionTitle']))
        
        abbrev_data = [
            ["Abbr.", "Meaning"],
            ["OEE", "Overall Equipment Effectiveness"],
            ["IoT", "Internet of Things"],
            ["AI", "Artificial Intelligence"],
            ["KPI", "Key Performance Indicator"],
        ]
        
        abbrev_table = Table(abbrev_data, colWidths=[3*cm, 13*cm])
        abbrev_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(abbrev_table)
        
        # Build PDF
        doc.build(story)
        
        print(f"\n✅ PDF generated: {output_path}")
        print(f"   📊 {self.chapter_num} chapters | {self.table_num} tables | {self.figure_num} figures")
        
        return output_path
    
    # ==================== HTML/WEB GENERATION ====================
    
    def generate_web_catalog(self, module1_data: Dict, module4_data: Dict = None,
                            output_path: str = "data/catalogs/industrial_catalog.html"):
        """Generate interactive web catalog with embedded images"""
        print("\n" + "="*60)
        print("🌐 GENERATING WEB CATALOG")
        print("="*60 + "\n")
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Extract data
        project_info = module1_data.get('stage_1_informations_generales', {}).get('informations_generales', {})
        catalog_images = module1_data.get('catalog_images', {})
        machines = module1_data.get('stage_4_machines_equipements', {}).get('machines_production', [])
        products = module1_data.get('stage_3_produits_fabriques', {}).get('produits_fabriques', [])
        processes = module1_data.get('stage_5_processus_production', {}).get('processus_production', [])
        
        project_name = project_info.get('nom_projet', 'Industrial Project')
        company_name = project_info.get('nom_entreprise', 'Company')
        sector = project_info.get('secteur_activite', 'Industrial')
        
        # Build HTML
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
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✅ Web catalog generated: {output_path}")
        return output_path
    
    # ==================== MAIN GENERATION ====================
    
    def generate_catalog(self, module1_path: str, module4_path: str = None,
                        images_config_path: str = None, output_dir: str = "data/catalogs"):
        """Generate both PDF and Web catalogs"""
        print("\n" + "="*60)
        print("📘 RIBIF MODULE 9: CATALOG GENERATOR")
        print("="*60 + "\n")
        
        # Load data
        module1_data, module4_data = self.load_data(module1_path, module4_path, images_config_path)
        
        # Generate filenames
        base = Path(module1_path).stem.replace('_ribif_extracted', '').replace('_extracted', '')
        
        # Generate catalogs
        pdf_path = f"{output_dir}/{base}_catalog.pdf"
        html_path = f"{output_dir}/{base}_catalog.html"
        
        pdf_result = self.generate_pdf_catalog(module1_data, module4_data, pdf_path)
        html_result = self.generate_web_catalog(module1_data, module4_data, html_path)
        
        print("\n" + "="*60)
        print("✅ CATALOG GENERATION COMPLETE")
        print("="*60)
        print(f"📘 PDF:  {pdf_result}")
        print(f"🌐 HTML: {html_result}")
        
        return {"pdf": pdf_result, "html": html_result}


# ==================== SAMPLE DATA STRUCTURE ====================

SAMPLE_IMAGES_CONFIG = '''
{
    "catalog_images": {
        "company_logo": "logos/company_logo.png",
        "cover_image": "covers/factory_hero.jpg",
        "site_overview": "site/aerial_view.jpg",
        "process_flow": "diagrams/process_flow.png",
        "supply_chain_diagram": "diagrams/supply_chain.png",
        "digital_twin_architecture": "diagrams/dt_architecture.png",
        "factory_3d": "3d/factory_render.png",
        "dashboard": "screenshots/kpi_dashboard.png"
    },
    "machines": {
        "CNC Milling Machine": {
            "photo": "machines/cnc_photo.jpg",
            "3d_model": "machines/cnc_3d_render.png",
            "2d_plan": "machines/cnc_technical_drawing.png"
        },
        "Hydraulic Press": {
            "photo": "machines/press_photo.jpg",
            "3d_model": "machines/press_3d.png",
            "2d_plan": "machines/press_drawing.pdf"
        }
    },
    "products": {
        "Steel Component A": {
            "photo": "products/component_a.jpg",
            "schematic": "products/component_a_schematic.png"
        }
    },
    "processes": {
        "Cutting": {
            "workflow": "processes/cutting_workflow.png"
        },
        "Assembly": {
            "workflow": "processes/assembly_workflow.png"
        }
    }
}
'''


def main():
    """Main entry point"""
    print("\n" + "="*60)
    print("📘 RIBIF MODULE 9: INDUSTRIAL CATALOG GENERATOR")
    print("   LaTeX Template-Based PDF Generation")
    print("="*60 + "\n")
    
    # Input files
    ribif_file = "data/extracted_data/FICHE_IDENTITE_INDUSTRIELLE_ribif_extracted.json"
    input_file = "data/extracted_data/input.json"
    template_file = "main.tex"
    output_pdf = "data/catalogs/catalog_output.pdf"
    
    # Check required files
    if not os.path.exists(ribif_file):
        print(f"❌ RIBIF data not found: {ribif_file}")
        return
    
    if not os.path.exists(input_file):
        print(f"❌ Input data not found: {input_file}")
        return
    
    if not os.path.exists(template_file):
        print(f"❌ LaTeX template not found: {template_file}")
        return
    
    # Initialize generator
    generator = IndustrialCatalogGenerator(image_base_path="data/images")
    
    # Generate PDF from template
    result = generator.generate_pdf_from_template(
        ribif_path=ribif_file,
        input_path=input_file,
        output_path=output_pdf,
        template_path=template_file
    )
    
    if result:
        print("\n🎉 Done! Your catalog PDF is ready.")
    else:
        print("\n❌ PDF generation failed.")


if __name__ == "__main__":
    main()
