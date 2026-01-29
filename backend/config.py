import os
import json
from pathlib import Path
from typing import Any

# Base directory for backend
BASE_DIR = Path(__file__).resolve().parent

# Storage directories
IMAGE_CACHE_DIR = BASE_DIR / "cache"
CONTEXT_DIR = BASE_DIR / "context"

# Feature toggles
ENABLE_CACHE = True
FORCE_HARDCODED_CACHE = False

# Methods: 'hybrid' (search then create), 'search', 'creation', 'overriten'/'overwritten'
METHOD = os.getenv("RIBIF_IMAGE_METHOD", "hybrid").lower()
VALID_METHODS = ("hybrid", "search", "creation", "overriten", "overwritten")
if METHOD not in VALID_METHODS:
    METHOD = "hybrid"

# Which backends to use
USE_GEMINI = os.getenv("RIBIF_USE_GEMINI", "0") in ("1", "true", "True")
USE_GROQ = os.getenv("RIBIF_USE_GROQ", "0") in ("1", "true", "True")

# Image/data behavior
CREATE_IMAGES = os.getenv("RIBIF_CREATE_IMAGES", "1") in ("1", "true", "True")
SEARCH_IMAGES = os.getenv("RIBIF_SEARCH_IMAGES", "1") in ("1", "true", "True")

# Optional API keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")


def ensure_dirs() -> None:
    """Create required directories if they don't exist."""
    IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    CONTEXT_DIR.mkdir(parents=True, exist_ok=True)


def _safe_join(base: Path, *paths: str) -> Path:
    """Join paths safely and prevent escaping the base directory."""
    base_resolved = base.resolve()
    target = base_resolved.joinpath(*paths).resolve()
    if not str(target).startswith(str(base_resolved)):
        raise ValueError("Attempt to write outside of base directory")
    return target


def get_image_path(filename: str) -> Path:
    return _safe_join(IMAGE_CACHE_DIR, filename)


def save_image_bytes(filename: str, data: bytes) -> Path:
    p = get_image_path(filename)
    with open(p, "wb") as f:
        f.write(data)
    return p


def save_context_json(name: str, payload: Any) -> Path:
    p = _safe_join(CONTEXT_DIR, f"{name}.json")
    tmp = str(p) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    os.replace(tmp, p)
    return p


# Ensure directories at import time so other modules can write without extra checks.
ensure_dirs()
