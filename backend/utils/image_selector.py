from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional

from config import CACHE_IMAGES_DIR


def _score(name: str, candidate: str) -> float:
    return SequenceMatcher(None, name.lower(), candidate.lower()).ratio()


def find_best_image(machine_name: str) -> Optional[Path]:
    if not machine_name:
        return None
    if not CACHE_IMAGES_DIR.exists():
        return None
    candidates = list(CACHE_IMAGES_DIR.glob("*"))
    if not candidates:
        return None

    best = None
    best_score = 0.0
    for path in candidates:
        if not path.is_file():
            continue
        stem = path.stem.replace("_", " ").replace("-", " ")
        score = _score(machine_name, stem)
        if score > best_score:
            best_score = score
            best = path
    return best


def get_random_image() -> Optional[Path]:
    import random
    if not CACHE_IMAGES_DIR.exists():
        return None
    candidates = list(CACHE_IMAGES_DIR.glob("*"))
    valid = [p for p in candidates if p.is_file()]
    if not valid:
        return None
    return random.choice(valid)
