"""
Module 6 TCO, verified offline.

Every cost estimate goes through RIBIFModule6TCO.call_gemini (Gemini). The
arithmetic around it, the validation and the heuristic fallbacks are local, so
call_gemini (or the genai client under it) is faked here.
"""

import json
from types import SimpleNamespace

import pytest

from utils.module_6.core import RIBIFModule6TCO, TCOCalculationInput

MACHINE = {
    "id": "M1",
    "name": "Extrudeuse bi-vis",
    "category": "extrusion",
    "manufacturer": "KraussMaffei",
    "original_specs": {"capacite": "500 kg/h", "puissance": "250 kW"},
}

PROJECT = {
    "machine_input": MACHINE,
    "suppliers": [{"supplier_name": "KraussMaffei", "website": "https://www.kraussmaffei.com", "region": "Germany", "source": "web"}],
    "estimated_revenue": 400_000_000,
    "stage_1_informations_generales": {"informations_generales": {"nom_entreprise": "Plastiques du Sahel", "nom_projet": "Profils PVC"}},
    "stage_2_matieres_premieres": {"matieres_premieres": [{"nom": "Resine PVC", "quantite_annuelle": 1200, "unite": "tonnes"}]},
    "stage_3_produits_fabriques": {"produits_fabriques": [{"nom_produit": "Profil de fenetre", "categorie": "menuiserie"}]},
}

MACHINE_ANSWER = {
    "estimated_purchase_price": 10_000_000,
    "implementation_cost": 1_000_000,
    "annual_operations_cost": 500_000,
    "annual_maintenance_cost": 300_000,
    "annual_downtime_cost": 100_000,
    "resale_value": 2_000_000,
    "disposal_cost": 0,
    "lifetime_years": 10,
    "confidence": "high",
    "notes": "test",
}


@pytest.fixture
def calculator():
    return RIBIFModule6TCO(api_key="offline-test-key")


def test_machine_tco_arithmetic(calculator, monkeypatch):
    monkeypatch.setattr(calculator, "call_gemini", lambda prompt, retry_strict=False: (dict(MACHINE_ANSWER), True, "{}"))

    tco = calculator.calculate_machine_tco(MACHINE, [])

    # 11M initial + 5M ops + 3M maintenance + 1M downtime - 2M resale
    assert tco.initial_cost == 11_000_000
    assert tco.total_tco == 18_000_000
    assert tco.annual_tco == 1_800_000
    assert tco.estimation_source == "llm"
    breakdown = tco.cost_breakdown
    assert breakdown.initial_pct + breakdown.operations_pct + breakdown.maintenance_pct + breakdown.downtime_pct == pytest.approx(100, abs=0.05)


def test_machine_prompt_carries_specs_and_suppliers(calculator, monkeypatch):
    prompts = []

    def fake_call(prompt, retry_strict=False):
        prompts.append(prompt)
        return dict(MACHINE_ANSWER), True, "{}"

    monkeypatch.setattr(calculator, "call_gemini", fake_call)
    calculator.estimate_machine_tco(MACHINE, [{"supplier_name": "KraussMaffei", "region": "Germany", "notes": "OEM"}])

    assert "500 kg/h" in prompts[0] and "250 kW" in prompts[0]
    assert "KraussMaffei: Germany" in prompts[0]


def test_unusable_answers_fall_back_to_heuristics(calculator, monkeypatch):
    calls = []

    def broken_call(prompt, retry_strict=False):
        calls.append(retry_strict)
        return {"estimated_purchase_price": "a lot"}, True, "{}"

    monkeypatch.setattr(calculator, "call_gemini", broken_call)
    estimate = calculator.estimate_machine_tco(MACHINE, [])

    assert calls == [False, True]  # one strict retry before falling back
    assert estimate["source"] == "heuristic"
    assert estimate["confidence"] == "low"


def test_full_calculation_completes_when_gemini_is_down(calculator, monkeypatch):
    monkeypatch.setattr(calculator, "call_gemini", lambda prompt, retry_strict=False: ({}, False, ""))

    result = calculator.calculate_tco(TCOCalculationInput(**PROJECT))

    assert result.company_name == "Plastiques du Sahel"
    assert result.machine_tco[0].estimation_source == "heuristic"
    assert [m.estimation_source for m in result.raw_materials_tco] == ["heuristic"]
    assert len(result.annual_tco) == 5
    assert result.annual_tco[1].total_tco == pytest.approx(result.annual_tco[0].total_tco * 1.07, rel=1e-3)
    assert result.tco_per_unit_revenue == pytest.approx(result.total_tco / 400_000_000, abs=1e-4)


def test_missing_revenue_is_an_error_not_a_guess(calculator, monkeypatch):
    monkeypatch.setattr(calculator, "call_gemini", lambda prompt, retry_strict=False: ({}, False, ""))
    project = dict(PROJECT, estimated_revenue=None)

    with pytest.raises(ValueError, match="estimated_revenue"):
        calculator.calculate_tco(TCOCalculationInput(**project))


def test_call_gemini_strips_fences_from_the_client_reply(calculator, monkeypatch):
    reply = SimpleNamespace(text="```json\n" + json.dumps(MACHINE_ANSWER) + "\n```")
    sent = {}

    def fake_generate_content(model, contents, config):
        sent["model"] = model
        sent["contents"] = contents
        return reply

    monkeypatch.setattr(calculator, "client", SimpleNamespace(models=SimpleNamespace(generate_content=fake_generate_content)))

    parsed, ok, raw = calculator.call_gemini("estimate", retry_strict=True)

    assert ok and parsed == MACHINE_ANSWER
    assert sent["model"] == calculator.model_name
    assert "RETURN VALID JSON ONLY" in sent["contents"]
