# Configure ONNX Runtime for serverless environments BEFORE any imports
# This prevents crashes from CPU feature detection failures in containers
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("ONNXRUNTIME_DISABLE_ALL_OPTIMIZATION", "1")
os.environ.setdefault("ORT_DISABLE_ALL", "1")

import os  # Re-import to ensure 'os' is available for the rest of the file
import base64
import mimetypes
from pathlib import Path
from typing import List, Optional, Union, Dict, Any
from dataclasses import dataclass, field
from dotenv import load_dotenv
from google import genai
from google.genai import types

from utils.logger import get_logger
from utils.quota_manager import with_quota_check, with_retry, is_quota_error

logger = get_logger(__name__)
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

# Lazy initialization to prevent slow startup blocking health checks
_client = None

def _get_client():
    """Lazy initialization of genai Client to prevent slow startup."""
    global _client
    if _client is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("API Key not found! Make sure you created a .env file.")
        _client = genai.Client(api_key=api_key)
    return _client

@with_quota_check("vertex_ai", max_calls=1000)
@with_retry(max_attempts=2, catch_quota_errors=True)
def generate_message(
    prompt: str,
    system_instruction: Optional[str] = None,
    tools: Optional[List] = None,
    images: Optional[List[Union[bytes, str]]] = None,
    documents: Optional[List[Union[bytes, str]]] = None,
    videos: Optional[List[Union[bytes, str]]] = None,
    audio: Optional[List[Union[bytes, str]]] = None,
    temperature: float = 1.0,
    top_p: float = 0.95,
) -> str:
    """
    HARDENED: Generates text using Gemini 2.5 Flash with quota checking and retries.
    
    Supports:
    - Images: png, jpeg, webp, heic, heif (max 3,000 per prompt)
    - Documents: pdf, text/plain (max 3,000 per prompt)
    - Videos: mp4, webm, quicktime, etc. (max 10 per prompt)
    - Audio: mp3, wav, flac, etc. (max 1 per prompt)
    
    Args:
        prompt: The text prompt to send
        system_instruction: Optional system instruction
        tools: Optional list of tools/functions
        images: Optional list of image inputs (MediaInput, bytes, base64 str, or dict with 'data' and 'mime_type')
        documents: Optional list of document inputs
        videos: Optional list of video inputs  
        audio: Optional list of audio inputs
        temperature: Generation temperature (0.0 - 2.0)
        top_p: Nucleus sampling parameter
        
    Returns:
        Generated text response
        
    Raises:
        RuntimeError: If quota exhausted or authentication fails
    """
    model_id = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    # Build contents with media
    contents = []
    
    def add_media(items, mime):
        if items:
            for item in items:
                if isinstance(item, str) and item.startswith("gs://"):
                    contents.append(types.Part.from_uri(file_uri=item, mime_type=mime))
                else:
                    data = base64.b64decode(item) if isinstance(item, str) else item
                    contents.append(types.Part.from_bytes(data=data, mime_type=mime))
    
    add_media(images, "image/jpeg")
    add_media(documents, "application/pdf")
    add_media(videos, "video/mp4")
    add_media(audio, "audio/mp3")
    contents.append(prompt)
    
    gen_config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=tools,
        temperature=temperature,
        top_p=top_p,
        top_k=64,
    )

    response = _get_client().models.generate_content(
        model=model_id,
        contents=contents,
        config=gen_config,
    )
    
    return response.text

def generate_image(
    prompt: str,
    images: Optional[List[Union[bytes, str]]] = None,
    candidate_count: int = 1,
    system_instruction: Optional[str] = None,
    temperature: float = 1.0,
    top_p: float = 0.95,
) -> List[bytes]:
    """
    Generates images using gemini-3-pro-image-preview.
    
    Args:
        prompt: Text description of the image to generate
        images: Optional input images (bytes or base64 str) for editing, max 14
        system_instruction: Optional system instruction
        temperature: 0.0-2.0 (default 1.0)
        top_p: 0.0-1.0 (default 0.95)
        
    Returns:
        List of generated image bytes
    """
    import time
    from google.genai.errors import ServerError

    model_id = os.getenv("IMAGE_MODEL", "gemini-3-pro-image-preview")
    
    contents = []
    if images:
        for img in images[:14]:
            img_bytes = base64.b64decode(img) if isinstance(img, str) else img
            contents.append(types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"))
    contents.append(prompt)

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = _get_client().models.generate_content(
                model=model_id,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_modalities=["IMAGE", "TEXT"],
                    temperature=temperature,
                    top_p=top_p,
                    top_k=64,
                    candidate_count=candidate_count,
                )
            )
            
            result = []
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                    result.append(part.inline_data.data)
            return result
            
        except ServerError as e:
            if attempt < max_retries - 1:
                logger.warning(
                    "Image generation server error (500), retrying in 5s... (Attempt %s/%s)",
                    attempt + 1,
                    max_retries,
                )
                time.sleep(5)
                continue
            else:
                logger.error("Image generation failed after %s attempts.", max_retries)
                raise e
        except Exception as e:
            logger.error("Image generation failed with error: %s", e)
            raise e
    return []

