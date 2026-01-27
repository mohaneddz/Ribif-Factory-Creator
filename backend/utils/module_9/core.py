"""
RIBIF Module 9: HTML-based Catalog Generator
Generates PDF catalogs from Module 1 data using HTML-to-PDF conversion.
Serverless-compatible using xhtml2pdf (pure Python).
"""

from __future__ import annotations

import base64
import logging
import re
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, Optional

from dotenv import load_dotenv
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class CatalogInput(BaseModel):
    """Input for catalog generation"""
    module1_data: Dict[str, Any]
    module4_data: Optional[Dict[str, Any]] = None
    images_config: Optional[Dict[str, Any]] = None
    output_dir: str = "data/catalogs"
    output_format: str = "both"
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


class RIBIFModule9Catalog:
    """
    Industrial catalog generator using HTML-to-PDF conversion.
    Serverless-compatible, no external system dependencies.
    """

    def __init__(self, image_base_path: str = "data"):
        load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")
        self.image_base_path = image_base_path

    def _escape_html(self, text: Any) -> str:
        """Escape HTML special characters."""
        if text is None:
            return ""
        s = str(text)
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    def _get_image_base64(self, url: str) -> Optional[str]:
        """Download image and return as base64 data URI."""
        if not url or not url.startswith("http"):
            return None
        try:
            import requests
            from PIL import Image
            resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200:
                img = Image.open(BytesIO(resp.content))
                if img.mode in ("RGBA", "P", "LA"):
                    img = img.convert("RGB")
                buf = BytesIO()
                img.save(buf, format="JPEG", quality=85)
                b64 = base64.b64encode(buf.getvalue()).decode()
                return f"data:image/jpeg;base64,{b64}"
        except Exception as e:
            logger.warning(f"Failed to fetch image {url}: {e}")
        return None

    def _generate_html_catalog(self, module1_data: Dict, module4_data: Dict = None) -> str:
        """Generate complete HTML catalog with xhtml2pdf-compatible CSS."""
        
        # Extract data
        project_info = module1_data.get('stage_1_informations_generales', {}).get('informations_generales', {})
        machines = module1_data.get('stage_4_machines_equipements', {}).get('machines_production', [])
        products = module1_data.get('stage_3_produits_fabriques', {}).get('produits_fabriques', [])
        processes = module1_data.get('stage_5_processus_production', {}).get('processus_production', [])
        
        project_name = self._escape_html(project_info.get('nom_projet', 'Industrial Project'))
        company_name = self._escape_html(project_info.get('nom_entreprise', 'Company'))
        sector = self._escape_html(project_info.get('secteur_activite', 'Industrial'))
        description = self._escape_html(project_info.get('description_projet', ''))
        objectives = project_info.get('objectifs_strategiques', []) or []
        date_str = datetime.now().strftime("%B %Y")

        # Build machine images lookup from module4
        machine_images = {}
        if module4_data:
            for item in module4_data.get('machines_enriched', []):
                m_input = item.get('machine_input', {})
                name = (m_input.get('nom_machine') or '').lower().strip()
                img_url = m_input.get('best_image_url', '')
                if not img_url:
                    assets = m_input.get('assets', {})
                    urls = assets.get('image_urls', []) if isinstance(assets, dict) else []
                    img_url = urls[0] if urls else ''
                if name and img_url:
                    machine_images[name] = img_url

        # xhtml2pdf compatible CSS - using simple properties only
        html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
@page {{
    size: A4;
    margin: 1.5cm;
    @frame footer {{
        -pdf-frame-content: footerContent;
        bottom: 0.5cm;
        margin-left: 1cm;
        margin-right: 1cm;
        height: 1cm;
    }}
}}
body {{
    font-family: Helvetica, Arial, sans-serif;
    font-size: 10pt;
    color: #1e293b;
    line-height: 1.5;
}}

/* Cover styles */
.cover-page {{
    background-color: #0f172a;
    color: white;
    padding: 60px 40px;
    margin: -1.5cm;
    margin-bottom: 0;
    min-height: 800px;
}}
.cover-series {{
    font-size: 11pt;
    letter-spacing: 3px;
    color: #94a3b8;
    margin-bottom: 30px;
}}
.cover-version {{
    font-size: 72pt;
    font-weight: bold;
    color: #4f46e5;
    margin-bottom: 20px;
}}
.cover-title {{
    font-size: 32pt;
    font-weight: bold;
    line-height: 1.2;
    margin-bottom: 60px;
}}
.cover-meta-table {{
    width: 100%;
    background-color: white;
    color: #1e293b;
    margin-top: 80px;
}}
.cover-meta-table td {{
    padding: 15px 20px;
    border-right: 1px solid #e2e8f0;
}}
.cover-meta-table td:last-child {{
    border-right: none;
}}
.meta-label {{
    font-size: 9pt;
    color: #64748b;
    font-weight: bold;
}}
.meta-value {{
    font-size: 11pt;
    font-weight: bold;
}}

