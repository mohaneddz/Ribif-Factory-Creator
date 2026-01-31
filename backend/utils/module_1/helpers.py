
import json
import re
from typing import Any, Dict, Optional
from utils.logger import get_logger

logger = get_logger(__name__)

def safe_json_loader(raw_str: str) -> Dict[str, Any]:
    """
    Robust JSON extraction and loading from LLM responses.
    - Handles code fences (```json ... ```).
    - Uses brace matching to find the first '{' and last '}'.
    - Attempts to fix unterminated strings.
    - Retries basic repairs if parsing fails.
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

    # 3. Try direct load
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as e:
        logger.debug(f"Initial JSON parse failed: {e}. Attempting repairs...")

    # 4. Common repairs
    try:
        # Handle smart quotes
        repaired = candidate.replace("\u201c", '"').replace("\u201d", '"')
        repaired = repaired.replace("\u2018", "'").replace("\u2019", "'")
        
        # Remove trailing commas
        repaired = re.sub(r",\s*([\]}])", r"\1", repaired)
        
        # Check for unterminated strings (common in LLM output)
        # We count quotes. If odd and ends with something other than a quote/brace, try adding a quote.
        if repaired.count('"') % 2 != 0:
            if not repaired.endswith('"') and not repaired.endswith('}') and not repaired.endswith(']'):
                repaired += '"'
        
        # Final attempt with repairs
        return json.loads(repaired)
    except Exception as final_e:
        logger.error(f"Failed to parse LLM JSON after repairs: {final_e}")
        logger.debug(f"Broken candidate: {candidate[:500]}...")
        return {}

def normalize_headers(headers: Dict[str, Any]) -> Dict[str, str]:
    """
    Ensures all header values are strings.
    Prevents requests from crashing on boolean or integer values.
    """
    if not headers:
        return {}
    return {str(k): str(v) for k, v in headers.items()}
