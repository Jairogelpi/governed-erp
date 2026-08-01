"""Spec 92 Workstream C -- Outcome & Realized ROI.

Builds a full recommendation -> approval -> action-draft -> converted-run
chain (reusing Phase 16.7's helpers), then drives OutcomeService through
the public API with fixture-sourced follow-up observations.
"""

from __future__ import annotations

from uuid import uuid4

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from apps.api.main import app
from sqlalchemy import update

from erpguard.config import settings
from erpguard.db.model_packages.decision_intelligence import MarginAnalysis
from erpguard.db.session import SessionLocal, init_db

from test_phase14_skill_compiler import _identity
from test_phase16_6_opportunity_roi_engine import _seed_margin_analysis, _segment
from test_phase16_7_pricing_scenario_draft import (
    _VALID_PRICING_INPUTS,
    _active_odoo_skill_package,
    _odoo_connection,
)
from test_phase16_7_pricing_scenario_draft import _FakeWriteTransport
from erpguard.application.connectors.service import ConnectorApplicationService


def _setup(monkeypatch) -> tuple[TestClient, dict, str]:
    monkeypatch.setattr(settings, "auth_secret", "skill-auth")
    monkeypatch.setattr(settings, "local_secret_key", Fernet.generate_key().decode())
    monkeypatch.setattr(settings, "allow_pricing_scenario_draft", True)
    init_db()
    tenant_id = f"outcome-tenant-{uuid4().hex}"
    headers = _identity(tenant_id)
    return TestClient(app), headers, tenant_id


def _seed_opportunity(tenant_id: str) -> tuple[str, str]:
    """Returns (opportunity_id, analysis_id)."""

    product_drivers = {
        "current": [_segment("p1", "1000", "700", "30")],
        "comparison": [_segment("p1", "1000", "500", "50")],
    }
    analysis_id = _seed_margin_analysis(
        tenant_id, status="ready", product_drivers=product_drivers, customer_drivers={"current": [], "comparison": []}
    )
    from erpguard.application.opportunity.service import OpportunityEngineService

    import json

    baseline_values = {
        "net_revenue": {"value": "1000"},
        "gross_margin": {"value": "300"},
        "gross_margin_percent": {"value": "30.0"},
    }
    db = SessionLocal()
    try:
        db.execute(
            update(MarginAnalysis)
            .where(MarginAnalysis.id == analysis_id)
            .values(current_metrics_json=json.dumps({"values": baseline_values}))
        )
        db.commit()
        rows = OpportunityEngineService(db).generate(tenant_id=tenant_id, margin_analysis_id=analysis_id, created_by="test")
        return rows[0].id, analysis_id
    finally:
        db.close()