/* Section header */
.section-header {{
    margin-bottom: 20px;
    margin-top: 30px;
}}
.section-header table {{
    width: 100%;
    border-collapse: collapse;
}}
.section-num {{
    background-color: #4f46e5;
    color: white;
    font-size: 20pt;
    font-weight: bold;
    padding: 10px 15px;
    width: 60px;
    text-align: center;
}}
.section-title-cell {{
    background-color: #0f172a;
    color: white;
    font-size: 12pt;
    font-weight: bold;
    padding: 10px 20px;
    letter-spacing: 1px;
}}

/* Content styles */
h3 {{
    color: #0f172a;
    font-size: 12pt;
    border-bottom: 2px solid #4f46e5;
    padding-bottom: 5px;
    margin-top: 20px;
    margin-bottom: 10px;
}}
p {{
    margin-bottom: 10px;
    text-align: justify;
}}
ul {{
    margin-left: 20px;
    margin-bottom: 15px;
}}
li {{
    margin-bottom: 5px;
}}

/* Tables */
.data-table {{
    width: 100%;
    border-collapse: collapse;
    margin: 15px 0;
}}
.data-table th {{
    background-color: #0f172a;
    color: white;
    padding: 10px;
    text-align: left;
    font-size: 10pt;
}}
.data-table td {{
    padding: 8px 10px;
    border-bottom: 1px solid #e2e8f0;
    font-size: 9pt;
}}
.data-table tr:nth-child(even) td {{
    background-color: #f8fafc;
}}

/* Machine cards */
.machine-card {{
    border: 1px solid #cbd5e1;
    margin-bottom: 15px;
    page-break-inside: avoid;
}}
.machine-header {{
    background-color: #4f46e5;
    color: white;
    padding: 8px 12px;
    font-weight: bold;
}}
.machine-body {{
    padding: 10px;
}}
.machine-body table {{
    width: 100%;
}}
.machine-body td {{
    padding: 4px 8px;
    vertical-align: top;
}}
.machine-img {{
    width: 100px;
    height: 75px;
    background-color: #f1f5f9;
    border: 1px dashed #cbd5e1;
    text-align: center;
    vertical-align: middle;
    color: #94a3b8;
    font-size: 9pt;
}}
.machine-img img {{
    max-width: 100px;
    max-height: 75px;
}}
.spec-table {{
    width: 100%;
}}
.spec-table td {{
    padding: 3px 5px;
    font-size: 9pt;
}}
.spec-label {{
    font-weight: bold;
    width: 100px;
}}

/* Process flow */
.flow-table {{
    width: 100%;
    margin: 15px 0;
}}
.flow-step {{
    border: 2px solid #0f172a;
    padding: 10px;
    text-align: center;
    width: 16%;
}}
.flow-step-last {{
    background-color: #0f172a;
    color: white;
    border: 2px solid #0f172a;
    padding: 10px;
    text-align: center;
    width: 16%;
}}
.flow-num {{
    font-size: 8pt;
    color: #64748b;
}}
.flow-name {{
    font-weight: bold;
    font-size: 9pt;
}}

/* Pillars */
.pillars-container {{
    border: 2px solid #0f172a;
    margin: 20px 0;
}}
.pillars-header {{
    background-color: #0f172a;
    color: white;
    padding: 10px;
    text-align: center;
    font-weight: bold;
}}
.pillars-body {{
    width: 100%;
}}
.pillar {{
    width: 33%;
    padding: 15px;
    vertical-align: top;
    border-right: 1px solid #e2e8f0;
}}
.pillar:last-child {{
    border-right: none;
}}
.pillar-title {{
    background-color: #4f46e5;
    color: white;
    padding: 5px 10px;
    text-align: center;
    font-weight: bold;
    font-size: 9pt;
    margin-bottom: 10px;
}}
.pillar-text {{
    font-size: 9pt;
    text-align: center;
}}

/* Footer */
.doc-footer {{
    text-align: center;
    font-size: 9pt;
    color: #64748b;
    border-top: 1px solid #0f172a;
    padding-top: 10px;
    margin-top: 30px;
}}

/* Page break */
.page-break {{
    page-break-before: always;
}}
</style>
</head>
<body>

<!-- COVER PAGE -->
<div class="cover-page">
    <div class="cover-series">TECHNICAL DOCUMENTATION SERIES</div>
    <div class="cover-version">5.0</div>
    <div class="cover-title">DIGITAL TWIN<br/>&amp; PROCESS<br/>CATALOGUE</div>
    
    <table class="cover-meta-table">
        <tr>
            <td>
                <div class="meta-label">PROJECT</div>
                <div class="meta-value">{project_name[:35]}</div>
            </td>
            <td>
                <div class="meta-label">DATE</div>
                <div class="meta-value">{date_str.upper()}</div>
            </td>
            <td>
                <div class="meta-label">SECTOR</div>
                <div class="meta-value">{sector[:25]}</div>
            </td>
        </tr>
    </table>
