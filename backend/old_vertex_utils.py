import os
import base64
import mimetypes
from pathlib import Path
from typing import List, Optional, Union, Dict, Any
from dataclasses import dataclass, field
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
image_client = genai.Client(api_key=os.getenv("IMAGE_API_KEY"))
video_client = genai.Client(api_key=os.getenv("VIDEO_API_KEY"))

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
    Generates text using Gemini 2.5 Flash with multimodal support.
    
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
        config: Optional MessageConfig for generation parameters
        
    Returns:
        Generated text response
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

    response = gemini_client.models.generate_content(
        model=model_id,
        contents=contents,
        config=gen_config,
    )
    
    return response.text

def generate_image(
    prompt: str,
    images: Optional[List[Union[bytes, str]]] = None,
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
    model_id = os.getenv("IMAGE_MODEL", "gemini-3-pro-image-preview")
    
    contents = []
    if images:
        for img in images[:14]:
            img_bytes = base64.b64decode(img) if isinstance(img, str) else img
            contents.append(types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"))
    contents.append(prompt)

    response = image_client.models.generate_content(
        model=model_id,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_modalities=["IMAGE", "TEXT"],
            temperature=temperature,
            top_p=top_p,
            top_k=64,
            candidate_count=1,
        )
    )

    result = []
    for part in response.candidates[0].content.parts:
        if part.inline_data and part.inline_data.mime_type.startswith("image/"):
            result.append(part.inline_data.data)
    return result

def generate_video(
    prompt: str,
    image: Optional[Union[bytes, str]] = None,
    aspect_ratio: str = "16:9",
    duration_seconds: int = 5,
) -> str:
    """
    Generates video using Veo 2 (veo-2.0-generate-001).
    
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

    operation = video_client.models.generate_videos(
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
        operation = video_client.operations.get(operation)

    return operation.result.generated_videos[0].video.uri


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