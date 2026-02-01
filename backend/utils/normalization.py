"""
Strict Input Normalization Utilities
=====================================

Reusable normalizers for numeric fields, text, and entity keys.
Never raises exceptions - always returns a safe default.
"""

from typing import Any, Optional, Union, Dict
import re
from decimal import Decimal, InvalidOperation


# =========================================================
# Numeric Normalization
# =========================================================

def normalize_numeric(
    value: Any,
    default: Union[int, float] = 0,
    allow_negative: bool = True,
    return_type: str = "float"
) -> Union[int, float]:
    """
    Safely parse any value to int or float.
    
    Args:
        value: Any input (int/float/str/dict/None/list)
        default: Default value if parsing fails
        allow_negative: If False, returns abs(value)
        return_type: "int" or "float"
    
    Returns:
        Parsed numeric value or default
        
    Examples:
        normalize_numeric("42") -> 42.0
        normalize_numeric("$1,234.56") -> 1234.56
        normalize_numeric({"amount": 100}) -> 100.0
        normalize_numeric(None) -> 0.0
        normalize_numeric([1, 2, 3]) -> 1.0 (first element)
    """
    # Handle None
    if value is None:
        return default
    
    # Already numeric
    if isinstance(value, (int, float)):
        result = float(value) if return_type == "float" else int(value)
        return abs(result) if not allow_negative and result < 0 else result
    
    # Handle dict (extract common keys)
    if isinstance(value, dict):
        for key in ["amount", "value", "price", "quantity", "count", "total"]:
            if key in value:
                return normalize_numeric(value[key], default, allow_negative, return_type)
        return default
    
    # Handle list (take first element)
    if isinstance(value, (list, tuple)):
        if len(value) > 0:
            return normalize_numeric(value[0], default, allow_negative, return_type)
        return default
    
    # String parsing
    if isinstance(value, str):
        # Remove common non-numeric characters
        cleaned = value.strip()
        
        # Remove currency symbols and spaces
        cleaned = re.sub(r'[$€£¥₹₽฿₪₩₦₴₱₡₵₸₹DZD\s,]', '', cleaned)
        
        # Handle percentage
        if '%' in cleaned:
            cleaned = cleaned.replace('%', '')
            try:
                result = float(cleaned) / 100
                return abs(result) if not allow_negative and result < 0 else result
            except (ValueError, InvalidOperation):
                return default
        
        # Handle ranges (e.g., "100-200")
        if '-' in cleaned and not cleaned.startswith('-'):
            parts = cleaned.split('-')
            if len(parts) == 2:
                try:
                    # Return midpoint
                    low = float(parts[0].strip())
                    high = float(parts[1].strip())
                    result = (low + high) / 2
                    return abs(result) if not allow_negative and result < 0 else result
                except (ValueError, InvalidOperation):
                    pass
        
        # Try direct parsing
        try:
            result = Decimal(cleaned)
            result = float(result) if return_type == "float" else int(result)
            return abs(result) if not allow_negative and result < 0 else result
        except (ValueError, InvalidOperation):
            pass
    
    # Fallback
    return default


def normalize_int(value: Any, default: int = 0, allow_negative: bool = True) -> int:
    """Shorthand for integer normalization."""
    return int(normalize_numeric(value, default, allow_negative, "float"))


def normalize_float(value: Any, default: float = 0.0, allow_negative: bool = True) -> float:
    """Shorthand for float normalization."""
    return normalize_numeric(value, default, allow_negative, "float")


def safe_sum(values: list, default: float = 0.0) -> float:
    """
    Safely sum a list of potentially non-numeric values.
    
    Examples:
        safe_sum([1, "2", None, {"amount": 3}]) -> 6.0
    """
    return sum(normalize_float(v) for v in values)


def safe_avg(values: list, default: float = 0.0) -> float:
    """Safely average a list of values."""
    if not values:
        return default
    return safe_sum(values) / len(values)


# =========================================================
# Text Normalization
# =========================================================

