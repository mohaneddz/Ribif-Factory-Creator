"""
Enhanced Gemini API integration for structured machine spec extraction.

Parses unstructured HTML/text using Gemini with JSON schema for reliable extraction.
Fallback for complex specifications when regex/table parsing fails.
"""

import json
import logging
from typing import Dict, Optional
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class GeminiSpecExtractor:
    """Use Gemini to extract structured specs from unstructured text."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Gemini extractor."""
        import os

        load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

        # Use provided API key or get from environment
        if not api_key:
            api_key = os.getenv("GOOGLE_API_KEY")

        if not api_key:
            raise ValueError("API Key not found! Make sure you created a .env file.")

        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)
        self.model_name = "gemini-2.5-flash"
        self.temperature = 0.1  # Low temperature for factual extraction
    
    async def extract_specs(self, text: str, manufacturer: Optional[str] = None, model: Optional[str] = None) -> Dict:
        """
        Extract machine specifications from unstructured text using Gemini.
        
        Args:
            text: Unstructured HTML/text containing specs
            manufacturer: Optional hint for manufacturer name
            model: Optional hint for model name
        
        Returns:
            Dict with extracted specs and confidence scores:
            {
                'capacity': {'value': 50, 'unit': 'kg', 'confidence': 0.95},
                'power': {'value': 5, 'unit': 'kW', 'confidence': 0.92},
                ...
                'raw_response': 'gemini response'
            }
        """
        try:
            # Build extraction prompt
            prompt = self._build_extraction_prompt(text, manufacturer, model)
            
            logger.info("Calling Gemini for spec extraction")
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=self.temperature,
                    top_p=0.95,
                    top_k=64,
                ),
            )
            response_text = response.text
            
            # Parse Gemini's JSON response
            specs = self._parse_gemini_response(response_text)
            specs['raw_response'] = response_text
            
            logger.info(f"Gemini extracted: {list(specs.keys())}")
            return specs
            
        except Exception as e:
            logger.error(f"Gemini extraction failed: {e}")
            return {
                'error': str(e),
                'raw_response': None
            }
    
    def _build_extraction_prompt(self, text: str, manufacturer: Optional[str], model: Optional[str]) -> str:
        """Build the extraction prompt for Gemini."""
        
        context = ""
        if manufacturer:
            context += f"Manufacturer: {manufacturer}\n"
        if model:
            context += f"Model: {model}\n"
        
        return f"""Extract machine specifications from the following text. Return ONLY valid JSON.

{context}

Text to analyze:
{text[:5000]}

Extract the following fields if present. Return exactly this JSON structure:
{{
    "capacity": {{"value": <number or null>, "unit": "<string>", "confidence": <0-1>}},
    "power": {{"value": <number or null>, "unit": "kW or W", "confidence": <0-1>}},
    "dimensions": {{"length": <number or null>, "width": <number or null>, "height": <number or null>, "unit": "mm or m", "confidence": <0-1>}},
    "weight": {{"value": <number or null>, "unit": "kg or g", "confidence": <0-1>}},
    "max_pressure": {{"value": <number or null>, "unit": "bar or PSI", "confidence": <0-1>}},
    "cycle_time": {{"value": <number or null>, "unit": "seconds or minutes", "confidence": <0-1>}},
    "production_rate": {{"value": <number or null>, "unit": "parts/hour or pieces/min", "confidence": <0-1>}},
    "material": "<material type if mentioned>",
    "temperature_range": {{"min": <number or null>, "max": <number or null>, "unit": "°C", "confidence": <0-1>}},
    "extraction_notes": "<any important notes about extraction quality>"
}}

For confidence:
- 0.9-1.0: Explicitly stated in text
- 0.7-0.9: Clearly inferred from context
- 0.5-0.7: Reasonable interpretation
- <0.5: Uncertain

Return ONLY the JSON object, no other text."""
    
    def _parse_gemini_response(self, response_text: str) -> Dict:
        """Parse Gemini's JSON response."""
        
        try:
            # Try to find JSON in response
            if '```json' in response_text:
                json_str = response_text.split('```json')[1].split('```')[0].strip()
            elif '{' in response_text:
                # Find first { and last }
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                json_str = response_text[start:end]
            else:
                raise ValueError("No JSON found in response")
            
            specs = json.loads(json_str)
            return specs
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON: {e}")
            # Return structure with null values
            return {
                'capacity': {'value': None, 'confidence': 0},
                'power': {'value': None, 'confidence': 0},
                'dimensions': {'length': None, 'width': None, 'height': None, 'confidence': 0},
                'weight': {'value': None, 'confidence': 0},
                'max_pressure': {'value': None, 'confidence': 0},
                'cycle_time': {'value': None, 'confidence': 0},
                'production_rate': {'value': None, 'confidence': 0},
                'error': str(e)
            }
        except Exception as e:
            logger.error(f"Error parsing Gemini response: {e}")
            raise
    
    def extract_specs_sync(self, text: str, manufacturer: Optional[str] = None, model: Optional[str] = None) -> Dict:
        """
        Synchronous wrapper for spec extraction.
        
        Use this if you're already in an async context but need sync API.
        """
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Already in async context
                raise RuntimeError("Cannot call sync method in async context")
            return loop.run_until_complete(self.extract_specs(text, manufacturer, model))
        except RuntimeError:
            # Fallback to new loop
            return asyncio.run(self.extract_specs(text, manufacturer, model))
    
    async def extract_with_fallback(
        self, 
        text: str,
        primary_specs: Optional[Dict] = None,
        manufacturer: Optional[str] = None,
        model: Optional[str] = None
    ) -> Dict:
        """
        Extract specs with intelligent fallback.
        
        If primary_specs exist, only extract missing fields.
        Prioritize high-confidence values from primary over Gemini.
        """
        gemini_specs = await self.extract_specs(text, manufacturer, model)
        
        if not primary_specs:
            return gemini_specs
        
        # Merge: keep primary if high confidence, supplement with Gemini
        merged = primary_specs.copy()
        
        for field in ['capacity', 'power', 'dimensions', 'weight', 'max_pressure', 'cycle_time', 'production_rate']:
            # If field missing in primary, add from Gemini
            if field not in merged or merged[field] is None:
                if field in gemini_specs and gemini_specs[field]:
                    # Only add if Gemini has decent confidence
                    if isinstance(gemini_specs[field], dict):
                        confidence = gemini_specs[field].get('confidence', 0)
                        if confidence >= 0.7:
                            merged[field] = gemini_specs[field]
                    else:
                        merged[field] = gemini_specs[field]
        
        return merged


async def extract_machine_specs(
    text: str,
    manufacturer: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None
) -> Dict:
    """
    Convenience function to extract specs from text using Gemini.
    """
    extractor = GeminiSpecExtractor(api_key)
    return await extractor.extract_specs(text, manufacturer, model)
