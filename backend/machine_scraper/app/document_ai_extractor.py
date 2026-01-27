"""
Google Cloud Document AI for PDF Specification Extraction.

Uses Document AI Form Parser to extract machine specs from technical datasheets.
Free tier: 1,000 pages/month
"""

import logging
from typing import Dict, Optional
import os

logger = logging.getLogger(__name__)

try:
    from google.cloud import documentai_v1 as documentai
    HAS_DOCUMENT_AI = True
except ImportError:
    HAS_DOCUMENT_AI = False
    logger.warning("google-cloud-documentai not installed")


class DocumentAIExtractor:
    """Extract structured specs from PDF datasheets using Google Cloud Document AI."""
    
    def __init__(self):
        """Initialize Document AI client."""
        self.has_api = HAS_DOCUMENT_AI
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.processor_id = os.getenv("DOCUMENT_AI_PROCESSOR_ID")
        
        if self.has_api and self.project_id and self.processor_id:
            try:
                self.client = documentai.DocumentProcessorServiceClient()
            except Exception as e:
                logger.warning(f"Document AI client init failed: {e}")
                self.has_api = False
        else:
            self.has_api = False
    
    async def extract_from_pdf(self, pdf_path: str, max_pages: int = 3) -> Dict[str, Optional[str]]:
        """
        Extract specifications from PDF using Document AI Form Parser.
        
        Limits processing to max 3 pages to control costs and stay within free tier.
        
        Returns dict with extracted specs:
        {
            'capacity': '100 tons',
            'power': '45 kW',
            'dimensions': '2000×1500×1800 mm',
            'weight': '5000 kg',
            'max_pressure': '350 bar',
            'cycle_time': '30 s',
            'production_rate': '200 parts/hour',
            'raw_fields': {...all detected fields...}
        }
        
        Args:
            pdf_path: Path to PDF file
            max_pages: Maximum pages to process (default: 3)
        """
        
        if not self.has_api:
            logger.warning("Document AI not configured")
            return {}
        
        try:
            # Read PDF file
            with open(pdf_path, "rb") as pdf:
                pdf_content = pdf.read()
            
            # Build request with max pages limit
            name = self.client.processor_path(self.project_id, "us", self.processor_id)
            raw_document = documentai.RawDocument(
                content=pdf_content,
                mime_type="application/pdf"
            )
            
            # ProcessOptions to limit pages
            process_options = documentai.ProcessOptions(
                individual_page_selector=documentai.ProcessOptions.IndividualPageSelector(
                    pages=[i+1 for i in range(max_pages)]
                )
            )
            
            request = documentai.ProcessRequest(
                name=name,
                raw_document=raw_document,
                process_options=process_options
            )
            
            # Process document
            result = self.client.process_document(request=request)
            document = result.document
            
            logger.info(f"Document AI processed PDF: {len(document.pages)} pages (limited to max {max_pages})")
            
            # Extract form fields
            specs = self._extract_form_fields(document)
            
            logger.info(f"Extracted specs: {specs}")
            return specs
            
        except Exception as e:
            logger.error(f"Document AI extraction failed: {e}")
            return {}
    
    def _extract_form_fields(self, document) -> Dict[str, Optional[str]]:
        """Parse form fields from Document AI response."""
        
        specs = {
            'capacity': None,
            'power': None,
            'dimensions': None,
            'weight': None,
            'max_pressure': None,
            'cycle_time': None,
            'production_rate': None,
            'raw_fields': {}
        }
        
        try:
            for page in document.pages:
                for form_field in page.form_fields:
                    field_name = self._extract_text(form_field.field_name, document)
                    field_value = self._extract_text(form_field.field_value, document)
                    
                    if not field_name or not field_value:
                        continue
                    
                    # Store raw field
                    specs['raw_fields'][field_name] = field_value
                    
                    # Map to standard fields
                    field_name_lower = field_name.lower()
                    
                    if any(x in field_name_lower for x in ['capacity', 'tonnage', 'force', 'clamping']):
                        if not specs['capacity']:
                            specs['capacity'] = field_value
                    
                    elif any(x in field_name_lower for x in ['power', 'watt', 'kw', 'hp', 'energy']):
                        if not specs['power']:
                            specs['power'] = field_value
                    
                    elif any(x in field_name_lower for x in ['dimension', 'size', 'length', 'width', 'height']):
                        if not specs['dimensions']:
                            specs['dimensions'] = field_value
                    
                    elif any(x in field_name_lower for x in ['weight', 'mass', 'ton']):
                        if not specs['weight']:
                            specs['weight'] = field_value
                    
                    elif any(x in field_name_lower for x in ['pressure', 'bar', 'psi']):
                        if not specs['max_pressure']:
                            specs['max_pressure'] = field_value
                    
                    elif any(x in field_name_lower for x in ['cycle', 'time', 'second']):
                        if not specs['cycle_time']:
                            specs['cycle_time'] = field_value
                    
                    elif any(x in field_name_lower for x in ['production', 'rate', 'speed', 'output']):
                        if not specs['production_rate']:
                            specs['production_rate'] = field_value
            
            # Remove None values and empty raw_fields
            specs = {k: v for k, v in specs.items() if v and (k != 'raw_fields' or v)}
            
            return specs
            
        except Exception as e:
            logger.error(f"Form field extraction failed: {e}")
            return specs
    
    @staticmethod
    def _extract_text(doc_element, document) -> str:
        """Extract text from document element."""
        if not doc_element or not doc_element.text_anchor:
            return ""
        
        try:
            response = ""
            for segment in doc_element.text_anchor.text_segments:
                start = int(segment.start_index) if segment.start_index else 0
                end = int(segment.end_index)
                response += document.text[start:end]
            return response.strip()
        except:
            return ""


async def extract_specs_from_pdf(pdf_path: str, max_pages: int = 3) -> Dict[str, Optional[str]]:
    """
    Convenience function to extract specs from PDF.
    
    Args:
        pdf_path: Path to PDF file
        max_pages: Maximum pages to process (default: 3)
    """
    extractor = DocumentAIExtractor()
    return await extractor.extract_from_pdf(pdf_path, max_pages=max_pages)
