import os
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = BASE_DIR / "uploads"
CACHE_DIR = BASE_DIR / "cache"
CACHE_IMAGES_DIR = CACHE_DIR / "images"
EMAIL_CACHE_DIR = CACHE_DIR / "email"
EMAIL_ATTACHMENTS_DIR = EMAIL_CACHE_DIR / "attachments"
TEMPLATE_DIR = BASE_DIR / "template"

# CREATE_IMAGES = os.getenv("RIBIF_CREATE_IMAGES", "1") in ("1", "true", "True")
CREATE_IMAGES = True


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "y", "on")

def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(str(raw).strip())
    except ValueError:
        return default


SKIP_MODULE_1 = _env_bool("SKIP_MODULE_1", False)
SKIP_MODULE_2 = _env_bool("SKIP_MODULE_2", False)
SKIP_MODULE_3 = _env_bool("SKIP_MODULE_3", False)
SKIP_MODULE_4 = _env_bool("SKIP_MODULE_4", False)
SKIP_MODULE_5 = _env_bool("SKIP_MODULE_5", False)
SKIP_MODULE_6 = _env_bool("SKIP_MODULE_6", False)
SKIP_MODULE_7 = _env_bool("SKIP_MODULE_7", False)
SKIP_MODULE_8 = _env_bool("SKIP_MODULE_8", False)
SKIP_MODULE_9 = _env_bool("SKIP_MODULE_9", False)

PIPLEINE_3D_CAP = _env_int("PIPLEINE_3D_CAP", 6)

OUTPUT_DIRS = {
    "module1": DATA_DIR / "module_1",
    "module2": DATA_DIR / "module_2",
    "module3": DATA_DIR / "module_3",
    "module4": DATA_DIR / "module_4",
    "module5": DATA_DIR / "module_5",
    "module6": DATA_DIR / "module_6",
    "module7": DATA_DIR / "module_7",
    "module8": DATA_DIR / "module_8",
    "module9": DATA_DIR / "module_9",
    "email": DATA_DIR / "email",
    "catalogs": DATA_DIR / "catalogs",
    "videos": DATA_DIR / "videos",
}

BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:5000")


def ensure_dirs() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    EMAIL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    EMAIL_ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    for path in OUTPUT_DIRS.values():
        path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def get_output_dir(name: str) -> Path:
    return OUTPUT_DIRS[name]


ensure_dirs()