def _converted_recommendation(client: TestClient, headers: dict, monkeypatch, tenant_id: str) -> dict:
    """Full A-workstream chain, returns the approved+converted recommendation dict."""

    process_key = _active_odoo_skill_package(client, headers, monkeypatch, tenant_id)
    connection_id = _odoo_connection(client, headers)
    opportunity_id, analysis_id = _seed_opportunity(tenant_id)

    create_resp = client.post(
        f"/v1/opportunities/{opportunity_id}/recommendations",
        headers=headers,
        json={
            "recommendation_type": "customer_discount_review",
            "title": "Discount scenario",
            "selected_action_template": "customer_discount_quote_scenario_v1",
        },
    )
    recommendation = create_resp.json()
    assert client.post(f"/v1/recommendations/{recommendation['id']}/submit", headers=headers).status_code == 200

    approver_headers = _identity(tenant_id)
    approval_id = client.post(
        "/v1/approvals", headers=approver_headers, json={"scope": recommendation["approval_scope"]}
    ).json()["id"]
    approve_resp = client.post(
        f"/v1/recommendations/{recommendation['id']}/approve", headers=approver_headers, json={"approval_id": approval_id}
    )
    assert approve_resp.status_code == 200, approve_resp.text
    recommendation = approve_resp.json()

    draft_resp = client.post(
        f"/v1/recommendations/{recommendation['id']}/action-drafts",
        headers=headers,
        json={"process_key": process_key, "connection_id": connection_id, "pricing_inputs": _VALID_PRICING_INPUTS},
    )
    assert draft_resp.status_code == 201, draft_resp.text
    draft = draft_resp.json()
    assert client.post(f"/v1/action-drafts/{draft['id']}/validate", headers=headers).status_code == 200

    transport = _FakeWriteTransport()
    monkeypatch.setattr(
        ConnectorApplicationService, "_odoo_write_transport_factory", lambda self, connection: (lambda context: transport)
    )
    plan_resp = client.post(
        f"/v1/action-drafts/{draft['id']}/plan-run", headers=headers, json={"idempotency_key": f"idem-{uuid4().hex}"}
    )
    assert plan_resp.status_code == 200, plan_resp.text
    run_id = plan_resp.json()["converted_run_id"]

    approval_id2 = client.post("/v1/approvals", headers=headers, json={"scope": "run:execute"}).json()["id"]
    assert client.post(
        f"/v1/runs/{run_id}/approve", headers=headers, json={"approval_ids": [approval_id2], "ttl_seconds": 900}
    ).status_code == 200
    execute_resp = client.post(f"/v1/runs/{run_id}/execute", headers=headers)
    assert execute_resp.status_code == 200, execute_resp.text

    final_resp = client.get(f"/v1/recommendations/{recommendation['id']}", headers=headers)
    recommendation = final_resp.json()
    assert recommendation["status"] == "converted", recommendation
    return {"recommendation": recommendation, "run_id": run_id}


def _valid_observed(**overrides) -> dict:
    payload = {
        "net_revenue": "1200.00",
        "gross_margin": "260.00",
        "gross_margin_percent": "21.6",
        "currency": "EUR",
        "metric_definition_version": "margin-truth/1.0.0",
        "cost_coverage_rate": 0.99,
    }
    payload.update(overrides)
    return payload


def _plan_and_approve(client, headers, tenant_id, recommendation_id, **overrides) -> dict:
    payload = {
        "execution_run_ids": [],
        "comparison_method": "fixture_replay",
        "observation_start": "2026-02-01",
        "observation_end": "2026-02-28",
        **overrides,
    }
    create_resp = client.post(
        f"/v1/recommendations/{recommendation_id}/measurement-plans", headers=headers, json=payload
    )
    assert create_resp.status_code == 201, create_resp.text
    plan = create_resp.json()

    approver_headers = _identity(tenant_id)
    approval_id = client.post(
        "/v1/approvals", headers=approver_headers, json={"scope": plan["approval_scope"]}
    ).json()["id"]
    approve_resp = client.post(
        f"/v1/measurement-plans/{plan['id']}/approve", headers=approver_headers, json={"approval_id": approval_id}
    )
    assert approve_resp.status_code == 200, approve_resp.text
    start_resp = client.post(f"/v1/measurement-plans/{plan['id']}/start", headers=headers)
    assert start_resp.status_code == 200, start_resp.text
    return start_resp.json()


