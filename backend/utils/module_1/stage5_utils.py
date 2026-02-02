"""
Stage 5 Production Process utilities for Module 1.
Handles parameter normalization, deduplication, and UI flattening.
"""

import re
import json
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from utils.logger import get_logger

logger = get_logger("module1.stage5_utils")


def parse_parameter_value(raw_value: Any) -> Tuple[Optional[float], Optional[str], str, str]:
    """
    Parse a parameter value from various formats into structured components.
    
    Args:
        raw_value: Can be string like "180°C", "5 bar", "45s", "N/A", 
                   or dict like "{'valeur': 25, 'unite': '°C'}", or already structured.
    
    Returns:
        Tuple of (value, unit, source, confidence)
        - value: Numeric value or None
        - unit: Unit string or None
        - source: "document_extracted", "estimated", "llm_generated", or "unknown"
        - confidence: "high", "medium", "low", or "unknown"
    """
    if not raw_value or raw_value == "N/A" or str(raw_value).strip() == "":
        return None, None, "unknown", "unknown"
    
    # Already a dict with structured data
    if isinstance(raw_value, dict):
        if "value" in raw_value and "unit" in raw_value:
            # Already normalized
            return (
                raw_value.get("value"),
                raw_value.get("unit"),
                raw_value.get("source", "unknown"),
                raw_value.get("confidence", "unknown")
            )
        elif "valeur" in raw_value:
            # French format from LLM
            val = raw_value.get("valeur")
            # Try to convert to number
            numeric_val = None
            if isinstance(val, (int, float)):
                numeric_val = float(val)
            elif isinstance(val, str) and val.replace('.', '', 1).replace('-', '', 1).isdigit():
                try:
                    numeric_val = float(val)
                except:
                    pass
            
            return (
                numeric_val,
                raw_value.get("unite"),
                raw_value.get("value_source", "llm_generated"),
                raw_value.get("confidence", "medium")
            )
    
    # String format - parse it
    raw_str = str(raw_value).strip()
    
    # Try to parse dict-like string (e.g., "{'valeur': 25, 'unite': '°C'}")
    if raw_str.startswith("{") or raw_str.startswith("'"):
        try:
            # Clean up the string
            cleaned = raw_str.replace("'", '"')
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return parse_parameter_value(parsed)  # Recursive call
        except:
            pass  # Continue to regex parsing
    
    # Regex patterns for common formats
    # Pattern: "180°C", "25 °C", "5bar", "5 bar", "45s", "45 min", etc.
    patterns = [
        (r'^(\d+(?:\.\d+)?)\s*(°C|C|°|celsius)$', 'temperature', '°C'),
        (r'^(\d+(?:\.\d+)?)\s*(bar|Bar|BAR)$', 'pressure', 'bar'),
        (r'^(\d+(?:\.\d+)?)\s*(s|sec|seconds?)$', 'cycle', 's'),
        (r'^(\d+(?:\.\d+)?)\s*(min|minutes?)$', 'cycle', 'min'),
        (r'^(\d+(?:\.\d+)?)\s*(h|hr|hours?)$', 'cycle', 'h'),
        (r'^(\d+(?:\.\d+)?)\s*(m/min|m\/min)$', 'speed', 'm/min'),
        (r'^(\d+(?:\.\d+)?)\s*$', 'unknown', None),  # Just a number
    ]
    
    for pattern, param_type, unit in patterns:
        match = re.match(pattern, raw_str, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            return value, unit, "document_extracted", "medium"
    
    # Special cases
    if "continu" in raw_str.lower() or "continuous" in raw_str.lower():
        return None, None, "estimated", "high"
    
    if "variable" in raw_str.lower() or "batch" in raw_str.lower():
        return None, None, "estimated", "medium"
    
    # Could not parse
    return None, None, "unknown", "low"


# Default process parameters based on operation/machine type
DEFAULT_PROCESS_PARAMS = {
    # High temperature processes
    "injection": {"temperature": 220, "pressure": 120, "cycle": 45},
    "moulage": {"temperature": 200, "pressure": 100, "cycle": 60},
    "molding": {"temperature": 200, "pressure": 100, "cycle": 60},
    "extrusion": {"temperature": 180, "pressure": 80, "cycle": 30},
    "thermoformage": {"temperature": 160, "pressure": 5, "cycle": 40},
    "thermoforming": {"temperature": 160, "pressure": 5, "cycle": 40},
    "soudure": {"temperature": 1800, "pressure": 1, "cycle": 20},
    "welding": {"temperature": 1800, "pressure": 1, "cycle": 20},
    "heat treatment": {"temperature": 450, "pressure": 1, "cycle": 3600},
    "traitement thermique": {"temperature": 450, "pressure": 1, "cycle": 3600},
    "cuisson": {"temperature": 180, "pressure": 1, "cycle": 1800},
    "baking": {"temperature": 180, "pressure": 1, "cycle": 1800},
    # Machining processes
    "usinage": {"temperature": 25, "pressure": 1, "cycle": 120},
    "machining": {"temperature": 25, "pressure": 1, "cycle": 120},
    "cnc": {"temperature": 25, "pressure": 1, "cycle": 180},
    "fraisage": {"temperature": 25, "pressure": 1, "cycle": 150},
    "milling": {"temperature": 25, "pressure": 1, "cycle": 150},
    "tournage": {"temperature": 25, "pressure": 1, "cycle": 90},
    "turning": {"temperature": 25, "pressure": 1, "cycle": 90},
    "découpe": {"temperature": 25, "pressure": 8, "cycle": 30},
    "cutting": {"temperature": 25, "pressure": 8, "cycle": 30},
    "perçage": {"temperature": 25, "pressure": 1, "cycle": 45},
    "drilling": {"temperature": 25, "pressure": 1, "cycle": 45},
    "laser": {"temperature": 25, "pressure": 1, "cycle": 60},
    # Pressing/forming
    "presse": {"temperature": 25, "pressure": 200, "cycle": 30},
    "press": {"temperature": 25, "pressure": 200, "cycle": 30},
    "emboutissage": {"temperature": 25, "pressure": 300, "cycle": 15},
    "stamping": {"temperature": 25, "pressure": 300, "cycle": 15},
    "pliage": {"temperature": 25, "pressure": 150, "cycle": 20},
    "bending": {"temperature": 25, "pressure": 150, "cycle": 20},
    # Assembly/handling
    "assemblage": {"temperature": 25, "pressure": 1, "cycle": 60},
    "assembly": {"temperature": 25, "pressure": 1, "cycle": 60},
    "montage": {"temperature": 25, "pressure": 1, "cycle": 90},
    "packaging": {"temperature": 25, "pressure": 1, "cycle": 30},
    "emballage": {"temperature": 25, "pressure": 1, "cycle": 30},
    "palettisation": {"temperature": 25, "pressure": 1, "cycle": 45},
    "palletizing": {"temperature": 25, "pressure": 1, "cycle": 45},
    "manutention": {"temperature": 25, "pressure": 1, "cycle": 20},
    "handling": {"temperature": 25, "pressure": 1, "cycle": 20},
    # Quality/inspection
    "contrôle": {"temperature": 25, "pressure": 1, "cycle": 60},
    "control": {"temperature": 25, "pressure": 1, "cycle": 60},
    "inspection": {"temperature": 25, "pressure": 1, "cycle": 45},
    "test": {"temperature": 25, "pressure": 1, "cycle": 120},
    "qc": {"temperature": 25, "pressure": 1, "cycle": 60},
    "quality": {"temperature": 25, "pressure": 1, "cycle": 60},
    # Surface treatment
    "peinture": {"temperature": 60, "pressure": 4, "cycle": 300},
    "painting": {"temperature": 60, "pressure": 4, "cycle": 300},
    "coating": {"temperature": 80, "pressure": 1, "cycle": 180},
    "revêtement": {"temperature": 80, "pressure": 1, "cycle": 180},
    "polissage": {"temperature": 25, "pressure": 1, "cycle": 120},
    "polishing": {"temperature": 25, "pressure": 1, "cycle": 120},
    "nettoyage": {"temperature": 40, "pressure": 3, "cycle": 60},
    "cleaning": {"temperature": 40, "pressure": 3, "cycle": 60},
    # Default fallback
    "default": {"temperature": 25, "pressure": 1, "cycle": 60},
}


def estimate_default_params(step_name: str, machine_name: str = None) -> Dict[str, Any]:
    """
    Estimate default process parameters based on step name and machine name.
    
    Args:
        step_name: Name of the production step
        machine_name: Name of the machine (optional)
    
    Returns:
        Dict with estimated temperature, pressure, cycle values
    """
    search_text = f"{step_name or ''} {machine_name or ''}".lower()
    
    # Find best matching process type
    for process_key, params in DEFAULT_PROCESS_PARAMS.items():
        if process_key in search_text:
            return params.copy()
    
    # Return default values
    return DEFAULT_PROCESS_PARAMS["default"].copy()


def normalize_parametres_process(raw_params: Dict[str, Any], step_name: str = None, machine_name: str = None) -> Dict[str, Any]:
    """
    Normalize parametres_process from various formats into structured schema.
    If values are missing or N/A, estimates sensible defaults based on operation type.
    
    Args:
        raw_params: Raw parameters dict with keys like temperature, pression, temps_cycle, vitesse
        step_name: Name of the step (for estimating defaults)
        machine_name: Name of the machine (for estimating defaults)
    
    Returns:
        Normalized dict with structured temperature, pressure, cycle_time, speed objects
    """
    normalized = {}
    
    # Get default estimates based on step/machine type
    defaults = estimate_default_params(step_name, machine_name)
    
    # Temperature
    temp_raw = raw_params.get("temperature") or raw_params.get("temp")
    if temp_raw:
        value, unit, source, confidence = parse_parameter_value(temp_raw)
        if value is not None:
            normalized["temperature"] = {
                "value": value,
                "unit": unit or "°C",
                "source": source,
                "confidence": confidence
            }
        else:
            # Use estimated default
            normalized["temperature"] = {
                "value": defaults["temperature"],
                "unit": "°C",
                "source": "estimated",
                "confidence": "medium"
            }
    else:
        # Use estimated default
        normalized["temperature"] = {
            "value": defaults["temperature"],
            "unit": "°C",
            "source": "estimated",
            "confidence": "medium"
        }
    
    # Pressure
    pressure_raw = raw_params.get("pression") or raw_params.get("pressure")
    if pressure_raw:
        value, unit, source, confidence = parse_parameter_value(pressure_raw)
        if value is not None:
            normalized["pressure"] = {
                "value": value,
                "unit": unit or "bar",
                "source": source,
                "confidence": confidence
            }
        else:
            # Use estimated default
            normalized["pressure"] = {
                "value": defaults["pressure"],
                "unit": "bar",
                "source": "estimated",
                "confidence": "medium"
            }
    else:
        # Use estimated default
        normalized["pressure"] = {
            "value": defaults["pressure"],
            "unit": "bar",
            "source": "estimated",
            "confidence": "medium"
        }
    
    # Cycle time
    cycle_raw = raw_params.get("temps_cycle") or raw_params.get("cycle_time") or raw_params.get("cycle")
    cycle_mode = None
    if cycle_raw:
        value, unit, source, confidence = parse_parameter_value(cycle_raw)
        
        # Detect cycle mode from raw string
        cycle_str = str(cycle_raw).lower()
        if "continu" in cycle_str or "continuous" in cycle_str:
            cycle_mode = "continuous"
        elif "sampling" in cycle_str or "échantillon" in cycle_str:
            cycle_mode = "sampling"
        elif "variable" in cycle_str:
            cycle_mode = "variable"
        elif "batch" in cycle_str or "lot" in cycle_str:
            cycle_mode = "batch"
        
        if value is not None:
            normalized["cycle_time"] = {
                "value": value,
                "unit": unit or "s",
                "source": source,
                "confidence": confidence
            }
        else:
            # Use estimated default
            normalized["cycle_time"] = {
                "value": defaults["cycle"],
                "unit": "s",
                "source": "estimated",
                "confidence": "medium"
            }
        if cycle_mode:
            normalized["cycle_mode"] = cycle_mode
    else:
        # Use estimated default
        normalized["cycle_time"] = {
            "value": defaults["cycle"],
            "unit": "s",
            "source": "estimated",
            "confidence": "medium"
        }
    
    # Speed (optional)
    speed_raw = raw_params.get("vitesse") or raw_params.get("speed")
    if speed_raw and speed_raw != "N/A":
        value, unit, source, confidence = parse_parameter_value(speed_raw)
        normalized["speed"] = {
            "value": value,
            "unit": unit,
            "source": source,
            "confidence": confidence
        }
    
    # Tolerances (keep as string if present)
    tolerances = raw_params.get("tolerances") or raw_params.get("tolerance")
    if tolerances and tolerances != "N/A":
        normalized["tolerances"] = str(tolerances)
    
    return normalized


def generate_step_signature(step: Dict[str, Any], product_family: str) -> str:
    """
    Generate a stable signature for deduplication.
    
    Signature includes:
    - product_family
    - normalized title (lowercase, stripped)
    - temperature value
    - pressure value
    - cycle value
    
    Args:
        step: Step dict
        product_family: Product family name
    
    Returns:
        MD5 hash signature
    """
    # Get normalized title
    title = step.get("nom_etape") or step.get("name") or ""
    # Remove product prefix if exists
    if title.startswith("[") and "]" in title:
        title = title.split("]", 1)[1].strip()
    title = title.lower().strip()
    
    # Get parameter values
    params = step.get("parametres_process", {})
    
    # Handle both old string format and new structured format
    if isinstance(params.get("temperature"), dict):
        temp_val = params["temperature"].get("value")
    else:
        temp_val, _, _, _ = parse_parameter_value(params.get("temperature"))
    
    if isinstance(params.get("pressure"), dict):
        pressure_val = params["pressure"].get("value")
    else:
        pressure_val, _, _, _ = parse_parameter_value(params.get("pression") or params.get("pressure"))
    
    if isinstance(params.get("cycle_time"), dict):
        cycle_val = params["cycle_time"].get("value")
    else:
        cycle_val, _, _, _ = parse_parameter_value(params.get("temps_cycle") or params.get("cycle_time"))
    
    # Create signature string
    sig_parts = [
        product_family.lower().strip(),
        title,
        str(temp_val) if temp_val is not None else "none",
        str(pressure_val) if pressure_val is not None else "none",
        str(cycle_val) if cycle_val is not None else "none"
    ]
    
    sig_string = "|".join(sig_parts)
    return hashlib.md5(sig_string.encode()).hexdigest()


def deduplicate_steps_within_group(steps: List[Dict[str, Any]], product_family: str) -> Tuple[List[Dict[str, Any]], int]:
    """
    Deduplicate steps within a single product family/group.
    
    Args:
        steps: List of step dicts
        product_family: Product family name for signature generation
    
    Returns:
        Tuple of (deduplicated_steps, duplicate_count)
    """
    seen_signatures = {}
    deduplicated = []
    duplicate_count = 0
    
    for step in steps:
        sig = generate_step_signature(step, product_family)
        
        if sig in seen_signatures:
            # Duplicate detected
            duplicate_count += 1
            logger.warning(
                f"Duplicate step detected in '{product_family}': "
                f"'{step.get('nom_etape') or step.get('name')}' (signature: {sig[:8]}...)"
            )
        else:
            seen_signatures[sig] = True
            deduplicated.append(step)
    
    return deduplicated, duplicate_count


def create_hierarchical_stage5_structure(raw_processes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Transform flattened or nested Stage 5 data into the new hierarchical structure with ui_steps.
    
    Args:
        raw_processes: List of processes (either flat steps or nested product-based routings)
    
    Returns:
        Dict with:
        - processes: List of {product_family, steps[]} (nested, source-of-truth)
        - ui_steps: Flattened list with group_id, product_family, local_step_no, global_step_no
        - total_steps: Total across all groups
        - total_ui_steps: Length of ui_steps
        - total_groups: Number of product families
        - duplicate_count: Number of duplicates removed
    """
    if not raw_processes:
        return {
            "processes": [],
            "ui_steps": [],
            "total_steps": 0,
            "total_ui_steps": 0,
            "total_groups": 0,
            "duplicate_count": 0
        }
    
    processes = []
    ui_steps = []
    global_step_no = 1
    total_duplicate_count = 0
    
    # Check if nested (product-based) or flat
    is_nested = len(raw_processes) > 0 and ("etapes" in raw_processes[0] or "steps" in raw_processes[0])
    
    if is_nested:
        # Nested structure: multiple product families with their own steps
        for group_idx, process_group in enumerate(raw_processes):
            product_family = process_group.get("produit") or process_group.get("product_family") or f"Product Group {group_idx + 1}"
            group_id = f"group_{group_idx + 1}"
            
            # Get steps from this group
            raw_steps = process_group.get("etapes") or process_group.get("steps") or []
            
            # Deduplicate within this group
            deduped_steps, dup_count = deduplicate_steps_within_group(raw_steps, product_family)
            total_duplicate_count += dup_count
            
            # Normalize each step
            normalized_steps = []
            for local_idx, step in enumerate(deduped_steps):
                # Extract step and machine names for default estimation
                step_name = step.get("name") or step.get("nom_etape") or f"Step {local_idx + 1}"
                machine_name = step.get("machine") or step.get("machine_name")
                
                # Normalize parameters with step context for better defaults
                raw_params = step.get("parametres_process", {})
                normalized_params = normalize_parametres_process(raw_params, step_name, machine_name)
                
                # Create normalized step
                normalized_step = {
                    "nom_etape": step_name,
                    "numero_etape": step.get("step") or step.get("numero_etape") or (local_idx + 1),
                    "type_operation": step.get("type_operation"),
                    "description": step.get("description"),
                    "machine": machine_name,
                    "machines_utilisees": step.get("machines_utilisees"),
                    "inputs": step.get("inputs"),
                    "outputs": step.get("outputs"),
                    "qc": step.get("qc"),
                    "parametres_process": normalized_params
                }
                
                # Remove None values for cleaner output
                normalized_step = {k: v for k, v in normalized_step.items() if v is not None}
                
                normalized_steps.append(normalized_step)
                
                # Create UI step
                ui_step = {
                    "group_id": group_id,
                    "product_family": product_family,
                    "local_step_no": local_idx + 1,
                    "global_step_no": global_step_no,
                    **normalized_step  # Include all step data
                }
                
                # Add prefixed nom_etape for UI display
                ui_step["nom_etape"] = f"[{product_family}] {ui_step['nom_etape']}"
                
                ui_steps.append(ui_step)
                global_step_no += 1
            
            # Add to processes
            processes.append({
                "product_family": product_family,
                "group_id": group_id,
                "steps": normalized_steps
            })
    
    else:
        # Flat structure: treat as single product group
        product_family = "Production"
        group_id = "group_1"
        
        # Deduplicate
        deduped_steps, dup_count = deduplicate_steps_within_group(raw_processes, product_family)
        total_duplicate_count += dup_count
        
        # Normalize each step
        normalized_steps = []
        for local_idx, step in enumerate(deduped_steps):
            # Extract step and machine names for default estimation
            step_name = step.get("nom_etape") or step.get("name") or f"Step {local_idx + 1}"
            machine_name = step.get("machine") or step.get("machine_name")
            
            # Normalize parameters with step context for better defaults
            raw_params = step.get("parametres_process", {})
            normalized_params = normalize_parametres_process(raw_params, step_name, machine_name)
            
            # Create normalized step
            normalized_step = {
                "nom_etape": step_name,
                "numero_etape": step.get("numero_etape") or step.get("step") or (local_idx + 1),
                "type_operation": step.get("type_operation"),
                "description": step.get("description"),
                "machine": machine_name,
                "machines_utilisees": step.get("machines_utilisees"),
                "inputs": step.get("inputs"),
                "outputs": step.get("outputs"),
                "qc": step.get("qc"),
                "parametres_process": normalized_params
            }
            
            # Remove None values
            normalized_step = {k: v for k, v in normalized_step.items() if v is not None}
            
            normalized_steps.append(normalized_step)
            
            # Create UI step
            ui_step = {
                "group_id": group_id,
                "product_family": product_family,
                "local_step_no": local_idx + 1,
                "global_step_no": global_step_no,
                **normalized_step
            }
            
            ui_steps.append(ui_step)
            global_step_no += 1
        
        # Add to processes
        processes.append({
            "product_family": product_family,
            "group_id": group_id,
            "steps": normalized_steps
        })
    
    # Calculate totals
    total_steps = sum(len(p["steps"]) for p in processes)
    
    return {
        "processes": processes,
        "ui_steps": ui_steps,
        "total_steps": total_steps,
        "total_ui_steps": len(ui_steps),
        "total_groups": len(processes),
        "duplicate_count": total_duplicate_count
    }
