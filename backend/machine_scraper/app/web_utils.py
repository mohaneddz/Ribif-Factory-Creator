"""Enhanced web utilities with structured data extraction.

Features:
- JSON-LD schema extraction (company info, contact, etc.)
- Open Graph meta tag extraction
- Semantic relevance scoring
- Intelligent text truncation
"""

from bs4 import BeautifulSoup
import json
import html
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class ContentExtractor:
    """Extract structured and unstructured data from HTML content."""

    def __init__(self):
        pass

    @staticmethod
    def _extract_json_ld(html_content: str) -> Dict:
        """Extract JSON-LD structured data (company info, contact, schema.org)."""
        soup = BeautifulSoup(html_content, "html.parser")
        json_ld_scripts = soup.find_all("script", type="application/ld+json")
        extracted_data = {}

        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, list):
                    data = data[0] if data else {}

                # Extract organization/company info
                if data.get("@type") in ["Organization", "LocalBusiness", "Corporation"]:
                    extracted_data.update({
                        "company_name": data.get("name"),
                        "description": data.get("description"),
                        "contact": data.get("contactPoint", {}).get("telephone"),
                        "email": data.get("contactPoint", {}).get("email"),
                        "address": data.get("address", {}).get("streetAddress"),
                        "city": data.get("address", {}).get("addressLocality"),
                        "country": data.get("address", {}).get("addressCountry"),
                    })

                # Extract product/service info
                if data.get("@type") in ["Product", "Service"]:
                    extracted_data.update({
                        "product_name": data.get("name"),
                        "product_description": data.get("description"),
                        "price": data.get("offers", {}).get("price"),
                    })

            except (json.JSONDecodeError, AttributeError, TypeError) as e:
                logger.debug(f"JSON-LD parse error: {e}")
                continue

        return extracted_data

    @staticmethod
    def _extract_meta_tags(html_content: str) -> Dict:
        """Extract Open Graph and meta tags."""
        soup = BeautifulSoup(html_content, "html.parser")
        extracted_data = {}

        # Open Graph tags
        og_tags = {
            "og:title": "title",
            "og:description": "description",
            "og:type": "content_type",
            "article:published_time": "published_date",
        }
        for prop, key in og_tags.items():
            meta = soup.find("meta", property=prop)
            if meta and meta.get("content"):
                extracted_data[key] = meta["content"]

        # Standard meta tags
        standard_tags = {
            "description": "meta_description",
            "keywords": "keywords",
        }
        for attr, key in standard_tags.items():
            meta = soup.find("meta", attrs={"name": attr})
            if meta and meta.get("content"):
                extracted_data[key] = meta["content"]

        return extracted_data

    def extract_structured_fields(self, html_content: str) -> Dict:
        """Extract all structured data (JSON-LD + meta tags)."""
        if not html_content:
            return {}
        json_ld_data = self._extract_json_ld(html_content)
        meta_data = self._extract_meta_tags(html_content)
        return {**meta_data, **json_ld_data}

    @staticmethod
    def intelligent_truncate(text: str, max_tokens: int = 500) -> str:
        """Truncate text at sentence boundary."""
        words = text.split()
        if len(words) <= max_tokens:
            return text

        truncated = " ".join(words[:max_tokens])
        # Find last sentence-ending punctuation
        last_punc = max(
            truncated.rfind("."),
            truncated.rfind("!"),
            truncated.rfind("?"),
        )
        if last_punc > 0:
            return truncated[: last_punc + 1]
        return truncated + "..."

    def extract_relevant_sections(
        self, content: str, html_content: str, **kwargs
    ) -> Tuple[str, float, Dict]:
        """Extract and score content relevance.

        Returns: (cleaned_content, semantic_score, structured_fields)
        """
        if not content:
            return "", 0.0, {}

        structured_fields = self.extract_structured_fields(html_content)
        cleaned_content = html.unescape(content or "").strip()
        truncated_content = self.intelligent_truncate(cleaned_content, 600)

        # Semantic scoring: how many query tokens appear in content
        semantic_score = 0.0
        query = kwargs.get("query", "")
        if query:
            query_tokens = set(query.lower().split())
            content_tokens = set(truncated_content.lower().split())
            if query_tokens:
                semantic_score = len(query_tokens & content_tokens) / len(query_tokens)

        return truncated_content, semantic_score, structured_fields