def test_metric_version_mismatch_blocks(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    result = _converted_recommendation(client, headers, monkeypatch, tenant_id)
    recommendation_id = result["recommendation"]["id"]
    plan = _plan_and_approve(client, headers, tenant_id, recommendation_id)

    capture_resp = client.post(
        f"/v1/measurement-plans/{plan['id']}/capture-followup", headers=headers,
        json={"observed": _valid_observed(metric_definition_version="margin-truth/2.0.0")},
    )
    assert capture_resp.status_code == 200, capture_resp.text

    evaluate_resp = client.post(f"/v1/measurement-plans/{plan['id']}/evaluate", headers=headers)
    assert evaluate_resp.status_code == 200, evaluate_resp.text
    report = evaluate_resp.json()
    assert report["result_classification"] == "blocked"
    assert "metric_definition_version_mismatch" in report["limitations"]
    assert report["realized_value"] is None


def test_mixed_currency_blocks(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    result = _converted_recommendation(client, headers, monkeypatch, tenant_id)
    recommendation_id = result["recommendation"]["id"]
    plan = _plan_and_approve(client, headers, tenant_id, recommendation_id)

    client.post(
        f"/v1/measurement-plans/{plan['id']}/capture-followup", headers=headers,
        json={"observed": _valid_observed(currency="USD")},
    )
    evaluate_resp = client.post(f"/v1/measurement-plans/{plan['id']}/evaluate", headers=headers)
    report = evaluate_resp.json()
    assert report["result_classification"] == "blocked"
    assert "currency_not_comparable" in report["limitations"]


def test_low_coverage_produces_inconclusive(monkeypatch):
    """0.82 clears the plan's minimum_data_coverage gate (default 0.8, so the
    comparison itself is not blocked) but sits below the 0.85 confidence
    threshold interpretation.py uses to downgrade to inconclusive."""

    client, headers, tenant_id = _setup(monkeypatch)
    result = _converted_recommendation(client, headers, monkeypatch, tenant_id)
    recommendation_id = result["recommendation"]["id"]
    plan = _plan_and_approve(client, headers, tenant_id, recommendation_id)

    client.post(
        f"/v1/measurement-plans/{plan['id']}/capture-followup", headers=headers,
        json={"observed": _valid_observed(cost_coverage_rate=0.82)},
    )
    evaluate_resp = client.post(f"/v1/measurement-plans/{plan['id']}/evaluate", headers=headers)
    report = evaluate_resp.json()
    assert report["result_classification"] == "inconclusive"


def test_same_inputs_produce_same_report_content_hash(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    result = _converted_recommendation(client, headers, monkeypatch, tenant_id)
    recommendation_id = result["recommendation"]["id"]

    hashes = []
    for _ in range(2):
        plan = _plan_and_approve(client, headers, tenant_id, recommendation_id)
        client.post(
            f"/v1/measurement-plans/{plan['id']}/capture-followup", headers=headers,
            json={"observed": _valid_observed()},
        )
        evaluate_resp = client.post(f"/v1/measurement-plans/{plan['id']}/evaluate", headers=headers)
        hashes.append(evaluate_resp.json())

    # Same evidence inputs (baseline + same observed metrics) -> same math,
    # different plan/report ids (fresh plan each time is intentional per design).
    assert hashes[0]["realized_value"] == hashes[1]["realized_value"]
    assert hashes[0]["result_classification"] == hashes[1]["result_classification"]


def test_positive_result_classified_correctly(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    result = _converted_recommendation(client, headers, monkeypatch, tenant_id)
    recommendation_id = result["recommendation"]["id"]
    plan = _plan_and_approve(client, headers, tenant_id, recommendation_id)

    # Baseline gross_margin = 1000-700 = 300 (from p1 segment: net_revenue 1000, cost 700).
    client.post(
        f"/v1/measurement-plans/{plan['id']}/capture-followup", headers=headers,
        json={"observed": _valid_observed(gross_margin="500.00")},
    )
    evaluate_resp = client.post(f"/v1/measurement-plans/{plan['id']}/evaluate", headers=headers)
    report = evaluate_resp.json()
    assert report["result_classification"] == "positive_observed_result"
    assert report["observed_margin_change"] == "200.00"
    assert report["realized_value"] == "200.00"


def test_missing_implementation_cost_leaves_net_roi_null(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    result = _converted_recommendation(client, headers, monkeypatch, tenant_id)
    recommendation_id = result["recommendation"]["id"]
    plan = _plan_and_approve(client, headers, tenant_id, recommendation_id)
    assert plan["implementation_cost"] is None

    client.post(
        f"/v1/measurement-plans/{plan['id']}/capture-followup", headers=headers,
        json={"observed": _valid_observed(gross_margin="500.00")},
    )
    report = client.post(f"/v1/measurement-plans/{plan['id']}/evaluate", headers=headers).json()
    assert report["implementation_cost"] is None
    assert report["net_realized_value"] is None
    assert "no_implementation_cost_evidenced_net_roi_not_computed" in report["limitations"]


def test_supplied_implementation_cost_computes_net_realized_value(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    result = _converted_recommendation(client, headers, monkeypatch, tenant_id)
    recommendation_id = result["recommendation"]["id"]
    plan = _plan_and_approve(client, headers, tenant_id, recommendation_id, implementation_cost="50.00")
    assert plan["implementation_cost"] == "50.00"

    client.post(
        f"/v1/measurement-plans/{plan['id']}/capture-followup", headers=headers,
        json={"observed": _valid_observed(gross_margin="500.00")},
    )
    report = client.post(f"/v1/measurement-plans/{plan['id']}/evaluate", headers=headers).json()
    assert report["realized_value"] == "200.00"
    assert report["implementation_cost"] == "50.00"
    assert report["net_realized_value"] == "150.00"
    assert "no_implementation_cost_evidenced_net_roi_not_computed" not in report["limitations"]
    # No fixed hourly rate or arbitrary cost assumption -- the number is exactly what was supplied.
    assert "proved" not in " ".join(report["limitations"]).lower()
    assert "caused" not in " ".join(report["limitations"]).lower()


def test_negative_implementation_cost_rejected(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    result = _converted_recommendation(client, headers, monkeypatch, tenant_id)
    recommendation_id = result["recommendation"]["id"]

    create_resp = client.post(
        f"/v1/recommendations/{recommendation_id}/measurement-plans", headers=headers,
        json={
            "execution_run_ids": [], "comparison_method": "fixture_replay",
            "observation_start": "2026-02-01", "observation_end": "2026-02-28",
            "implementation_cost": "-10.00",
        },
    )
    assert create_resp.status_code == 422, create_resp.text


def test_negative_result_classified_correctly(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    result = _converted_recommendation(client, headers, monkeypatch, tenant_id)
    recommendation_id = result["recommendation"]["id"]
    plan = _plan_and_approve(client, headers, tenant_id, recommendation_id)

    client.post(
        f"/v1/measurement-plans/{plan['id']}/capture-followup", headers=headers,
        json={"observed": _valid_observed(gross_margin="100.00")},
    )
    evaluate_resp = client.post(f"/v1/measurement-plans/{plan['id']}/evaluate", headers=headers)
    report = evaluate_resp.json()
    assert report["result_classification"] == "negative_observed_result"
    assert report["observed_margin_change"] == "-200.00"


def test_fixture_outcome_labelled_source(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    result = _converted_recommendation(client, headers, monkeypatch, tenant_id)
    recommendation_id = result["recommendation"]["id"]
    plan = _plan_and_approve(client, headers, tenant_id, recommendation_id)

    capture_resp = client.post(
        f"/v1/measurement-plans/{plan['id']}/capture-followup", headers=headers,
        json={"observed": _valid_observed()},
    )
    assert capture_resp.json()["source"] == "fixture"


def test_no_causal_language_in_report(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    result = _converted_recommendation(client, headers, monkeypatch, tenant_id)
    recommendation_id = result["recommendation"]["id"]
    plan = _plan_and_approve(client, headers, tenant_id, recommendation_id)

    client.post(
        f"/v1/measurement-plans/{plan['id']}/capture-followup", headers=headers,
        json={"observed": _valid_observed(gross_margin="500.00")},
    )
    evaluate_resp = client.post(f"/v1/measurement-plans/{plan['id']}/evaluate", headers=headers)
    body_text = str(evaluate_resp.json()).lower()
    for forbidden in ("proved", "caused", "guaranteed"):
        assert forbidden not in body_text