</div>

<!-- SECTION 01: PROCESS & WORKFLOW -->
<div class="page-break"></div>
<div class="section-header">
    <table><tr>
        <td class="section-num">01</td>
        <td class="section-title-cell">PROCESS &amp; WORKFLOW</td>
    </tr></table>
</div>

<h3>Operational Overview</h3>
<p>{description or f"This catalog presents comprehensive technical documentation for {project_name}, operated by {company_name}."}</p>
'''

        if objectives:
            html += '<h3>Key Objectives</h3><ul>'
            for obj in objectives[:5]:
                if isinstance(obj, str):
                    html += f'<li>{self._escape_html(obj)}</li>'
            html += '</ul>'

        html += '''
<div class="pillars-container">
    <div class="pillars-header">CORE PILLARS</div>
    <table class="pillars-body">
        <tr>
            <td class="pillar">
                <div class="pillar-title">1. AUTOMATION</div>
                <div class="pillar-text">Streamlined production workflows with minimal manual intervention.</div>
            </td>
            <td class="pillar">
                <div class="pillar-title">2. CONNECTIVITY</div>
                <div class="pillar-text">Integrated systems for real-time monitoring and analytics.</div>
            </td>
            <td class="pillar">
                <div class="pillar-title">3. SUSTAINABILITY</div>
                <div class="pillar-text">Eco-friendly processes that reduce waste and optimize energy.</div>
            </td>
        </tr>
    </table>
</div>

<!-- SECTION 02: PROCESS ARCHITECTURE -->
<div class="page-break"></div>
<div class="section-header">
    <table><tr>
        <td class="section-num">02</td>
        <td class="section-title-cell">PROCESS ARCHITECTURE</td>
    </tr></table>
</div>

<h3>Workflow Description</h3>
<p>The manufacturing process follows a structured workflow designed for optimal efficiency and quality control.</p>

<table class="flow-table">
    <tr>
'''
        
        if processes:
            for idx, proc in enumerate(processes, 1):
                name = self._escape_html(proc.get('nom_etape', proc.get('nom', f'Step {idx}')))[:20]
                is_last = idx == len(processes)
                cls = 'flow-step-last' if is_last else 'flow-step'
                html += f'<td class="{cls}"><div class="flow-num">STEP {idx:02d}</div><div class="flow-name">{name}</div></td>'
        else:
            for i, name in enumerate(['INPUT', 'PROCESS', 'TRANSFORM', 'QUALITY', 'FINISH', 'OUTPUT'], 1):
                cls = 'flow-step-last' if i == 6 else 'flow-step'
                html += f'<td class="{cls}"><div class="flow-num">STEP {i:02d}</div><div class="flow-name">{name}</div></td>'

        html += '''
    </tr>
</table>

<!-- SECTION 03: MACHINE ASSETS -->
<div class="page-break"></div>
<div class="section-header">
    <table><tr>
        <td class="section-num">03</td>
        <td class="section-title-cell">MACHINE ASSETS</td>
    </tr></table>
</div>

<p>Equipment inventory detailing the primary manufacturing assets deployed in this facility.</p>
'''

        for idx, machine in enumerate(machines, 1):
            m_name = self._escape_html(machine.get('nom_machine', f'Machine {idx}'))
            m_type = self._escape_html(machine.get('type', machine.get('categorie', 'Equipment')))
            specs = machine.get('specifications', {}) if isinstance(machine.get('specifications'), dict) else {}
            manufacturer = self._escape_html(specs.get('fabricant', specs.get('manufacturer', 'N/A')))
            capacity = self._escape_html(str(specs.get('capacite', specs.get('capacity', 'Standard'))))
            power = self._escape_html(str(specs.get('puissance', specs.get('power', 'Standard'))))
            
            # Try to get machine image
            img_cell = '<td class="machine-img">[Photo]</td>'
            img_key = m_name.lower().strip()
            if img_key in machine_images:
                b64 = self._get_image_base64(machine_images[img_key])
                if b64:
                    img_cell = f'<td class="machine-img"><img src="{b64}"/></td>'
            
            html += f'''
<div class="machine-card">
    <div class="machine-header">{m_name[:30]} - {m_type[:20]}</div>
    <div class="machine-body">
        <table>
            <tr>
                {img_cell}
                <td>
                    <table class="spec-table">
                        <tr><td class="spec-label">Manufacturer</td><td>{manufacturer[:25]}</td></tr>
                        <tr><td class="spec-label">Capacity</td><td>{capacity[:20]}</td></tr>
                        <tr><td class="spec-label">Power</td><td>{power[:20]}</td></tr>
                        <tr><td class="spec-label">Status</td><td><b>Operational</b></td></tr>
                    </table>
                </td>
            </tr>
        </table>
    </div>
