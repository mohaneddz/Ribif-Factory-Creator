"""
AI + I/O utilities: data loading, image caching, background removal,
Gemini/Replicate calls.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import threading
import mimetypes
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests
from PIL import Image

from dotenv import load_dotenv

try:
    from . import vertex_utils as vtx
    from .log_utils import info, warn
    from .config import (
        ASSETS_DIR,
        LOCAL_IMAGES_DIR,
        CACHE_FILE,
        REPLICATE_API_TOKEN,
        REPLICATE_MODEL,
        BASE_IMAGE_URL,
        BASE_DIR,
    )
except ImportError:  # Fallback for running as a script.
    import vertex_utils as vtx
    from log_utils import info, warn
    from config import (
        ASSETS_DIR,
        LOCAL_IMAGES_DIR,
        CACHE_FILE,
        REPLICATE_API_TOKEN,
        REPLICATE_MODEL,
        BASE_IMAGE_URL,
        BASE_DIR,
    )

load_dotenv()

_CACHE_LOCK = threading.Lock()
_CACHE: Optional[Dict[str, Any]] = None


def _auto_workers(item_count: int, multiplier: int = 4, min_workers: int = 4, max_workers: Optional[int] = None) -> int:
    cpu = os.cpu_count() or 4
    target = cpu * multiplier
    if max_workers:
        target = min(target, max_workers)
    if item_count <= 0:
        return max(1, min_workers)
    return max(min_workers, min(item_count, target))


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _ensure_dirs() -> None:
    os.makedirs(ASSETS_DIR, exist_ok=True)
    os.makedirs(LOCAL_IMAGES_DIR, exist_ok=True)


def _local_image_path(url: str, content_type: Optional[str] = None) -> str:
    ext = None
    if content_type:
        ext = mimetypes.guess_extension(content_type.split(";")[0].strip())
    if not ext:
        ext = os.path.splitext(url.split("?", 1)[0])[1]
    if not ext:
        ext = ".jpg"
    filename = f"img_{_hash(url)}{ext}"
    return os.path.join(LOCAL_IMAGES_DIR, filename)


def _download_url_original(url: str) -> Optional[str]:
    if not url:
        return None

    _ensure_dirs()
    cache = _load_cache()
    cached_path = cache.get("originals", {}).get(url)
    if cached_path and os.path.exists(cached_path):
        info(f"Cache hit (original): {url} -> {cached_path}")
        return cached_path

    for attempt in range(3):
        try:
            headers = {"User-Agent": "Mozilla/5.0", "Accept": "image/*,*/*;q=0.8"}
            r = requests.get(url, headers=headers, timeout=30)
            r.raise_for_status()
            content_type = r.headers.get("Content-Type", "")
            if content_type and "image" not in content_type:
                warn(f"URL did not return an image: {url} ({content_type})")
                return None
            local_path = _local_image_path(url, content_type)
            with open(local_path, "wb") as f:
                f.write(r.content)

            def _update(c):
                c.setdefault("originals", {})[url] = local_path
            _update_cache(_update)
            return local_path
        except Exception as exc:
            if attempt == 2:
                warn(f"Image download failed: {url} => {exc}")
                return None
            continue


def _nobg_cache_path(key: str) -> str:
    return os.path.join(ASSETS_DIR, f"img_{_hash(key)}_nobg.png")


def _load_cache() -> Dict[str, Any]:
    global _CACHE
    with _CACHE_LOCK:
        if _CACHE is not None:
            return _CACHE
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    _CACHE = json.load(f)
            except Exception:
                _CACHE = {"version": 1, "downloads": {}, "backgrounds": {}}
        else:
            _CACHE = {"version": 1, "downloads": {}, "backgrounds": {}}
        return _CACHE


def _save_cache(cache: Dict[str, Any]) -> None:
    _ensure_dirs()
    tmp_path = f"{CACHE_FILE}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)
    os.replace(tmp_path, CACHE_FILE)


def _update_cache(update_fn) -> None:
    with _CACHE_LOCK:
        cache = _load_cache()
        update_fn(cache)
        _save_cache(cache)


# =========================
# Data loading
# =========================
def load_data(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    if isinstance(raw, dict) and "machines" in raw:
        items = raw["machines"]
    elif isinstance(raw, list):
        items = raw
    else:
        raise ValueError("data.json must be a list or an object with 'machines' key")

    out: List[Dict[str, Any]] = []
    for item in items:
        out.append(
            {
                "model": str(item.get("model") or item.get("name") or "Machine"),
                "name": str(item.get("name") or item.get("model") or ""),
                "width": float(item.get("width", 1.0)),
                "height": float(item.get("height", 1.0)),
                "count": int(item.get("count", 1)),
                "image": str(item.get("image", "")),
                "use": str(item.get("use", "")),
            }
        )
    return out


def load_pipeline(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_flows(flows: Iterable[Any]) -> List[Tuple[str, str]]:
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
    if force_regen:
        return True
    if not os.path.exists(links_path):
        return True
    try:
        with open(links_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "flows" not in data:
            return True
        return False
    except Exception:
        return True


def expand_flows_to_instances(flows: List[Tuple[str, str]], machines: List[Dict[str, Any]]) -> List[Tuple[str, str]]:
    machine_counts: Dict[str, int] = {}
    for m in machines:
        model = str(m.get("model") or m.get("name") or "Machine")
        machine_counts[model] = int(m.get("count", 1) or 1)

    expanded: List[Tuple[str, str]] = []
    for src_model, dst_model in flows:
        src_count = machine_counts.get(src_model, 1)
        dst_count = machine_counts.get(dst_model, 1)

        if src_count == 1:
            src_instances = [src_model]
        else:
            src_instances = [f"{src_model}_{i+1}" for i in range(src_count)]

        if dst_count == 1:
            dst_instances = [dst_model]
        else:
            dst_instances = [f"{dst_model}_{i+1}" for i in range(dst_count)]

        pairs = min(len(src_instances), len(dst_instances))
        for i in range(pairs):
            expanded.append((src_instances[i], dst_instances[i]))

        if len(src_instances) > len(dst_instances):
            for i in range(pairs, len(src_instances)):
                expanded.append((src_instances[i], dst_instances[0]))
        elif len(dst_instances) > len(src_instances):
            for i in range(pairs, len(dst_instances)):
                expanded.append((src_instances[0], dst_instances[i]))

    return expanded


# =========================
# Image caching + background removal
# =========================
def download_image(url: str) -> Optional[str]:
    """Download an image and store ONLY the no-background version in cache."""
    if not url:
        return None

    _ensure_dirs()
    cache = _load_cache()
    cached_path = cache.get("downloads", {}).get(url)
    if cached_path and os.path.exists(cached_path):
        info(f"Cache hit: {url} -> {cached_path}")
        return cached_path

    target_path = _nobg_cache_path(url)
    if os.path.exists(target_path):
        def _update(c):
            c.setdefault("downloads", {})[url] = target_path
        _update_cache(_update)
        info(f"Cache hit (file): {url} -> {target_path}")
        return target_path

    try:
        local_path = _download_url_original(url)
        if not local_path or not os.path.exists(local_path):
            return None
        with open(local_path, "rb") as f:
            cleaned = remove_background(f.read())
        with open(target_path, "wb") as f:
            f.write(cleaned)

        def _update(c):
            c.setdefault("downloads", {})[url] = target_path
            c.setdefault("backgrounds", {})[url] = target_path
            c.setdefault("originals", {})[url] = local_path
        _update_cache(_update)
        return target_path
    except Exception as exc:
        warn(f"Image download failed: {url} => {exc}")
        return None


def resolve_image_source(source: str) -> Optional[str]:
    if not source:
        return None

    if source.startswith("http://") or source.startswith("https://"):
        return download_image(source)

    # absolute path
    if os.path.exists(source):
        return _cache_local_nobg(source)

    # relative to local images dir
    local_path = os.path.join(LOCAL_IMAGES_DIR, source)
    if os.path.exists(local_path):
        return _cache_local_nobg(local_path)

    # relative to project root
    project_path = os.path.join(os.path.dirname(__file__), source)
    if os.path.exists(project_path):
        return _cache_local_nobg(project_path)

    # relative web path (requires BASE_IMAGE_URL)
    if _looks_like_relative_url(source):
        base = (BASE_IMAGE_URL or "").rstrip("/")
        if base:
            return download_image(f"{base}/{source.lstrip('/')}")
        warn("Relative URL provided but BASE_IMAGE_URL is not set.")

    # if already cached
    cached_path = _nobg_cache_path(source)
    if os.path.exists(cached_path):
        info(f"Cache hit: {source} -> {cached_path}")
        return cached_path

    warn(f"Image not found: {source}")
    return None


def _looks_like_relative_url(value: str) -> bool:
    if value.startswith(("/", "./", "../")):
        return True
    return "/" in value and "://" not in value


def _cache_local_nobg(path: str) -> str:
    """Read a local image and store only the no-background version in cache."""
    _ensure_dirs()
    key = os.path.abspath(path)
    target = _nobg_cache_path(key)
    if os.path.exists(target):
        info(f"Cache hit: {path} -> {target}")
        return target

    with open(path, "rb") as f:
        data = f.read()
    cleaned = remove_background(data)
    with open(target, "wb") as f:
        f.write(cleaned)
    return target


def remove_background(image_bytes: bytes) -> bytes:
    """
    Use vertex_utils background removal (single API key stack),
    then clean residual green spill.
    """
    import numpy as np

    base = vtx.remove_background(image_bytes)
    img = Image.open(io.BytesIO(base)).convert("RGBA")
    arr = np.array(img)
    r, g, b, a = arr[..., 0], arr[..., 1], arr[..., 2], arr[..., 3]
    green_left = (g > 150) & (r < 120) & (b < 120) & (a > 0)
    arr[..., 0][green_left] = 200
    arr[..., 1][green_left] = 200
    arr[..., 2][green_left] = 200
    out = Image.fromarray(arr, "RGBA")

    buf = io.BytesIO()
    out.save(buf, format="PNG")
    return buf.getvalue()


def remove_background_file(path: str) -> Optional[str]:
    """Create a no-background copy in cache only."""
    if not path:
        return None

    out_path = _nobg_cache_path(os.path.abspath(path))
    if os.path.exists(out_path):
        info(f"Cache hit: {path} -> {out_path}")
        return out_path

    try:
        with open(path, "rb") as f:
            img_bytes = f.read()
        cleaned = remove_background(img_bytes)
        with open(out_path, "wb") as f:
            f.write(cleaned)

        def _update(c):
            c.setdefault("backgrounds", {})[path] = out_path
        _update_cache(_update)
        return out_path
    except Exception as exc:
        warn(f"Background removal failed for {path}: {exc}")
        return None


def process_machine_images(machines: List[Dict[str, Any]], workers: Optional[int] = None) -> None:
    """Parallel download + background removal. Mutates machines in-place."""
    if not machines:
        return

    def _process(m: Dict[str, Any]) -> Tuple[str, Optional[str], Optional[str]]:
        src = str(m.get("image", ""))
        if src.startswith("http://") or src.startswith("https://"):
            local_path = _download_url_original(src)
            if local_path:
                m["image"] = os.path.relpath(local_path, BASE_DIR)
                src = m["image"]
        nobg = resolve_image_source(src)
        m["image_path"] = nobg
        m["image_nobg_path"] = nobg
        return str(m.get("model") or m.get("name") or "Machine"), nobg, nobg

    if not workers or workers <= 0:
        workers = _auto_workers(len(machines))
    info(f"Image workers: {workers}")

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(_process, m) for m in machines]
        for fut in as_completed(futures):
            try:
                fut.result()
            except Exception as exc:
                warn(f"Image processing failed: {exc}")


def prefetch_machine_images(machines: List[Dict[str, Any]], workers: Optional[int] = None) -> None:
    """Download originals only and set machine image paths to local relative files."""
    if not machines:
        return

    def _process(m: Dict[str, Any]) -> Optional[str]:
        src = str(m.get("image", ""))
        if src.startswith("http://") or src.startswith("https://"):
            local_path = _download_url_original(src)
            if local_path:
                m["image"] = os.path.relpath(local_path, BASE_DIR)
                return local_path
        return None

    if not workers or workers <= 0:
        workers = _auto_workers(len(machines))
    info(f"Image prefetch workers: {workers}")

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(_process, m) for m in machines]
        for fut in as_completed(futures):
            try:
                fut.result()
            except Exception as exc:
                warn(f"Image prefetch failed: {exc}")


def generate_message(
    prompt: str,
    system_instruction: Optional[str] = None,
    images: Optional[List[bytes]] = None,
    temperature: float = 1.0,
    top_p: float = 0.95,
) -> str:
    return vtx.generate_message(
        prompt=prompt,
        system_instruction=system_instruction,
        images=images,
        temperature=temperature,
        top_p=top_p,
    )


def generate_image(
    prompt: str,
    images: Optional[List[bytes]] = None,
    candidate_count: int = 1,
    system_instruction: Optional[str] = None,
    temperature: float = 1.0,
    top_p: float = 0.95,
) -> List[bytes]:
    return vtx.generate_image(
        prompt=prompt,
        images=images,
        candidate_count=candidate_count,
        system_instruction=system_instruction,
        temperature=temperature,
        top_p=top_p,
    )


# =========================
# Replicate
# =========================
def generate_3d_model(
    image_path: str,
    texture_size: int = 2048,
    mesh_simplify: float = 0.9,
    generate_model: bool = True,
    save_gaussian_ply: bool = True,
    ss_sampling_steps: int = 38,
) -> Dict[str, Any]:
    """
    Generates a 3D model from a single image using Replicate.
    """
    import replicate

    if not image_path or not os.path.exists(image_path):
        raise RuntimeError(f"Input image not found for 3D generation: {image_path}")

    if REPLICATE_API_TOKEN and not os.getenv("REPLICATE_API_TOKEN"):
        os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN
    if not os.getenv("REPLICATE_API_TOKEN"):
        raise RuntimeError("REPLICATE_API_TOKEN is missing. Add it to your .env file.")

    input_data = {
        "image": open(image_path, "rb"),
        "texture_size": texture_size,
        "mesh_simplify": mesh_simplify,
        "generate_model": generate_model,
        "save_gaussian_ply": save_gaussian_ply,
        "ss_sampling_steps": ss_sampling_steps,
    }

    try:
        output = replicate.run(REPLICATE_MODEL, input=input_data)
        return output
    except Exception as exc:
        raise RuntimeError(f"Replicate 3D generation failed: {exc}") from exc
