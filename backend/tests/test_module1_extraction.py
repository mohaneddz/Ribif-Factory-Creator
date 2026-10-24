"""
Module 1 extraction, verified offline.

Document parsing (PyMuPDF / python-docx), page selection, prompt building and
result assembly are local. The only service call is vertex_utils.generate_message
(Gemini), which is replaced here by a fake that answers per stage.
"""

import json

import fitz
import pytest
from docx import Document

import vertex_utils
from utils.module_1 import core

SAMPLE_PAGES = [
    "Fiche projet. Entreprise: Plastiques du Sahel SARL. Localisation: zone industrielle de Setif. "
    "Objectif du projet: produire des profils PVC pour menuiserie.",
    "Machines et equipements: une ligne d'extrusion bi-vis KraussMaffei, une presse a injection "
    "de 250 tonnes et un robot de palettisation.",
    "Matieres premieres: resine PVC, stabilisant calcium-zinc, additif anti-UV.",
]

STAGE_ANSWERS = {
    "informations_generales": {"informations_generales": {"nom_projet": "Profils PVC", "entreprise": "Plastiques du Sahel SARL"}},
    "matieres_premieres": {"matieres_premieres": [{"nom": "Resine PVC"}, {"nom": "Stabilisant Ca-Zn"}]},
    "produits_fabriques": {"produits_fabriques": [{"nom_produit": "Profil de fenetre"}]},
    "machines_production": {"machines_production": [
        {"nom_machine": "Ligne d'extrusion bi-vis", "quantite_necessaire": 1},
        {"nom_machine": "Presse a injection 250 t", "quantite_necessaire": 2},
        {"nom_machine": "", "quantite_necessaire": None},
    ]},
    "processus_production": {"processus_production": [{"etape": "Extrusion"}], "kpi_production": {"trs": "85%"}},
    "aspects_reglementaires": {"aspects_reglementaires": ["Norme EN 12608"], "analyse_risques": [], "opportunites": [], "recommandations": []},
}


def _schema_key(prompt):
    structure = prompt.split("REQUIRED JSON STRUCTURE", 1)[1]
    for key in STAGE_ANSWERS:
        if f'"{key}"' in structure:
            return key
    raise AssertionError("prompt carries no known stage schema")


@pytest.fixture
def fake_gemini(monkeypatch):
    prompts = []

    def fake_generate_message(prompt, system_instruction=None, temperature=1.0, top_p=0.95, **kwargs):
        prompts.append({"prompt": prompt, "system": system_instruction, "temperature": temperature})
        return "```json\n" + json.dumps(STAGE_ANSWERS[_schema_key(prompt)]) + "\n```"

    monkeypatch.setattr(vertex_utils, "generate_message", fake_generate_message)
    return prompts


@pytest.fixture
def sample_pdf(tmp_path):
    path = tmp_path / "fiche_projet.pdf"
    doc = fitz.open()
    for text in SAMPLE_PAGES:
        page = doc.new_page()
        page.insert_textbox(fitz.Rect(40, 40, 560, 800), text, fontsize=11)
    doc.save(str(path))
    doc.close()
    return path


def test_pdf_text_is_read_page_by_page(sample_pdf):
    full_text, pages = core.read_document_text(str(sample_pdf))

    assert len(pages) == 3
    assert "KraussMaffei" in pages[1]
    assert "PAGE 3" in full_text


def test_docx_is_read_as_a_single_page(tmp_path):
    path = tmp_path / "fiche.docx"
    document = Document()
    for text in SAMPLE_PAGES:
        document.add_paragraph(text)
    document.save(str(path))

    full_text, pages = core.read_document_text(str(path))

    assert pages == [full_text]
    assert "resine PVC" in full_text


def test_unsupported_extension_is_rejected(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("x")
    with pytest.raises(ValueError):
        core.read_document_text(str(path))


def test_relevant_pages_follow_stage_keywords():
    chosen = core.pick_relevant_pages(SAMPLE_PAGES, ["machine", "presse", "robot"], max_pages=1)
    assert chosen == [1]


def test_process_document_assembles_all_six_stages(sample_pdf, tmp_path, fake_gemini):
    result = core.RIBIFExtractor().process_document(str(sample_pdf), output_dir=str(tmp_path / "out"))

    assert len(fake_gemini) == 6
    assert all(call["system"] == core.SYSTEM_INSTRUCTION for call in fake_gemini)
    machine_prompt = next(c["prompt"] for c in fake_gemini if _schema_key(c["prompt"]) == "machines_production")
    assert "KraussMaffei" in machine_prompt

    machines = result["stage_4_machines_equipements"]["machines_production"]
    assert [m["nom_machine"] for m in machines] == ["Ligne d'extrusion bi-vis", "Presse a injection 250 t"]
    assert result["stage_1_informations_generales"]["informations_generales"]["entreprise"] == "Plastiques du Sahel SARL"
    assert result["ribif_metadata"]["source_file"] == "fiche_projet.pdf"
    assert "WARNINGS" not in result["ribif_metadata"]["note"]

    saved = json.loads((tmp_path / "out" / "module_1.json").read_text(encoding="utf-8"))
    assert saved["stage_4_machines_equipements"] == result["stage_4_machines_equipements"]


def test_invalid_json_gets_one_repair_attempt(monkeypatch, tmp_path):
    replies = iter(["not json at all", '{"machines_production": []}'])
    prompts = []

    def fake_generate_message(prompt, **kwargs):
        prompts.append(prompt)
        return next(replies)

    monkeypatch.setattr(vertex_utils, "generate_message", fake_generate_message)
    monkeypatch.chdir(tmp_path)  # the failed raw output is dumped under ./data

    data = core.VertexJSON().generate_json("extract machines", temperature=0.2, tag="pytest_repair")

    assert data == {"machines_production": []}
    assert len(prompts) == 2
    assert "BROKEN OUTPUT" in prompts[1]


def test_failed_stage_is_reported_not_fatal(sample_pdf, tmp_path, monkeypatch):
    def flaky_generate_message(prompt, **kwargs):
        key = _schema_key(prompt)
        if key == "produits_fabriques":
            raise RuntimeError("quota exhausted")
        return json.dumps(STAGE_ANSWERS[key])

    monkeypatch.setattr(vertex_utils, "generate_message", flaky_generate_message)

    result = core.RIBIFExtractor().process_document(str(sample_pdf), output_dir=str(tmp_path))

    assert "stage_3_produits_fabriques" not in result or result["stage_3_produits_fabriques"] == {}
    assert "quota exhausted" in result["ribif_metadata"]["note"]
    assert result["stage_4_machines_equipements"]["machines_production"]