</div>
'''

        if not machines:
            html += '<p><i>Machine inventory to be populated based on equipment specifications.</i></p>'

        html += '''
<!-- SECTION 04: PRODUCT CATALOG -->
<div class="page-break"></div>
<div class="section-header">
    <table><tr>
        <td class="section-num">04</td>
        <td class="section-title-cell">PRODUCT CATALOG</td>
    </tr></table>
</div>

<p>Manufactured items, specifications, and material composition.</p>

<table class="data-table">
    <tr>
        <th>REF</th>
        <th>PRODUCT NAME</th>
        <th>MATERIAL</th>
        <th>CATEGORY</th>
    </tr>
'''

        if products:
            for idx, prod in enumerate(products, 1):
                p_name = self._escape_html(prod.get('nom_produit', f'Product {idx}'))[:30]
                p_cat = self._escape_html(prod.get('categorie', 'Type'))[:15]
                p_mat = prod.get('materiaux', prod.get('composition', 'Standard'))
                if isinstance(p_mat, list):
                    p_mat = ', '.join(str(m)[:12] for m in p_mat[:2])
                else:
                    p_mat = self._escape_html(str(p_mat))[:25]
                html += f'<tr><td><b>P-{idx:03d}</b></td><td><b>{p_name}</b></td><td>{p_mat}</td><td>{p_cat}</td></tr>'
        else:
            html += '<tr><td>P-001</td><td>Sample Product</td><td>Standard</td><td>Type A</td></tr>'

        html += '''
</table>

<!-- SECTION 05: LOGISTICS -->
<div class="page-break"></div>
<div class="section-header">
    <table><tr>
        <td class="section-num">05</td>
        <td class="section-title-cell">LOGISTICS &amp; SUPPLY CHAIN</td>
    </tr></table>
</div>

<h3>Inbound Flow</h3>
<p>Raw materials and components are sourced from qualified suppliers and delivered following strict quality protocols.</p>
<ul>
    <li><b>Supplier Management:</b> Qualified vendor network with regular audits</li>
    <li><b>Quality Rate:</b> 98% acceptance rate on incoming materials</li>
</ul>

<h3>Outbound Flow</h3>
<p>Finished products are packaged, labeled, and distributed through established logistics channels.</p>
<ul>
    <li><b>Distribution:</b> Daily shipments via certified carriers</li>
    <li><b>Lead Time:</b> 48h average delivery time</li>
</ul>

<!-- SECTION 06: DIGITAL TWIN -->
<div class="page-break"></div>
<div class="section-header">
    <table><tr>
        <td class="section-num">06</td>
        <td class="section-title-cell">DIGITAL TWIN INTERFACE</td>
    </tr></table>
</div>

<h3>Interface Guide: Twin Manager v5.0</h3>
<p>The Digital Twin interface provides real-time, browser-based supervision of the factory floor using <b>React.js</b> and <b>Three.js</b> for 3D visualization.</p>

<h3>1. 3D Visualization</h3>
<ul>
    <li><b>Assets:</b> CNC Machines, Robot Arms, Conveyor Belts</li>
    <li><b>Status:</b> Green (Running), Amber (Idle), Red (Warning)</li>
    <li><b>Animation:</b> Real-time sync with production cycle</li>
</ul>

<h3>2. Predictive Maintenance</h3>
<p>Risk Matrix correlating Temperature, Machine Health %, and Vibration levels. Triggers warning if Temperature exceeds 90°C.</p>

<h3>3. TCO Optimization</h3>
<p>Total Cost of Ownership calculator projecting 10-year financial data: CAPEX + Operating Costs + Maintenance.</p>

<h3>4. Safety Monitoring</h3>
<p>Real-time air quality tracking for hazardous zones with automated ventilation control.</p>

<div class="doc-footer">
    <b>{company_name.upper()}</b> &mdash; INTERNAL TECHNICAL REFERENCE &mdash; END OF DOCUMENT
</div>

