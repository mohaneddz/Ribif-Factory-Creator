import base64
import os
from pathlib import Path
from flask import Blueprint, jsonify, request

from config import OUTPUT_DIRS
from utils.app_helpers import get_request_project_id
from vertex_utils import generate_video

bp_module3 = Blueprint("module3", __name__)


@bp_module3.route("/api/module3/video", methods=["POST"])
def generate_video_from_images():
    import time
    import requests

    try:
        project_id = get_request_project_id(include_form=True, include_json=True)
        images_data = []
        default_prompts = [
            "Cinematic slow pan across industrial manufacturing equipment, smooth camera movement, professional lighting, 4K quality",
            "Dramatic walkthrough of factory production line, machines operating, cinematic motion blur, professional industrial video",
            "Aerial-style view of manufacturing facility interior, sweeping camera movement, dramatic lighting, high production value",
        ]

        if "image1" in request.files:
            for i, key in enumerate(["image1", "image2", "image3"]):
                if key in request.files:
                    file = request.files[key]
                    if file.filename:
                        img_bytes = file.read()
                        prompt = request.form.get(f"prompt{i+1}", default_prompts[i])
                        images_data.append((img_bytes, prompt))
        elif request.is_json:
            data = request.get_json()
            images = data.get("images", [])
            prompts = data.get("prompts", default_prompts)
            for i, img_input in enumerate(images[:3]):
                prompt = prompts[i] if i < len(prompts) else default_prompts[i]
                try:
                    img_bytes = base64.b64decode(img_input) if isinstance(img_input, str) else img_input
                except Exception:
                    continue
                images_data.append((img_bytes, prompt))

        if len(images_data) < 3:
            return jsonify({"error": f"Need 3 images, got {len(images_data)}", "status": "error"}), 400

        video_uris = []
        for i, (img_bytes, prompt) in enumerate(images_data, 1):
            try:
                video_uri = generate_video(
                    prompt=prompt,
                    image=img_bytes,
                    aspect_ratio="16:9",
                    duration_seconds=8,
                )
                video_uris.append(video_uri)
            except Exception:
                video_uris.append(None)

        valid_videos = [v for v in video_uris if v is not None]
        if not valid_videos:
            return jsonify({"error": "All video generations failed", "status": "error"}), 500

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
                verbose=False,
                logger=None,
            )
            for clip in clips:
                clip.close()
            final_clip.close()
        except Exception:
            merged_path = Path(downloaded_paths[0])

        total_duration = len(downloaded_paths) * 5
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

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500
