import os
import json
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

# Check if we're in a read-only filesystem environment (serverless/containerized)
# Use /tmp for writable directories in such environments
def _is_writable(path: Path) -> bool:
    """Check if a directory path is writable."""
    try:
        test_path = path / ".write_test"
        path.mkdir(parents=True, exist_ok=True)
        test_path.touch()
        test_path.unlink()
        return True
    except (OSError, PermissionError):
        return False

# Determine the writable base directory
def _get_writable_base() -> Path:
    """Get a writable base directory, falling back to /tmp if needed."""
    # First try the BASE_DIR
    if _is_writable(BASE_DIR / "data"):
        return BASE_DIR
    # Fall back to /tmp for serverless environments
    tmp_base = Path("/tmp/ribif")
    try:
        tmp_base.mkdir(parents=True, exist_ok=True)
        return tmp_base
    except OSError:
        # Last resort: use system temp directory
        import tempfile
        return Path(tempfile.gettempdir()) / "ribif"

WRITABLE_BASE = _get_writable_base()

# Use writable base for data directories that need write access
DATA_DIR = WRITABLE_BASE / "data"
UPLOAD_DIR = WRITABLE_BASE / "uploads"
CACHE_DIR = WRITABLE_BASE / "cache"
CACHE_IMAGES_DIR = CACHE_DIR / "images"
EMAIL_CACHE_DIR = CACHE_DIR / "email"
EMAIL_ATTACHMENTS_DIR = EMAIL_CACHE_DIR / "attachments"

# Template directory stays in BASE_DIR (read-only is fine for templates)
TEMPLATE_DIR = BASE_DIR / "template"


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

# CREATE_IMAGES = os.getenv("RIBIF_CREATE_IMAGES", "1") in ("1", "true", "True")
CREATE_MACHINE_IMAGES = _env_bool("CREATE_MACHINE_IMAGES", True)


SKIP_MODULE_1 = _env_bool("SKIP_MODULE_1", False)
SKIP_MODULE_2 = _env_bool("SKIP_MODULE_2", False)
SKIP_MODULE_3 = _env_bool("SKIP_MODULE_3", False)
SKIP_MODULE_4 = _env_bool("SKIP_MODULE_4", False)
SKIP_MODULE_5 = _env_bool("SKIP_MODULE_5", False)
SKIP_MODULE_6 = _env_bool("SKIP_MODULE_6", False)
SKIP_MODULE_7 = _env_bool("SKIP_MODULE_7", False)
SKIP_MODULE_8 = _env_bool("SKIP_MODULE_8", False)
SKIP_MODULE_9 = _env_bool("SKIP_MODULE_9", False)

CREATE_REALISTIC_RENDER = _env_bool("CREATE_REALISTIC_RENDER", True)
CREATE_3D_MODEL = _env_bool("CREATE_3D_MODEL", True)

PIPLEINE_3D_CAP = _env_int("PIPLEINE_3D_CAP", 6)

# Web Search Configuration
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
BING_API_KEY = os.getenv("BING_API_KEY")
GOOGLE_CSE_KEY = os.getenv("GOOGLE_CSE_KEY")
GOOGLE_CSE_CX = os.getenv("GOOGLE_CSE_CX")

SEARCH_CACHE_DIR = CACHE_DIR / "search"
SEARCH_CACHE_TTL_HOURS = _env_int("SEARCH_CACHE_TTL_HOURS", 24)
SEARCH_RATE_LIMIT_PER_MINUTE = _env_int("SEARCH_RATE_LIMIT_PER_MINUTE", 30)

WEB_SEARCH_ENABLED = _env_bool("WEB_SEARCH_ENABLED", True)
PREFER_WEB_DATA = _env_bool("PREFER_WEB_DATA", True)

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
    """Create necessary directories, handling read-only filesystem gracefully."""
    dirs_to_create = [
        UPLOAD_DIR,
        CACHE_DIR,
        CACHE_IMAGES_DIR,
        EMAIL_CACHE_DIR,
        EMAIL_ATTACHMENTS_DIR,
        SEARCH_CACHE_DIR,
        *OUTPUT_DIRS.values(),
    ]
    
    for dir_path in dirs_to_create:
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            # Log warning but don't fail - directory might be created on-demand
            print(f"Warning: Could not create directory {dir_path}: {e}")
    
    # Template directory is read-only in production, don't try to create it
    # It should be part of the deployed code


def write_json(path: Path, payload: dict) -> Path:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass  # Directory might already exist or be in a read-only section
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def get_output_dir(name: str) -> Path:
    return OUTPUT_DIRS[name]


ensure_dirs()