</body>
</html>'''

        return html

    def _generate_pdf_in_memory(self, module1_data: Dict, module4_data: Dict = None) -> bytes:
        """Generate PDF using reportlab (pure Python, serverless-compatible)."""
        from io import BytesIO
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm, mm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
            PageBreak, Image as RLImage
        )
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
        
        # Extract data
        project_info = module1_data.get('stage_1_informations_generales', {}).get('informations_generales', {})
        machines = module1_data.get('stage_4_machines_equipements', {}).get('machines_production', [])
        products = module1_data.get('stage_3_produits_fabriques', {}).get('produits_fabriques', [])
        processes = module1_data.get('stage_5_processus_production', {}).get('processus_production', [])
        
        project_name = self._escape_html(project_info.get('nom_projet', 'Industrial Project'))
        company_name = self._escape_html(project_info.get('nom_entreprise', 'Company'))
        sector = self._escape_html(project_info.get('secteur_activite', 'Industrial'))
        description = self._escape_html(project_info.get('description_projet', ''))
        objectives = project_info.get('objectifs_strategiques', []) or []
        date_str = datetime.now().strftime("%B %Y")
        
        # Build machine images lookup from module4
        machine_images = {}
        if module4_data:
            for item in module4_data.get('machines_enriched', []):
                m_input = item.get('machine_input', {})
                name = (m_input.get('nom_machine') or '').lower().strip()
                img_url = m_input.get('best_image_url', '')
                if not img_url:
                    assets = m_input.get('assets', {})
                    urls = assets.get('image_urls', []) if isinstance(assets, dict) else []
                    img_url = urls[0] if urls else ''
                if name and img_url:
                    machine_images[name] = img_url
        
        # Create PDF buffer
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4, 
            leftMargin=1.5*cm, 
            rightMargin=1.5*cm,
            topMargin=1.5*cm, 
            bottomMargin=1.5*cm
        )
        
        # Define colors
        dark_blue = colors.HexColor('#0f172a')
        indigo = colors.HexColor('#4f46e5')
        light_gray = colors.HexColor('#f8fafc')
        gray_text = colors.HexColor('#64748b')
        border_gray = colors.HexColor('#e2e8f0')
        
        # Define styles
        styles = getSampleStyleSheet()
        
        style_cover_series = ParagraphStyle(
            'CoverSeries', parent=styles['Normal'],
            fontSize=11, textColor=colors.HexColor('#94a3b8'),
            spaceAfter=20, alignment=TA_LEFT
        )
        style_cover_version = ParagraphStyle(
            'CoverVersion', parent=styles['Normal'],
            fontSize=48, fontName='Helvetica-Bold', textColor=indigo,
            spaceAfter=15, alignment=TA_LEFT
        )
        style_cover_title = ParagraphStyle(
            'CoverTitle', parent=styles['Normal'],
            fontSize=28, fontName='Helvetica-Bold', textColor=colors.white,
            spaceAfter=40, leading=34, alignment=TA_LEFT
        )
        style_section_title = ParagraphStyle(
            'SectionTitle', parent=styles['Normal'],
            fontSize=12, fontName='Helvetica-Bold', textColor=colors.white,
            alignment=TA_LEFT
        )
        style_section_num = ParagraphStyle(
            'SectionNum', parent=styles['Normal'],
            fontSize=18, fontName='Helvetica-Bold', textColor=colors.white,
            alignment=TA_CENTER
        )
        style_h3 = ParagraphStyle(
            'H3', parent=styles['Normal'],
            fontSize=12, fontName='Helvetica-Bold', textColor=dark_blue,
            spaceBefore=15, spaceAfter=8, borderPadding=5
        )
        style_body = ParagraphStyle(
            'Body', parent=styles['Normal'],
            fontSize=10, textColor=dark_blue,
            spaceAfter=8, alignment=TA_JUSTIFY, leading=14
        )
        style_bullet = ParagraphStyle(
            'Bullet', parent=styles['Normal'],
            fontSize=10, textColor=dark_blue,
            leftIndent=20, spaceAfter=5, leading=13
        )
        style_footer = ParagraphStyle(
            'Footer', parent=styles['Normal'],
            fontSize=9, textColor=gray_text, alignment=TA_CENTER
        )
        style_meta_label = ParagraphStyle(
            'MetaLabel', parent=styles['Normal'],
            fontSize=9, fontName='Helvetica-Bold', textColor=gray_text
        )
        style_meta_value = ParagraphStyle(
            'MetaValue', parent=styles['Normal'],
            fontSize=11, fontName='Helvetica-Bold', textColor=dark_blue
        )
        style_table_header = ParagraphStyle(
            'TableHeader', parent=styles['Normal'],
            fontSize=10, fontName='Helvetica-Bold', textColor=colors.white
        )
        style_table_cell = ParagraphStyle(
            'TableCell', parent=styles['Normal'],
            fontSize=9, textColor=dark_blue
        )
        style_pillar_title = ParagraphStyle(
            'PillarTitle', parent=styles['Normal'],
            fontSize=9, fontName='Helvetica-Bold', textColor=colors.white,
            alignment=TA_CENTER
        )
        style_pillar_text = ParagraphStyle(
            'PillarText', parent=styles['Normal'],
            fontSize=9, textColor=dark_blue, alignment=TA_CENTER, leading=12
        )
        style_flow_num = ParagraphStyle(
            'FlowNum', parent=styles['Normal'],
            fontSize=8, textColor=gray_text, alignment=TA_CENTER
        )
        style_flow_name = ParagraphStyle(
            'FlowName', parent=styles['Normal'],
            fontSize=9, fontName='Helvetica-Bold', textColor=dark_blue,
            alignment=TA_CENTER
        )
        
        elements = []
        page_width = A4[0] - 3*cm
        
        # === COVER PAGE ===
        # Dark background table for cover
        cover_content = [
            [Paragraph('TECHNICAL DOCUMENTATION SERIES', style_cover_series)],
            [Paragraph('5.0', style_cover_version)],
            [Paragraph('DIGITAL TWIN<br/>& PROCESS<br/>CATALOGUE', style_cover_title)],
        ]
        cover_table = Table(cover_content, colWidths=[page_width])
        cover_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), dark_blue),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 40),
            ('RIGHTPADDING', (0, 0), (-1, -1), 40),
            ('TOPPADDING', (0, 0), (0, 0), 60),
            ('BOTTOMPADDING', (-1, -1), (-1, -1), 40),
        ]))
        elements.append(cover_table)
        
        # Cover metadata table
        meta_data = [
            [
                [Paragraph('PROJECT', style_meta_label), Paragraph(project_name[:35], style_meta_value)],
                [Paragraph('DATE', style_meta_label), Paragraph(date_str.upper(), style_meta_value)],
                [Paragraph('SECTOR', style_meta_label), Paragraph(sector[:25], style_meta_value)],
            ]
        ]
        meta_cells = []
        for item in meta_data[0]:
            cell_table = Table([[item[0]], [item[1]]], colWidths=[page_width/3 - 10])
            meta_cells.append(cell_table)
        
        meta_table = Table([meta_cells], colWidths=[page_width/3]*3)
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
            ('RIGHTPADDING', (0, 0), (-1, -1), 15),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('LINEAFTER', (0, 0), (1, -1), 1, border_gray),
        ]))
        elements.append(Spacer(1, 80))
        elements.append(meta_table)
        
        # Helper function for section headers
        def add_section_header(num: str, title: str):
            header_data = [[
                Paragraph(num, style_section_num),
                Paragraph(title, style_section_title)
            ]]
            header_table = Table(header_data, colWidths=[60, page_width - 60])
            header_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, 0), indigo),
                ('BACKGROUND', (1, 0), (1, 0), dark_blue),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 15),
                ('RIGHTPADDING', (0, 0), (-1, -1), 15),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ]))
            elements.append(header_table)
            elements.append(Spacer(1, 15))
        
        # === SECTION 01: PROCESS & WORKFLOW ===
        elements.append(PageBreak())
        add_section_header('01', 'PROCESS & WORKFLOW')
        
        elements.append(Paragraph('Operational Overview', style_h3))
        desc_text = description or f"This catalog presents comprehensive technical documentation for {project_name}, operated by {company_name}."
        elements.append(Paragraph(desc_text, style_body))
        
        if objectives:
            elements.append(Paragraph('Key Objectives', style_h3))
            for obj in objectives[:5]:
                if isinstance(obj, str):
                    elements.append(Paragraph(f"• {self._escape_html(obj)}", style_bullet))
        
        # Core Pillars
        elements.append(Spacer(1, 20))
        pillar_header = [[Paragraph('CORE PILLARS', ParagraphStyle('PillarHeader', parent=styles['Normal'], fontSize=11, fontName='Helvetica-Bold', textColor=colors.white, alignment=TA_CENTER))]]
        pillar_header_table = Table(pillar_header, colWidths=[page_width])
        pillar_header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), dark_blue),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(pillar_header_table)
        
        pillars = [
            ('1. AUTOMATION', 'Streamlined production workflows with minimal manual intervention.'),
            ('2. CONNECTIVITY', 'Integrated systems for real-time monitoring and analytics.'),
            ('3. SUSTAINABILITY', 'Eco-friendly processes that reduce waste and optimize energy.'),
        ]
        pillar_cells = []
        for title, text in pillars:
            title_p = Paragraph(title, style_pillar_title)
            text_p = Paragraph(text, style_pillar_text)
            title_table = Table([[title_p]], colWidths=[page_width/3 - 20])
            title_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), indigo),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            cell = Table([[title_table], [text_p]], colWidths=[page_width/3 - 20])
            cell.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 1), (-1, -1), 10),
            ]))
            pillar_cells.append(cell)
        
        pillars_table = Table([pillar_cells], colWidths=[page_width/3]*3)
        pillars_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 2, dark_blue),
            ('LINEAFTER', (0, 0), (1, -1), 1, border_gray),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 15),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
        ]))
        elements.append(pillars_table)
        
        # === SECTION 02: PROCESS ARCHITECTURE ===
        elements.append(PageBreak())
        add_section_header('02', 'PROCESS ARCHITECTURE')
        
        elements.append(Paragraph('Workflow Description', style_h3))
        elements.append(Paragraph('The manufacturing process follows a structured workflow designed for optimal efficiency and quality control.', style_body))
        
        # Flow steps
        if processes:
            flow_data = []
            for idx, proc in enumerate(processes, 1):
                name = self._escape_html(proc.get('nom_etape', proc.get('nom', f'Step {idx}')))[:20]
                flow_data.append((f'STEP {idx:02d}', name, idx == len(processes)))
        else:
            flow_data = [
                ('STEP 01', 'INPUT', False),
                ('STEP 02', 'PROCESS', False),
                ('STEP 03', 'TRANSFORM', False),
                ('STEP 04', 'QUALITY', False),
                ('STEP 05', 'FINISH', False),
                ('STEP 06', 'OUTPUT', True),
            ]
        
        flow_cells = []
        col_width = page_width / len(flow_data) if flow_data else page_width / 6
        for step_num, step_name, is_last in flow_data:
            num_style = ParagraphStyle('FlowNumLast' if is_last else 'FlowNum', parent=style_flow_num, textColor=colors.white if is_last else gray_text)
            name_style = ParagraphStyle('FlowNameLast' if is_last else 'FlowName', parent=style_flow_name, textColor=colors.white if is_last else dark_blue)
            cell_table = Table([
                [Paragraph(step_num, num_style)],
                [Paragraph(step_name, name_style)]
            ], colWidths=[col_width - 10])
            cell_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), dark_blue if is_last else colors.white),
                ('BOX', (0, 0), (-1, -1), 2, dark_blue),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            flow_cells.append(cell_table)
        
        flow_table = Table([flow_cells], colWidths=[col_width]*len(flow_data))
        flow_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(Spacer(1, 15))
        elements.append(flow_table)
        
        # === SECTION 03: MACHINE ASSETS ===
        elements.append(PageBreak())
        add_section_header('03', 'MACHINE ASSETS')
        
        elements.append(Paragraph('Equipment inventory detailing the primary manufacturing assets deployed in this facility.', style_body))
        
        for idx, machine in enumerate(machines, 1):
            m_name = self._escape_html(machine.get('nom_machine', f'Machine {idx}'))
            m_type = self._escape_html(machine.get('type', machine.get('categorie', 'Equipment')))
            specs = machine.get('specifications', {}) if isinstance(machine.get('specifications'), dict) else {}
            manufacturer = self._escape_html(specs.get('fabricant', specs.get('manufacturer', 'N/A')))
            capacity = self._escape_html(str(specs.get('capacite', specs.get('capacity', 'Standard'))))
            power = self._escape_html(str(specs.get('puissance', specs.get('power', 'Standard'))))
            
            # Machine header
            m_header = [[Paragraph(f"{m_name[:30]} - {m_type[:20]}", ParagraphStyle('MachineHeader', parent=styles['Normal'], fontSize=10, fontName='Helvetica-Bold', textColor=colors.white))]]
            m_header_table = Table(m_header, colWidths=[page_width])
            m_header_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), indigo),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            elements.append(m_header_table)
            
            # Machine specs
            spec_data = [
                ['Manufacturer', manufacturer[:25]],
                ['Capacity', capacity[:20]],
                ['Power', power[:20]],
                ['Status', 'Operational'],
            ]
            spec_table_cells = []
            for label, value in spec_data:
                spec_table_cells.append([
                    Paragraph(f"<b>{label}</b>", style_table_cell),
                    Paragraph(value, style_table_cell)
                ])
            
            spec_table = Table(spec_table_cells, colWidths=[100, page_width - 120])
            spec_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            
            body_table = Table([[spec_table]], colWidths=[page_width])
            body_table.setStyle(TableStyle([
                ('BOX', (0, 0), (-1, -1), 1, border_gray),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ]))
            elements.append(body_table)
            elements.append(Spacer(1, 10))
        
        if not machines:
            elements.append(Paragraph('<i>Machine inventory to be populated based on equipment specifications.</i>', style_body))
        
        # === SECTION 04: PRODUCT CATALOG ===
        elements.append(PageBreak())
        add_section_header('04', 'PRODUCT CATALOG')
        
        elements.append(Paragraph('Manufactured items, specifications, and material composition.', style_body))
        
        # Product table
        product_header = [
            Paragraph('REF', style_table_header),
            Paragraph('PRODUCT NAME', style_table_header),
            Paragraph('MATERIAL', style_table_header),
            Paragraph('CATEGORY', style_table_header),
        ]
        product_data = [product_header]
        
        if products:
            for idx, prod in enumerate(products, 1):
                p_name = self._escape_html(prod.get('nom_produit', f'Product {idx}'))[:30]
                p_cat = self._escape_html(prod.get('categorie', 'Type'))[:15]
                p_mat = prod.get('materiaux', prod.get('composition', 'Standard'))
                if isinstance(p_mat, list):
                    p_mat = ', '.join(str(m)[:12] for m in p_mat[:2])
                else:
                    p_mat = self._escape_html(str(p_mat))[:25]
                product_data.append([
                    Paragraph(f"<b>P-{idx:03d}</b>", style_table_cell),
                    Paragraph(f"<b>{p_name}</b>", style_table_cell),
                    Paragraph(p_mat, style_table_cell),
                    Paragraph(p_cat, style_table_cell),
                ])
        else:
            product_data.append([
                Paragraph('P-001', style_table_cell),
                Paragraph('Sample Product', style_table_cell),
                Paragraph('Standard', style_table_cell),
                Paragraph('Type A', style_table_cell),
            ])
        
        product_table = Table(product_data, colWidths=[60, page_width*0.35, page_width*0.3, page_width*0.2])
        product_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), dark_blue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LINEBELOW', (0, 1), (-1, -1), 1, border_gray),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, light_gray]),
        ]))
        elements.append(Spacer(1, 10))
        elements.append(product_table)
        
        # === SECTION 05: LOGISTICS ===
        elements.append(PageBreak())
        add_section_header('05', 'LOGISTICS & SUPPLY CHAIN')
        
        elements.append(Paragraph('Inbound Flow', style_h3))
        elements.append(Paragraph('Raw materials and components are sourced from qualified suppliers and delivered following strict quality protocols.', style_body))
        elements.append(Paragraph('• <b>Supplier Management:</b> Qualified vendor network with regular audits', style_bullet))
        elements.append(Paragraph('• <b>Quality Rate:</b> 98% acceptance rate on incoming materials', style_bullet))
        
        elements.append(Paragraph('Outbound Flow', style_h3))
        elements.append(Paragraph('Finished products are packaged, labeled, and distributed through established logistics channels.', style_body))
        elements.append(Paragraph('• <b>Distribution:</b> Daily shipments via certified carriers', style_bullet))
        elements.append(Paragraph('• <b>Lead Time:</b> 48h average delivery time', style_bullet))
        
        # === SECTION 06: DIGITAL TWIN ===
        elements.append(PageBreak())
        add_section_header('06', 'DIGITAL TWIN INTERFACE')
        
        elements.append(Paragraph('Interface Guide: Twin Manager v5.0', style_h3))
        elements.append(Paragraph('The Digital Twin interface provides real-time, browser-based supervision of the factory floor using <b>React.js</b> and <b>Three.js</b> for 3D visualization.', style_body))
        
        elements.append(Paragraph('1. 3D Visualization', style_h3))
        elements.append(Paragraph('• <b>Assets:</b> CNC Machines, Robot Arms, Conveyor Belts', style_bullet))
        elements.append(Paragraph('• <b>Status:</b> Green (Running), Amber (Idle), Red (Warning)', style_bullet))
        elements.append(Paragraph('• <b>Animation:</b> Real-time sync with production cycle', style_bullet))
        
        elements.append(Paragraph('2. Predictive Maintenance', style_h3))
        elements.append(Paragraph('Risk Matrix correlating Temperature, Machine Health %, and Vibration levels. Triggers warning if Temperature exceeds 90°C.', style_body))
        
        elements.append(Paragraph('3. TCO Optimization', style_h3))
        elements.append(Paragraph('Total Cost of Ownership calculator projecting 10-year financial data: CAPEX + Operating Costs + Maintenance.', style_body))
        
        elements.append(Paragraph('4. Safety Monitoring', style_h3))
        elements.append(Paragraph('Real-time air quality tracking for hazardous zones with automated ventilation control.', style_body))
        
        # Footer
        elements.append(Spacer(1, 30))
        elements.append(Paragraph(f"<b>{company_name.upper()}</b> — INTERNAL TECHNICAL REFERENCE — END OF DOCUMENT", style_footer))
        
        # Build PDF
        doc.build(elements)
        return buffer.getvalue()

    def generate_catalog_in_memory(self, input_data: CatalogInput) -> Dict[str, Any]:
        """Generate catalog PDF in memory (serverless-friendly)."""
        module1_data = input_data.module1_data
        module4_data = input_data.module4_data

        project_info = module1_data.get("stage_1_informations_generales", {}).get("informations_generales", {})
        project_name = project_info.get("nom_projet", "Industrial Project")
        company_name = project_info.get("nom_entreprise", "Company")

        base_name = input_data.base_filename or project_name or "catalog"
        base_name = re.sub(r"[^A-Za-z0-9_-]+", "_", base_name).strip("_") or "catalog"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        pdf_filename = f"{base_name}_{timestamp}.pdf"
        pdf_bytes = self._generate_pdf_in_memory(module1_data, module4_data)

        return {
            "created_at": datetime.utcnow().isoformat(),
            "project_name": project_name,
            "company_name": company_name,
            "output_format": "pdf",
            "pdf_filename": pdf_filename,
            "pdf_content": pdf_bytes,
            "pdf_size_bytes": len(pdf_bytes),
        }
