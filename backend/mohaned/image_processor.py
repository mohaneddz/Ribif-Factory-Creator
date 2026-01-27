"""
Utility to remove backgrounds from all machine images in the cache.
"""

import os
from pathlib import Path
from typing import Dict
from io_utils import cache_path_for
from vertex_utils import remove_background
from config import ASSETS_DIR


def remove_all_machine_backgrounds(machines) -> Dict[str, str]:
    """
    Process all machine images to remove backgrounds.
    
    Args:
        machines: List of Machine objects with image URLs
        
    Returns:
        Dictionary mapping original image path to nobg image path
    """
    processed = {}
    
    for m in machines:
        if not m.image:
            continue
            
        # Get cached image path
        cached_path = cache_path_for(m.image)
        if not os.path.exists(cached_path):
            continue
        
        # Check if nobg version already exists
        nobg_path = cached_path.replace(".png", "_nobg.png")
        
        if os.path.exists(nobg_path):
            print(f"[*] Background already removed: {m.model}")
            processed[cached_path] = nobg_path
            continue
        
        # Remove background
        try:
            print(f"[*] Removing background: {m.model}")
            with open(cached_path, "rb") as f:
                img_bytes = f.read()
            
            nobg_bytes = remove_background(img_bytes)
            
            with open(nobg_path, "wb") as f:
                f.write(nobg_bytes)
            
            processed[cached_path] = nobg_path
            print(f"[+] Saved: {nobg_path}")
            
        except Exception as e:
            print(f"[!] Failed to remove background for {m.model}: {e}")
            processed[cached_path] = cached_path  # Use original
    
    return processed
