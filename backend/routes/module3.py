import base64
import os
from pathlib import Path
from typing import Any, List, Optional

import requests
from flask import Blueprint, jsonify, request

from config import OUTPUT_DIRS, SKIP_MODULE_3
from supabase_utils import get_supabase, insert_video
from utils.app_helpers import (
    get_request_project_id,
    get_request_user_id,
    load_template_payload,
    upload_and_register_file,
    upload_with_name_timestamp,
)
from utils.logger import log_skip, get_logger

# Lazy import for faster startup
_vertex_generate_video = None

def _get_generate_video():
    global _vertex_generate_video
    if _vertex_generate_video is None:
        try:
            from vertex_utils import generate_video
        except Exception:
            from utils.module_2.vertex_utils import generate_video
        _vertex_generate_video = generate_video
    return _vertex_generate_video

bp_module3 = Blueprint("module3", __name__)

CLIP_SECONDS = 8


def _load_image_input(value: Any) -> Optional[bytes]:
    if value is None:
        return None
    if isinstance(value, Path):
        value = str(value)
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        data = value.strip()
        if data.startswith("data:image"):
            try:
                _, b64 = data.split(",", 1)
                return base64.b64decode(b64)
            except Exception:
                return None
        if data.startswith("http://") or data.startswith("https://"):
            try:
                resp = requests.get(data, timeout=30)
                resp.raise_for_status()
                return resp.content
            except Exception:
                return None
        if os.path.exists(data):
            try:
                with open(data, "rb") as f:
                    return f.read()
            except Exception:
                return None
        try:
            # validate=True so a missing file path is not "decoded" into garbage bytes
            return base64.b64decode(data, validate=True)
        except Exception:
            return None
    return None


def _collect_module2_images(payload: Optional[dict]) -> List[bytes]:
    candidates: List[Any] = []
    if isinstance(payload, dict):
        for key in (
            "layout_realistic",
            "layout_realistic_clean",
            "layout_2d",
            "layout_realistic_url",
            "layout_realistic_clean_url",
            "layout_2d_url",
        ):
            if payload.get(key):
                candidates.append(payload.get(key))
        inner = payload.get("data") if isinstance(payload.get("data"), dict) else None
        if inner:
            for key in (
                "layout_realistic",
                "layout_realistic_clean",
                "layout_2d",
                "layout_realistic_url",
                "layout_realistic_clean_url",
                "layout_2d_url",
            ):
                if inner.get(key):
                    candidates.append(inner.get(key))
    if not candidates:
        candidates = [
            OUTPUT_DIRS["module2"] / "realistic_layout.png",
            OUTPUT_DIRS["module2"] / "realistic_clean.png",
            OUTPUT_DIRS["module2"] / "layout_square.png",
        ]
    images: List[bytes] = []
    for src in candidates:
        img = _load_image_input(src)
        if img:
            images.append(img)
    return images


def _ensure_three(images: List[bytes]) -> List[bytes]:
    if not images:
        return images
    while len(images) < 3:
        images.append(images[-1])
    return images[:3]