def normalize_text(value: Any, default: str = "") -> str:
    """
    Safely normalize any value to text.
    
    Args:
        value: Any input
        default: Default if None or empty
        
    Returns:
        Normalized string
    """
    if value is None:
        return default
    
    if isinstance(value, str):
        return value.strip()
    
    if isinstance(value, (int, float)):
        return str(value)
    
    if isinstance(value, dict):
        # Try common text keys
        for key in ["name", "text", "value", "label", "title"]:
            if key in value:
                return normalize_text(value[key], default)
        return default
    
    if isinstance(value, (list, tuple)):
        if len(value) > 0:
            return normalize_text(value[0], default)
        return default
    
    return str(value)


# =========================================================
# Entity Key Canonicalization
# =========================================================

def canonicalize_key(text: str) -> str:
    """
    Normalize entity keys for robust matching.
    
    Handles:
    - Case insensitivity
    - Whitespace normalization
    - Special character removal
    - Accents/diacritics
    
    Examples:
        canonicalize_key("Injection Molding Machine") -> "injection_molding_machine"
        canonicalize_key("Extrudeuse Bi-Vis") -> "extrudeuse_bi_vis"
        canonicalize_key("  CNC   Lathe  ") -> "cnc_lathe"
    """
    if not text:
        return ""
    
    # Lowercase
    text = text.lower()
    
    # Remove accents (basic)
    accents = {
        'à': 'a', 'á': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a',
        'è': 'e', 'é': 'e', 'ê': 'e', 'ë': 'e',
        'ì': 'i', 'í': 'i', 'î': 'i', 'ï': 'i',
        'ò': 'o', 'ó': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
        'ù': 'u', 'ú': 'u', 'û': 'u', 'ü': 'u',
        'ñ': 'n', 'ç': 'c'
    }
    for old, new in accents.items():
        text = text.replace(old, new)
    
    # Replace special chars with underscore
    text = re.sub(r'[^a-z0-9]+', '_', text)
    
    # Remove leading/trailing underscores
    text = text.strip('_')
    
    return text


def fuzzy_match_key(key1: str, key2: str) -> bool:
    """
    Check if two entity keys are equivalent.
    
    Examples:
        fuzzy_match_key("Injection Machine", "injection_machine") -> True
        fuzzy_match_key("CNC Lathe", "cnc-lathe") -> True
    """
    return canonicalize_key(key1) == canonicalize_key(key2)


def normalize_entity_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize all keys in a dictionary for robust matching.
    
    Returns a new dict with canonicalized keys.
    """
    return {canonicalize_key(k): v for k, v in data.items()}


# =========================================================
# List/Collection Normalization
# =========================================================

def normalize_list(value: Any, default: list = None) -> list:
    """
    Safely normalize to list.
    
    Examples:
        normalize_list("item") -> ["item"]
        normalize_list(None) -> []
        normalize_list([1, 2]) -> [1, 2]
    """
    if default is None:
        default = []
    
    if value is None:
        return default
    
    if isinstance(value, list):
        return value
    
    if isinstance(value, (tuple, set)):
        return list(value)
    
    # Single item
    return [value]


# =========================================================
# Boolean Normalization
# =========================================================

def normalize_bool(value: Any, default: bool = False) -> bool:
    """
    Safely normalize to boolean.
    
    Examples:
        normalize_bool("true") -> True
        normalize_bool(1) -> True
        normalize_bool("no") -> False
        normalize_bool(None) -> False
    """
    if value is None:
        return default
    
    if isinstance(value, bool):
        return value
    
    if isinstance(value, (int, float)):
        return value != 0
    
    if isinstance(value, str):
        value = value.lower().strip()
        if value in ('true', 'yes', '1', 'on', 'oui', 'si'):
            return True
        if value in ('false', 'no', '0', 'off', 'non'):
            return False
    
    return default


# =========================================================
# Validation Helpers
# =========================================================

def is_valid_numeric(value: Any) -> bool:
    """Check if value can be normalized to a number."""
    try:
        normalize_numeric(value)
        return True
    except:
        return False


def clamp_numeric(value: Any, min_val: float = None, max_val: float = None) -> float:
    """
    Normalize and clamp a numeric value to a range.
    
    Examples:
        clamp_numeric(150, 0, 100) -> 100
        clamp_numeric(-5, 0, 100) -> 0
    """
    num = normalize_float(value)
    
    if min_val is not None and num < min_val:
        return min_val
    
    if max_val is not None and num > max_val:
        return max_val
    
    return num
