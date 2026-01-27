"""
I/O utilities: loading data, caching images, loading pipeline.
"""

import os
import json
import hashlib
from typing import List, Optional, Dict, Any
import requests
from PIL import Image

from models import Machine
from config import ASSETS_DIR


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def cache_path_for(url: str) -> str:
    os.makedirs(ASSETS_DIR, exist_ok=True)
    return os.path.join(ASSETS_DIR, f"img_{_hash(url)}.png")


def download_image_to_png(url: str) -> Optional[str]:
    if not url:
        return None
    path = cache_path_for(url)
    if os.path.exists(path):
        return path
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "image/*,*/*;q=0.8",
    }
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        with open(path, "wb") as f:
            f.write(r.content)
        img = Image.open(path).convert("RGBA")
        img.save(path, format="PNG")
        return path
    except Exception as e:
        print(f"[!] Image download failed: {url} => {e}")
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
        return None


def load_data(path: str) -> List[Machine]:
    """Load machines from data.json - handles both flat array and nested {machines:[]} formats"""
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    
    # Handle nested format: {"machines": [...]}
    if isinstance(raw, dict) and "machines" in raw:
        items = raw["machines"]
    # Handle flat array format: [...]
    elif isinstance(raw, list):
        items = raw
    else:
        raise ValueError("data.json must be either a list of machines or an object with 'machines' key")
    
    out: List[Machine] = []
    for item in items:
        out.append(
            Machine(
                model=str(item.get("model") or item.get("name") or "Machine"),
                name=str(item.get("name") or item.get("model") or ""),
                width=float(item.get("width", 1.0)),
                height=float(item.get("height", 1.0)),
                count=int(item.get("count", 1)),
                image=str(item.get("image", "")),
                use=str(item.get("use", "")),
            )
        )
    return out


def load_pipeline(path: str) -> Optional[Dict[str, Any]]:
    """Load pipeline from links.json"""
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_flows(flows) -> List[tuple]:
    """Normalize flow format to list of (from, to) tuples"""
    out = []
    for flow in flows:
        if isinstance(flow, dict):
            a = flow.get("from")
            b = flow.get("to")
            if a and b:
                out.append((str(a), str(b)))
        else:
            try:
                a, b = flow
                out.append((str(a), str(b)))
            except Exception:
                continue
    return out


def should_regenerate_links(links_path: str, force_regen: bool = False) -> bool:
    """
    Determine if links.json needs to be regenerated.
    
    Args:
        links_path: Path to links.json file
        force_regen: If True, force regeneration even if file exists
        
    Returns:
        True if links should be regenerated, False otherwise
    """
    if force_regen:
        return True
    
    if not os.path.exists(links_path):
        return True
    
    try:
        with open(links_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Check if it has the required structure
        if not isinstance(data, dict) or "flows" not in data:
            return True
        return False
    except Exception:
        return True


def expand_flows_to_instances(flows: List[tuple], machines: List[Machine]) -> List[tuple]:
    """
    Expand model-level flows to instance-level flows.
    
    For machines with count > 1, this creates instance IDs (e.g., A_1, A_2, A_3)
    and maps flows sequentially:
    - A -> B becomes A_1->B_1, A_2->B_2, etc.
    - Remaining sources feed the first destination instance (hub policy)
    
    Args:
        flows: List of (from_model, to_model) tuples at model level
        machines: List of Machine objects with count information
        
    Returns:
        List of (from_instance, to_instance) tuples at instance level
    """
    # Build machine count map
    machine_counts = {}
    for m in machines:
        machine_counts[m.model] = m.count if m.count > 1 else 1
    
    expanded = []
    
    for src_model, dst_model in flows:
        src_count = machine_counts.get(src_model, 1)
        dst_count = machine_counts.get(dst_model, 1)
        
        # Generate instance IDs
        if src_count == 1:
            src_instances = [src_model]
        else:
            src_instances = [f"{src_model}_{i+1}" for i in range(src_count)]
        
        if dst_count == 1:
            dst_instances = [dst_model]
        else:
            dst_instances = [f"{dst_model}_{i+1}" for i in range(dst_count)]
        
        # Sequential mapping: pair instances 1-to-1
        pairs = min(len(src_instances), len(dst_instances))
        for i in range(pairs):
            expanded.append((src_instances[i], dst_instances[i]))
        
        # Hub policy: remaining sources feed first destination
        if len(src_instances) > len(dst_instances):
            for i in range(pairs, len(src_instances)):
                expanded.append((src_instances[i], dst_instances[0]))
        # If more destinations, remaining destinations receive from first source
        elif len(dst_instances) > len(src_instances):
            for i in range(pairs, len(dst_instances)):
                expanded.append((src_instances[0], dst_instances[i]))
    
    return expanded
