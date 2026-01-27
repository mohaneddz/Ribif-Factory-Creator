
import json
import re
from typing import Any, Dict, Optional
from utils.logger import get_logger

logger = get_logger(__name__)


def sanitize_unicode_escapes(text: str) -> str:
    """
    Fix invalid unicode escapes that crash json.loads.
    
    LLMs sometimes produce invalid sequences like:
    - \\u followed by non-hex chars (e.g., \\uNOPE)
    - \\u followed by <4 hex digits (e.g., \\u12)
    
    This replaces invalid \\u sequences with escaped backslashes.
    """
    if not text:
        return text
    
    # Pattern: \u NOT followed by exactly 4 hex digits
    # We need to be careful to not break valid unicode escapes
    def fix_invalid_unicode(text: str) -> str:
        """Check if a \\uXXXX sequence is valid and fix if not.
        
        Args:
            text: The string starting with \\u (e.g., '\\u0041' or '\\uNOPE')
        
        Returns:
            The original text if valid, or escaped version if invalid.
        """
        full = text
        # Check if the 4 chars after \u are all hex
        after_u = full[2:6] if len(full) >= 6 else ""
        if len(after_u) == 4 and all(c in '0123456789abcdefABCDEF' for c in after_u):
            return full  # Valid, keep as-is
        # Invalid - escape the backslash
        return '\\\\u' + full[2:]
    
    # Find all \u sequences and validate them
    # This regex finds \u followed by anything
    result = re.sub(r'\\u(.{0,4})', lambda m: fix_invalid_unicode('\\u' + m.group(1)), text)
    
    return result


def safe_json_loader(raw_str: str) -> Dict[str, Any]:
    """
    Robust JSON extraction and loading from LLM responses.
    - Handles code fences (```json ... ```).
    - Uses brace matching to find the first '{' and last '}'.
    - Sanitizes invalid unicode escapes.
    - Attempts to fix unterminated strings.
    - Retries basic repairs if parsing fails.
    - NO long backoffs - max 1 retry then fallback to empty dict.
    """
    if not raw_str:
        return {}
    
    # 1. Strip code fences
    cleaned = raw_str.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

    # 2. Extract first {...} via brace matching or regex
    # Regex is faster for simple cases
    m = re.search(r"(\{[\s\S]*\})", cleaned)
    if not m:
        logger.warning("No JSON object found in LLM response.")
        return {}
    
    candidate = m.group(1)
    
    # 3. Sanitize unicode escapes BEFORE parsing
    candidate = sanitize_unicode_escapes(candidate)

    # 4. Try direct load
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as e:
        logger.debug(f"Initial JSON parse failed: {e}. Attempting repairs...")

    # 5. Common repairs (ONE attempt only, no backoff)
    try:
        # Handle smart quotes
        repaired = candidate.replace("\u201c", '"').replace("\u201d", '"')
        repaired = repaired.replace("\u2018", "'").replace("\u2019", "'")
        
        # Remove trailing commas
        repaired = re.sub(r",\s*([\]}])", r"\1", repaired)
        
        # Fix common escape issues
        repaired = repaired.replace('\\"', '"')  # Over-escaped quotes
        repaired = re.sub(r'\\([^"\\nrtbfu/])', r'\1', repaired)  # Invalid escapes
        
        # Check for unterminated strings (common in LLM output)
        # We count quotes. If odd and ends with something other than a quote/brace, try adding a quote.
        if repaired.count('"') % 2 != 0:
            if not repaired.endswith('"') and not repaired.endswith('}') and not repaired.endswith(']'):
                repaired += '"'
        
        # Final attempt with repairs
        return json.loads(repaired)
    except Exception as final_e:
        logger.error(f"Failed to parse LLM JSON after repairs: {final_e}")
        logger.debug(f"Broken candidate (first 500 chars): {candidate[:500]}...")
        # NO RETRY/BACKOFF - return empty immediately
        return {}


def normalize_headers(headers: Dict[str, Any]) -> Dict[str, str]:
    """
    Ensures all header values are strings.
    Prevents requests from crashing on boolean or integer values.
    """
    if not headers:
        return {}
    return {str(k): str(v) for k, v in headers.items()}