@bp_module3.route("/api/module3/video", methods=["POST"])
def generate_video_from_images():
    import time

    try:
        if SKIP_MODULE_3:
            log_skip("module3.generate_video_from_images", reason="SKIP_MODULE_3")
            payload = load_template_payload("module3") or {}
            project_id = get_request_project_id(include_form=True, include_json=True)
            if isinstance(payload, dict) and project_id:
                payload["project_id"] = payload.get("project_id") or project_id
            return jsonify(payload)

        project_id = get_request_project_id(include_form=True, include_json=True)
        default_prompts = [
            "Cinematic slow pan across industrial manufacturing equipment, smooth camera movement, professional lighting, 4K quality",
            "Dramatic walkthrough of factory production line, machines operating, cinematic motion blur, professional industrial video",
            "Aerial-style view of manufacturing facility interior, sweeping camera movement, dramatic lighting, high production value",
        ]

        prompts = default_prompts[:]
        images_bytes: List[bytes] = []
        payload = None

        if "image1" in request.files:
            prompts = []
            for i, key in enumerate(["image1", "image2", "image3"]):
                if key in request.files:
                    file = request.files[key]
                    if file.filename:
                        images_bytes.append(file.read())
                        prompts.append(request.form.get(f"prompt{i+1}", default_prompts[i]))
            if not prompts:
                prompts = default_prompts[:]
        elif request.is_json:
            payload = request.get_json()
            images = payload.get("images", []) if isinstance(payload, dict) else []
            prompts = payload.get("prompts", default_prompts) if isinstance(payload, dict) else default_prompts
            if not isinstance(prompts, list):
                prompts = default_prompts
            for img_input in images:
                img_bytes = _load_image_input(img_input)
                if img_bytes:
                    images_bytes.append(img_bytes)

        if len(images_bytes) < 3:
            images_bytes.extend(_collect_module2_images(payload))

        images_bytes = _ensure_three(images_bytes)
        if len(images_bytes) < 3:
            return jsonify({"error": f"Need 3 images, got {len(images_bytes)}", "status": "error"}), 400

        while len(prompts) < 3:
            prompts.append(default_prompts[len(prompts)])

        images_data = [(images_bytes[i], prompts[i]) for i in range(3)]

        video_uris = []
        log = get_logger(__name__)
        generate_video = _get_generate_video()  # Lazy load
        for img_bytes, prompt in images_data:
            try:
                video_uri = generate_video(
                    prompt=prompt,
                    image=img_bytes,
                    aspect_ratio="16:9",
                    duration_seconds=CLIP_SECONDS,
                )
                log.info("module3: generated video uri=%s for prompt=%s", str(video_uri)[:200], prompt[:80])
                video_uris.append(video_uri)
            except Exception as exc:
                log.exception("module3: generate_video failed for prompt=%s", prompt[:120])
                video_uris.append(None)

        valid_videos = [v for v in video_uris if v is not None]
        if not valid_videos:
            log.error("module3: all video generation attempts failed. video_uris=%s", video_uris)
            return jsonify({"error": "All video generations failed", "status": "error", "video_uris": video_uris}), 500

        output_dir = OUTPUT_DIRS["videos"]
        os.makedirs(output_dir, exist_ok=True)

        downloaded_paths = []
        video_api_key = os.getenv("GOOGLE_API_KEY", "")

        for i, uri in enumerate(valid_videos, 1):
            local_path = output_dir / f"video_{i}_{int(time.time())}.mp4"
            try:
                if uri.startswith("gs://"):
                    from google.cloud import storage
                    parts = uri.replace("gs://", "").split("/", 1)
                    bucket_name = parts[0]
                    blob_name = parts[1] if len(parts) > 1 else ""
                    storage_client = storage.Client()
                    bucket = storage_client.bucket(bucket_name)
                    blob = bucket.blob(blob_name)
                    blob.download_to_filename(local_path)
                elif "generativelanguage.googleapis.com" in uri:
                    if "key=" not in uri:
                        separator = "&" if "?" in uri else "?"
                        download_url = f"{uri}{separator}key={video_api_key}"
                    else:
                        download_url = uri
                    response = requests.get(download_url, stream=True)
                    response.raise_for_status()
                    with open(local_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                else:
                    response = requests.get(uri, stream=True)
                    response.raise_for_status()
                    with open(local_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                downloaded_paths.append(str(local_path))
            except Exception:
                pass

        if not downloaded_paths:
            return jsonify({"error": "Failed to download any videos", "status": "partial_error"}), 500

        merged_path = output_dir / f"merged_factory_tour_{int(time.time())}.mp4"
        try:
            from moviepy import VideoFileClip, concatenate_videoclips
            clips = [VideoFileClip(path) for path in downloaded_paths]
            final_clip = concatenate_videoclips(clips, method="compose")
            final_clip.write_videofile(
                str(merged_path),
                codec="libx264",
                audio_codec="aac",
                fps=24,
                logger=None,
            )
            for clip in clips:
                clip.close()
            final_clip.close()
        except Exception:
            merged_path = Path(downloaded_paths[0])

        total_duration = len(downloaded_paths) * CLIP_SECONDS
        result = {
            "message": "Video generation completed",
            "video_url": str(merged_path),
            "individual_videos": video_uris,
            "downloaded_videos": downloaded_paths,
            "duration_seconds": total_duration,
            "status": "success",
        }
        if project_id:
            result["project_id"] = project_id

        client = get_supabase()
        owner_id = get_request_user_id()
        if client and project_id:
            try:
                merged_file_id = None
                merged_path_obj = Path(result.get("video_url", ""))
                if merged_path_obj.exists():
                    merged_file_id, signed_url, _ = upload_with_name_timestamp(
                        client=client,
                        project_id=project_id,
                        owner_id=owner_id,
                        local_path=str(merged_path_obj),
                        category="videos",
                        label=merged_path_obj.name,
                    )
                    # CRITICAL: Use the Supabase URL for the frontend
                    if signed_url:
                        result["video_url"] = signed_url
                        
                insert_video(client, project_id, merged_file_id, result)
            except Exception:
                pass

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500
