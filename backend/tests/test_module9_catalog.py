"""
Module 9 technical catalog, run locally.

The PDF is built in memory with ReportLab from Module 1 and Module 4 output.
The only outside calls are image downloads (requests.get) and the Supabase
upload in the route; both are replaced here. The sample inputs are the saved
pipeline outputs in backend/template/.
"""

import io
import json
from pathlib import Path

import pytest
import requests
from PIL import Image
from pypdf import PdfReader

from utils.module_9.core import CatalogInput, RIBIFModule9Catalog

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "template"


def _load(name):
    return json.loads((TEMPLATE_DIR / f"{name}.json").read_text(encoding="utf-8"))


@pytest.fixture
def module1_data():
    return _load("module1")


@pytest.fixture
def fake_image_download(monkeypatch):
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), (200, 30, 30)).save(buf, format="PNG")
    requested = []

    class Reply:
        status_code = 200
        content = buf.getvalue()

    def fake_get(url, timeout=None, headers=None):
        requested.append(url)
        return Reply()

    monkeypatch.setattr(requests, "get", fake_get)
    return requested


def _pdf_text(pdf_bytes):
    return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf_bytes)).pages)


def test_catalog_pdf_is_built_from_pipeline_outputs(module1_data, fake_image_download):
    result = RIBIFModule9Catalog().generate_catalog_in_memory(
        CatalogInput(module1_data=module1_data, module4_data=_load("module4"))
    )

    pdf = result["pdf_content"]
    assert pdf.startswith(b"%PDF")
    assert result["pdf_size_bytes"] == len(pdf)
    assert result["pdf_filename"].endswith(".pdf")

    info = module1_data["stage_1_informations_generales"]["informations_generales"]
    assert result["company_name"] == info["nom_entreprise"]
    text = _pdf_text(pdf).upper()
    assert info["nom_entreprise"].upper().split()[0] in text


def test_catalog_survives_failed_image_downloads(module1_data, monkeypatch):
    def offline_get(*args, **kwargs):
        raise requests.ConnectionError("offline")

    monkeypatch.setattr(requests, "get", offline_get)

    result = RIBIFModule9Catalog().generate_catalog_in_memory(CatalogInput(module1_data=module1_data))

    assert result["pdf_content"].startswith(b"%PDF")


def test_non_http_image_paths_are_not_fetched(fake_image_download):
    assert RIBIFModule9Catalog()._get_image_base64("data/images/local.png") is None
    assert fake_image_download == []


def test_route_returns_catalog_without_a_database(module1_data, monkeypatch, fake_image_download):
    import app as backend_app
    import routes.module9 as route

    monkeypatch.setattr(route, "SKIP_MODULE_9", False)
    monkeypatch.setattr(route, "get_supabase", lambda: None)

    response = backend_app.app.test_client().post("/api/module9/catalog", json={"module1_data": module1_data})

    assert response.status_code == 200
    body = response.get_json()
    assert body["message"] == "Catalog generated successfully"
    assert body["data"]["pdf_size_bytes"] > 0
    assert "pdf_content" not in body["data"]