@with_quota_check("vertex_ai", max_calls=100)
@with_retry(max_attempts=4, backoff=True, catch_quota_errors=True)
def generate_video(
    prompt: str,
    image: Optional[Union[bytes, str]] = None,
    aspect_ratio: str = "16:9",
    duration_seconds: int = 5,
) -> str:
    """
    Generates video using Veo 2 (veo-2.0-generate-001).
    
    Includes automatic retry with exponential backoff for 429 RESOURCE_EXHAUSTED errors.
    
    Args:
        prompt: Text description of the video to generate (English only)
        image: Optional input image (bytes or base64 str) for image-to-video, max 20MB
        aspect_ratio: "16:9" or "9:16"
        duration_seconds: 5 to 8 seconds
        
    Returns:
        GCS URI of the generated video
    """
    model_id = os.getenv("VIDEO_MODEL", "veo-2.0-generate-001")
    
    contents = [prompt]
    if image:
        if isinstance(image, str) and image.startswith("gs://"):
            contents.append(types.Part.from_uri(file_uri=image, mime_type="image/jpeg"))
        else:
            img_bytes = base64.b64decode(image) if isinstance(image, str) else image
            contents.append(types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"))

    operation = _get_client().models.generate_videos(
        model=model_id,
        prompt=prompt,
        config=types.GenerateVideosConfig(
            aspect_ratio=aspect_ratio,
            duration_seconds=duration_seconds,
        )
    )

    # Wait for the operation to complete
    import time
    while not operation.done:
        time.sleep(5)
        operation = _get_client().operations.get(operation)

    return operation.result.generated_videos[0].video.uri

def remove_background(image_bytes: bytes) -> bytes:
    """
    Smart background removal:
    - If chroma-green is detected -> pure chroma key (perfect, no rembg)
    - If DISABLE_REMBG=true or serverless detected -> skip rembg, return original
    - Otherwise -> fallback to rembg segmentation
    
    IMPORTANT: rembg/ONNX crashes in some serverless environments (Leapcell).
    Set DISABLE_REMBG=true in environment to skip rembg entirely.
    """
    import io
    import os
    import numpy as np
    from PIL import Image

    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    arr = np.array(img)

    r, g, b, a = arr[...,0], arr[...,1], arr[...,2], arr[...,3]

    # --- Detect green screen coverage ---
    green_mask = (g > 200) & (r < 80) & (b < 80)
    green_ratio = green_mask.mean()

    # --- If image is mostly green → CHROMA KEY ---
    if green_ratio > 0.15:
        arr[green_mask, 3] = 0   # transparent alpha
        out = Image.fromarray(arr, "RGBA")
    else:
        # --- Check if rembg should be disabled ---
        disable_rembg = os.environ.get("DISABLE_REMBG", "").lower() in ("true", "1", "yes")
        
        # Auto-detect serverless environment where ONNX crashes
        if not disable_rembg:
            try:
                # This file doesn't exist/parse correctly in Leapcell containers
                if not os.path.exists("/sys/devices/system/cpu/possible"):
                    disable_rembg = True
                    logger.warning("Auto-detected serverless environment, disabling rembg")
            except Exception:
                pass
        
        if disable_rembg:
            logger.warning("rembg disabled (DISABLE_REMBG=true or serverless detected)")
            logger.warning("Returning original image without background removal")
            out = img
        else:
            # --- Try rembg ---
            try:
                from rembg import remove
                out = remove(img).convert("RGBA")
            except Exception as e:
                logger.warning(f"rembg background removal failed: {e}")
                logger.warning("Falling back to original image without background removal")
                out = img

    buf = io.BytesIO()
    out.save(buf, format="PNG")
    return buf.getvalue()

def generate_3d(
    images: List[str],
    texture_size: int = 2048,
    mesh_simplify: float = 0.9,
    generate_model: bool = True,
    save_gaussian_ply: bool = True,
    ss_sampling_steps: int = 38,
) -> Dict[str, Any]:
    """
    Generates 3D models from images using Replicate's Trellis model.
    
    Args:
        images: List of image URLs to generate 3D model from
        texture_size: Size of the texture (default 2048)
        mesh_simplify: Mesh simplification factor 0.0-1.0 (default 0.9)
        generate_model: Whether to generate the model file (default True)
        save_gaussian_ply: Whether to save as Gaussian PLY (default True)
        ss_sampling_steps: Number of sampling steps (default 38)
        
    Returns:
        Dictionary containing model_file URL and other output data
    """
    import replicate
    
    input_data = {
        "images": images,
        "texture_size": texture_size,
        "mesh_simplify": mesh_simplify,
        "generate_model": generate_model,
        "save_gaussian_ply": save_gaussian_ply,
        "ss_sampling_steps": ss_sampling_steps,
    }
    
    output = replicate.run(
        "firtoz/trellis:e8f6c45206993f297372f5436b90350817bd9b4a0d52d2a76df50c1c8afa2b3c",
        input=input_data
    )
    
    return output