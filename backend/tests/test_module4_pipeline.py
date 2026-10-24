"""
Module 4 bounded sourcing pipeline, verified up to the service boundary.

Supplier discovery goes through utils.web_search.aggregator.search_machine_suppliers
(Serper, Bing, DuckDuckGo and B2B marketplace scrapers) and the final synthesis
through generate_message (Gemini). Both are faked; classification, budgeting,
dedup, filtering and the AI fallback run for real.
"""

import json
import re

import pytest

from utils.module_4 import core_v2
from utils.web_search import aggregator
from utils.web_search.base import SupplierResult

UNKNOWN_MACHINE = {"nom_machine": "Ligne de pultrusion composite sur mesure", "type": "Pultrusion", "quantite_necessaire": 1}
KNOWN_MACHINE = {"nom_machine": "Machine de thermoformage grand format", "type": "Thermoformage", "quantite_necessaire": 1}


def _results():
    return [
        SupplierResult(supplier_name="Pultrex Ltd", website="https://www.pultrex.com",
                       source_url="https://www.pultrex.com/pultrusion", region="Finland",
                       notes="Pultrusion machines manufacturer (OEM)", source="serper", relevance_score=0.9),
        SupplierResult(supplier_name="Pultrex Ltd", website="https://www.pultrex.com",
                       source_url="https://www.pultrex.com/contact", region="Finland",
                       notes="Pultrusion machines manufacturer (OEM)", source="bing", relevance_score=0.8),
    ]


@pytest.fixture
def services(monkeypatch, tmp_path):
    searches, prompts = [], []

    def fake_search(machine_name, machine_type="", region="", max_results_per_source=5, max_total_results=15):
        searches.append(machine_name)
        return _results()

    def fake_generate_message(prompt, system_instruction=None, temperature=1.0, **kwargs):
        prompts.append(prompt)
        canonical = re.search(r'"canonical_name": "([^"]+)"', prompt).group(1)
        return json.dumps({"canonical_name": canonical, "machine_class": "core_variable", "confidence": "medium"})

    monkeypatch.setattr(core_v2, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(core_v2, "USE_CACHE", False)
    monkeypatch.setattr(core_v2, "WEB_SEARCH_ENABLED", True)
    monkeypatch.setattr(aggregator, "search_machine_suppliers", fake_search)
    monkeypatch.setattr(core_v2, "generate_message", fake_generate_message)
    return searches, prompts


def test_each_pass1_query_is_a_distinct_search(services):
    searches, _ = services

    core_v2.process_module_4_bounded([UNKNOWN_MACHINE], max_workers=1)

    assert len(searches) >= 2
    assert len(set(searches)) == len(searches)
    assert all("pultrusion" in q.lower() for q in searches)


def test_web_suppliers_are_deduped_and_budget_is_respected(services):
    _, prompts = services

    result = core_v2.process_module_4_bounded([UNKNOWN_MACHINE], max_workers=1)

    meta = result["ribif_metadata"]
    assert meta["hard_budget_compliant"] is True
    assert meta["hard_budget_consumed"] <= meta["hard_budget_max"]
    assert len(prompts) == 1  # one synthesis call per machine

    machine = result["machines_enriched"][0]
    names = [s["supplier_name"] for s in machine["suppliers"]]
    assert names == ["Pultrex Ltd"]
    assert not machine["suppliers"][0].get("is_ai_fallback")
    assert "no_public_suppliers_subtext" not in machine


def test_known_machine_uses_industry_knowledge_without_web(services):
    searches, _ = services

    result = core_v2.process_module_4_bounded([KNOWN_MACHINE], max_workers=1)

    assert searches == []
    machine = result["machines_enriched"][0]
    assert machine["machine_input"]["canonical_name"] == "Thermoforming Machine"
    assert machine["suppliers"]
    assert all(s["is_ai_fallback"] for s in machine["suppliers"])
    assert "No public suppliers" in machine["no_public_suppliers_subtext"]


def test_search_outage_falls_back_to_ai_suppliers(services, monkeypatch):
    def failing_search(**kwargs):
        raise ConnectionError("serper down")

    monkeypatch.setattr(aggregator, "search_machine_suppliers", failing_search)

    result = core_v2.process_module_4_bounded([UNKNOWN_MACHINE], max_workers=1)

    machine = result["machines_enriched"][0]
    assert machine["suppliers"], "every machine keeps at least one supplier suggestion"
    assert all(s["is_ai_fallback"] for s in machine["suppliers"])
    assert result["ribif_metadata"]["supplier_outcomes"]["all_machines_have_outcome"] is True


def test_web_search_disabled_makes_no_calls(services, monkeypatch):
    searches, _ = services
    monkeypatch.setattr(core_v2, "WEB_SEARCH_ENABLED", False)

    result = core_v2.process_module_4_bounded([UNKNOWN_MACHINE], max_workers=1)

    assert searches == []
    assert result["machines_enriched"][0]["suppliers"]
