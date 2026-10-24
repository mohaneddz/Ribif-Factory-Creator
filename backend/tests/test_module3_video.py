"""
Module 3 video route, verified up to the Veo boundary.

Video generation is a Veo call (vertex_utils.generate_video) and the clips are
downloaded from Google storage URLs. Both are faked; what is checked is how the
route turns the uploaded layout images into three generation requests and how
it reports the result.
"""

import base64
import io

import pytest
import requests
from PIL import Image

import routes.module3 as route


def _png_data_uri():
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), (0, 255, 0)).save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


@pytest.fixture
def client(monkeypatch, tmp_path):
    import app as backend_app

    monkeypatch.setattr(route, "SKIP_MODULE_3", False)
    monkeypatch.setattr(route, "get_supabase", lambda: None)
    monkeypatch.setitem(route.OUTPUT_DIRS, "videos", tmp_path)
    monkeypatch.setitem(route.OUTPUT_DIRS, "module2", tmp_path / "no_module2_output")
    return backend_app.app.test_client()


@pytest.fixture
def fake_veo(monkeypatch):
    calls = []

    def fake_generate_video(prompt, image=None, aspect_ratio="16:9", duration_seconds=5):
        calls.append({"prompt": prompt, "image": image, "aspect_ratio": aspect_ratio, "duration": duration_seconds})
        return f"https://storage.example.invalid/clip_{len(calls)}.mp4"

    class Download:
        def raise_for_status(self):
            pass

        def iter_content(self, chunk_size=8192):
            yield b"\x00\x00\x00\x18ftypmp42"

    monkeypatch.setattr(route, "_get_generate_video", lambda: fake_generate_video)
    monkeypatch.setattr(requests, "get", lambda url, stream=False, **kw: Download())
    return calls


def test_one_image_is_expanded_into_three_clip_requests(client, fake_veo):
    response = client.post("/api/module3/video", json={"images": [_png_data_uri()], "prompts": ["Pan over the extrusion line"]})

    assert response.status_code == 200
    assert len(fake_veo) == 3
    assert fake_veo[0]["prompt"] == "Pan over the extrusion line"
    assert all(call["image"].startswith(b"\x89PNG") for call in fake_veo)
    assert {call["aspect_ratio"] for call in fake_veo} == {"16:9"}
    assert {call["duration"] for call in fake_veo} == {route.CLIP_SECONDS}

    body = response.get_json()
    assert body["status"] == "success"
    assert len(body["downloaded_videos"]) == 3
    assert body["duration_seconds"] == 3 * route.CLIP_SECONDS


def test_all_generation_failures_return_500(client, monkeypatch):
    def failing_generate_video(**kwargs):
        raise RuntimeError("RESOURCE_EXHAUSTED")

    monkeypatch.setattr(route, "_get_generate_video", lambda: failing_generate_video)

    response = client.post("/api/module3/video", json={"images": [_png_data_uri()]})

    assert response.status_code == 500
    assert response.get_json()["error"] == "All video generations failed"


def test_no_images_is_a_client_error(client, fake_veo):
    response = client.post("/api/module3/video", json={"images": []})

    assert response.status_code == 400
    assert fake_veo == []


def test_missing_file_paths_are_not_treated_as_base64():
    assert route._load_image_input(r"C:\missing\realistic_layout.png") is None
    assert route._load_image_input("data/module2/realistic_layout.png") is None
