"""
Module 5 negotiation, verified offline.

Offer scoring and counter-offer pricing are local maths. Email wording comes
from vertex_utils.generate_message (Gemini), sending goes through smtplib, and
the voice channel runs in the browser through Vapi. Gemini and SMTP are faked
here; Vapi is not exercised.
"""

import pytest

import vertex_utils
from utils import email_service
from utils.module_5.core import NegotiationConfig, compute_counter_offer, evaluate_offer, run_text_negotiation

REQUIREMENTS = {
    "target_price": 450000,
    "max_price": 550000,
    "currency": "EUR",
    "preferred_incoterms": ["DDP", "CIF"],
    "max_lead_time_days": 90,
    "min_warranty_months": 24,
    "max_deposit_pct": 30,
}
OFFER = {
    "price": "520 000 EUR",
    "incoterm": "EXW",
    "payment_terms": "50% deposit",
    "lead_time_days": 120,
    "warranty_months": 12,
}


def test_weak_offer_is_scored_and_issues_listed():
    evaluation = evaluate_offer(OFFER, REQUIREMENTS, NegotiationConfig())

    assert evaluation["price"] == 520000
    assert evaluation["currency"] == "EUR"
    assert set(evaluation["issues"]) == {
        "Price above target", "Incoterm not preferred", "Lead time above target", "Warranty below target",
    }
    assert evaluation["recommendation"] in {"counter", "counter_aggressively"}
    assert 0 <= evaluation["scores"]["overall"] <= 1


def test_offer_meeting_every_requirement_is_accepted():
    good = {"price": 440000, "incoterm": "DDP", "payment_terms": "30% deposit", "lead_time_days": 60, "warranty_months": 36}

    assert evaluate_offer(good, REQUIREMENTS, NegotiationConfig())["recommendation"] == "accept"


def test_counter_offer_anchors_below_target_and_concedes_each_round():
    cfg = NegotiationConfig(anchor_discount=0.08, concession_rate=0.03)

    first = compute_counter_offer(OFFER, REQUIREMENTS, {"round": 1}, cfg)
    third = compute_counter_offer(OFFER, REQUIREMENTS, {"round": 3}, cfg)

    assert first["price"] == pytest.approx(450000 * 0.92)
    assert third["price"] == pytest.approx(450000 * 0.92 + 2 * 0.03 * 450000)
    assert first["incoterm"] == "DDP"
    assert first["lead_time_days"] == 90 and first["warranty_months"] == 24


def test_counter_offer_never_exceeds_the_suppliers_price():
    cheap = dict(OFFER, price=400000)

    counter = compute_counter_offer(cheap, REQUIREMENTS, {"round": 10}, NegotiationConfig())

    assert counter["price"] == 400000


def test_email_draft_is_built_from_the_offer_and_counter(monkeypatch):
    prompts = []

    def fake_generate_message(prompt, system_instruction=None, temperature=1.0, top_p=0.95, **kwargs):
        prompts.append(prompt)
        return "  Dear Engel team, we propose 414000 EUR DDP.  "

    monkeypatch.setattr(vertex_utils, "generate_message", fake_generate_message)

    result = run_text_negotiation({
        "buyer_requirements": REQUIREMENTS,
        "supplier_offer": OFFER,
        "email_context": {"buyer_company": "RIBIF", "supplier_company": "Engel", "product_name": "Injection press"},
    })

    assert result["email_draft"] == "Dear Engel team, we propose 414000 EUR DDP."
    assert '"incoterm": "EXW"' in prompts[0]
    assert "Supplier company: Engel" in prompts[0]
    assert result["negotiation_state"]["round"] == 2


def test_template_email_when_gemini_is_unavailable(monkeypatch):
    def failing_generate_message(**kwargs):
        raise RuntimeError("quota exhausted")

    monkeypatch.setattr(vertex_utils, "generate_message", failing_generate_message)

    result = run_text_negotiation({"buyer_requirements": REQUIREMENTS, "supplier_offer": OFFER})

    assert str(result["counter_offer"]["price"]) in result["email_draft"]
    assert "DDP" in result["email_draft"]


def test_text_route_returns_and_persists_the_round(monkeypatch, tmp_path):
    import app as backend_app
    import routes.module_5 as route

    monkeypatch.setattr(vertex_utils, "generate_message", lambda **kwargs: "Counter proposal attached.")
    monkeypatch.setitem(route.OUTPUT_DIRS, "module5", tmp_path)

    response = backend_app.app.test_client().post(
        "/api/module5/text/negotiation",
        json={"buyer_requirements": REQUIREMENTS, "supplier_offer": OFFER, "project_id": "p1"},
    )

    assert response.status_code == 200
    assert response.get_json()["email_draft"] == "Counter proposal attached."
    assert len(list(tmp_path.glob("module_5_text_*.json"))) == 1


class FakeSMTP:
    instances = []

    def __init__(self, host, port, timeout=None, context=None):
        self.host, self.port = host, port
        self.calls = []
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self, context=None):
        self.calls.append("starttls")

    def login(self, user, password):
        self.calls.append(("login", user))

    def send_message(self, msg, from_addr=None, to_addrs=None):
        self.calls.append(("send", msg["Subject"], tuple(to_addrs)))


def test_send_email_builds_the_message_for_smtp(monkeypatch):
    FakeSMTP.instances = []
    monkeypatch.setattr(email_service.smtplib, "SMTP", FakeSMTP)

    result = email_service.send_email({
        "smtp_host": "smtp.test", "smtp_username": "buyer@ribif.test", "smtp_password": "pw",
        "to": "sales@engel.test", "cc": ["ops@ribif.test"], "subject": "RFQ", "text": "Hello",
    })

    server = FakeSMTP.instances[0]
    assert (server.host, server.port) == ("smtp.test", 587)
    assert server.calls == ["starttls", ("login", "buyer@ribif.test"), ("send", "RFQ", ("sales@engel.test", "ops@ribif.test"))]
    assert result["status"] == "sent"


def test_explicit_false_disables_starttls(monkeypatch):
    FakeSMTP.instances = []
    monkeypatch.setattr(email_service.smtplib, "SMTP", FakeSMTP)

    email_service.send_email({"smtp_host": "smtp.test", "smtp_use_tls": False, "to": "a@b.test", "text": "x"})

    assert "starttls" not in FakeSMTP.instances[0].calls
