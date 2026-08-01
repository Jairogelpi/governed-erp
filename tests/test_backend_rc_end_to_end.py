"""Spec 92 Sec 19 -- Backend RC end-to-end acceptance scenario.

Drives the full lifecycle through the public API in one flow: snapshot ->
margin analysis -> opportunity -> recommendation -> approval -> action draft
-> canary policy -> deterministic routing -> signed permit -> execution
against an injected staging transport -> draft-only postconditions ->
measurement plan -> fixture follow-up -> realized outcome report -> sealed,
verified evidence bundle.

Unlike `test_phase16_7_pricing_scenario_draft.py`'s single-package helper,
this scenario needs BOTH a stable and a canary package sharing one
process_key so the run genuinely gets canary-routed (Sec 19: "deterministically
route a bounded case") -- the two-package trick is the same one
`test_phase19_2_canary_safety_gates.py` uses, applied to the Odoo pricing
scenario capability instead of the fake connector's read capability.
"""

from __future__ import annotations

from uuid import uuid4

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import update

from apps.api.main import app
from erpguard.application.canary.service import CanaryRouterService
from erpguard.application.connectors.service import ConnectorApplicationService
from erpguard.config import settings
from erpguard.db.model_packages.execution import ExecutionRun
from erpguard.db.model_packages.skill_package import SkillPackage
from erpguard.db.session import SessionLocal, init_db
from erpguard.domain.shadow.service import ShadowService

from test_phase14_skill_compiler import _build_submitted_candidate_with_proof, _identity
from test_phase16_7_pricing_scenario_draft import (
    _VALID_PRICING_INPUTS,
    _FakeWriteTransport,
    _approved_recommendation,
    _odoo_connection,
)
from test_phase19_skill_deployment_lifecycle import _shadow_deployment_row
from test_phase20_1_realized_outcomes import _seed_opportunity, _valid_observed

_CAPABILITY = "sales.quote.create_pricing_scenario_draft"


def _setup(monkeypatch) -> tuple[TestClient, dict, str]:
    monkeypatch.setattr(settings, "auth_secret", "skill-auth")
    monkeypatch.setattr(settings, "local_secret_key", Fernet.generate_key().decode())
    monkeypatch.setattr(settings, "allow_pricing_scenario_draft", True)
    init_db()
    tenant_id = f"backend-rc-tenant-{uuid4().hex}"
    headers = _identity(tenant_id)
    return TestClient(app), headers, tenant_id


def _compile_and_approve(client, headers, tenant_id) -> tuple[str, str]:
    candidate_id, process_key, version = _build_submitted_candidate_with_proof(client, headers, tenant_id)
    compile_resp = client.post(
        f"/v1/process-candidates/{candidate_id}/compile", headers=headers,
        json={"connector_id": "odoo", "workflow_steps": [{"step_name": "create_draft", "capability": _CAPABILITY}]},
    )
    assert compile_resp.status_code == 201, compile_resp.text
    skill_id = compile_resp.json()["id"]
    assert client.post(f"/v1/skills/{skill_id}/versions/{version}/approve", headers=headers).status_code == 200
    return skill_id, process_key


def _stable_and_canary_odoo_packages(client, headers, monkeypatch, tenant_id) -> tuple[str, str, str]:
    """Returns (process_key, stable_skill_id, canary_skill_id), both compiled
    for the pricing-scenario capability against the Odoo connector.

    Both candidates are built (and their OCEL events imported) before any
    `ShadowDeployment` fixture exists for this tenant -- the operational
    shadow feed reprocesses every existing `ShadowDeployment` on each new
    OCEL import, and these test-only stub deployments aren't meant to
    receive a second candidate's events (same ordering
    `test_two_active_policies_for_same_process_rejected` relies on)."""

    monkeypatch.setattr(
        ShadowService, "dashboard", lambda self, *, tenant_id, deployment_id: {"recommendation": "eligible_for_canary"}
    )
    stable_id, process_key = _compile_and_approve(client, headers, tenant_id)
    canary_id, _own_process_key = _compile_and_approve(client, headers, tenant_id)
    db = SessionLocal()
    try:
        db.execute(update(SkillPackage).where(SkillPackage.id == canary_id).values(process_key=process_key))
        db.commit()
    finally:
        db.close()

    d1 = _shadow_deployment_row(tenant_id, process_key)
    assert client.post(
        f"/v1/skills/{stable_id}/promote-canary", headers=headers, json={"shadow_deployment_id": d1, "reason": "t"}
    ).status_code == 200
    assert client.post(
        f"/v1/skills/{stable_id}/promote-active", headers=headers, json={"reason": "t"}
    ).status_code == 200

    d2 = _shadow_deployment_row(tenant_id, process_key)
    assert client.post(
        f"/v1/skills/{canary_id}/promote-canary", headers=headers, json={"shadow_deployment_id": d2, "reason": "t"}
    ).status_code == 200

    return process_key, stable_id, canary_id


def _active_canary_policy(client, headers, tenant_id, *, process_key, stable_id, canary_id) -> dict:
    shadow_deployment_id = _shadow_deployment_row(tenant_id, process_key)
    payload = {
        "process_key": process_key,
        "stable_skill_package_id": stable_id,
        "canary_skill_package_id": canary_id,
        "shadow_deployment_id": shadow_deployment_id,
        "percentage_basis_points": 10000,  # force canary every time -- deterministic, not probabilistic
        "maximum_cases": 100,
        "maximum_total_amount": 100000,
        "allowed_capabilities": [_CAPABILITY],
        "maximum_amount": 100000,
    }
    create_resp = client.post("/v1/canary-policies", headers=headers, json=payload)
    assert create_resp.status_code == 201, create_resp.text
    policy = create_resp.json()

    approver_headers = _identity(tenant_id)
    approval_id = client.post(
        "/v1/approvals", headers=approver_headers, json={"scope": policy["approval_scope"]}
    ).json()["id"]
    assert client.post(
        f"/v1/canary-policies/{policy['id']}/approve", headers=approver_headers, json={"approval_id": approval_id}
    ).status_code == 200
    activate_resp = client.post(f"/v1/canary-policies/{policy['id']}/activate", headers=headers)
    assert activate_resp.status_code == 200, activate_resp.text
    return activate_resp.json()


def test_backend_rc_end_to_end(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)

    # 1-4: analytical snapshot -> margin analysis -> opportunity -> select one
    opportunity_id, _analysis_id = _seed_opportunity(tenant_id)

    # 5-7: recommendation -> submit -> independently approve
    recommendation = _approved_recommendation(client, headers, tenant_id, opportunity_id)
    assert recommendation["margin_opportunity_id"] == opportunity_id

    # 8-9: pricing scenario action draft -> validate
    process_key, stable_id, canary_id = _stable_and_canary_odoo_packages(client, headers, monkeypatch, tenant_id)
    connection_id = _odoo_connection(client, headers)
    draft_resp = client.post(
        f"/v1/recommendations/{recommendation['id']}/action-drafts", headers=headers,
        json={"process_key": process_key, "connection_id": connection_id, "pricing_inputs": _VALID_PRICING_INPUTS},
    )
    assert draft_resp.status_code == 201, draft_resp.text
    draft = draft_resp.json()
    assert draft["recommendation_id"] == recommendation["id"]
    assert client.post(f"/v1/action-drafts/{draft['id']}/validate", headers=headers).status_code == 200

    # 10-11: canary policy -> approve and activate
    policy = _active_canary_policy(client, headers, tenant_id, process_key=process_key, stable_id=stable_id, canary_id=canary_id)

    # Sec 19 "same canary context selects same package": the deterministic
    # bucket/lane math is pure and reproducible for identical inputs.
    business_object_key = f"rec-{recommendation['id']}"
    db = SessionLocal()
    try:
        router_service = CanaryRouterService(db)
        first_route = router_service.route(
            tenant_id=tenant_id, process_key=process_key, business_object_key=business_object_key,
            capability=_CAPABILITY, execution_run_id=None,
        )
        second_route = router_service.route(
            tenant_id=tenant_id, process_key=process_key, business_object_key=business_object_key,
            capability=_CAPABILITY, execution_run_id=None,
        )
        assert first_route.selected_skill_package_id == second_route.selected_skill_package_id == canary_id
        assert first_route.bucket == second_route.bucket
    finally:
        db.close()

    # 12-14: deterministically route this bounded case -> signed permit -> execute
    transport = _FakeWriteTransport()
    monkeypatch.setattr(
        ConnectorApplicationService, "_odoo_write_transport_factory", lambda self, connection: (lambda context: transport)
    )
    plan_resp = client.post(
        f"/v1/action-drafts/{draft['id']}/plan-run", headers=headers,
        json={
            "idempotency_key": f"idem-{uuid4().hex}",
            "routing_context": {"business_object_key": business_object_key, "capability": _CAPABILITY},
        },
    )
    assert plan_resp.status_code == 200, plan_resp.text
    run_id = plan_resp.json()["converted_run_id"]
    assert run_id is not None

    db = SessionLocal()
    try:
        run = db.query(ExecutionRun).filter_by(id=run_id).one()
        assert run.skill_package_id == canary_id, "exact selected package must be recorded"
        assert run.deployment_lane == "canary"
    finally:
        db.close()

    approval_id = client.post("/v1/approvals", headers=headers, json={"scope": "run:execute"}).json()["id"]
    assert client.post(
        f"/v1/runs/{run_id}/approve", headers=headers, json={"approval_ids": [approval_id], "ttl_seconds": 900}
    ).status_code == 200
    execute_resp = client.post(f"/v1/runs/{run_id}/execute", headers=headers)
    assert execute_resp.status_code == 200, execute_resp.text
    executed = execute_resp.json()
    assert executed["status"] == "succeeded"

    # Sec 9.8: the canary dashboard's estimated_opportunity_value is no
    # longer a hardcoded null -- it traces this run back through its
    # action draft/recommendation to the MarginOpportunity that motivated
    # it (impact_base == 200 for the fixed _segment(...) fixture below).
    dashboard = client.get(f"/v1/canary-policies/{policy['id']}/dashboard", headers=headers).json()
    from decimal import Decimal

    assert Decimal(dashboard["estimated_opportunity_value"]) == Decimal("200"), dashboard

    # 15: verify draft-only postconditions -- no confirmation/invoice/delivery/purchase/manufacturing.
    evidence_resp = client.get(f"/v1/runs/{run_id}/evidence", headers=headers)
    assert evidence_resp.status_code == 200, evidence_resp.text
    evidence = evidence_resp.json()
    postcondition_summary = evidence["verification"]["postcondition"]["summary"]
    assert postcondition_summary == "pricing_scenario_draft_postconditions_verified"
    snapshot = evidence["verification"]["postcondition"]["evidence"]["snapshot"]
    assert snapshot["state"] == "draft"
    assert snapshot["invoice_count"] == 0
    assert snapshot["picking_count"] == 0
    assert snapshot["purchase_order_count"] == 0
    assert snapshot["manufacturing_order_count"] == 0
    assert transport.create_calls == 1

    # Structural: no generic model/method/execute_raw entry point exists.
    from erpguard.connectors.odoo.plugin import OdooConnectorPlugin

    plugin = OdooConnectorPlugin()
    for forbidden in ("execute_raw", "call_method", "model", "method"):
        assert not hasattr(plugin, forbidden)

    # 16-18: measurement plan -> fixture follow-up -> realized outcome report
    plan_payload = {
        "execution_run_ids": [run_id],
        "comparison_method": "fixture_replay",
        "observation_start": "2026-02-01",
        "observation_end": "2026-02-28",
    }
    plan_create = client.post(
        f"/v1/recommendations/{recommendation['id']}/measurement-plans", headers=headers, json=plan_payload
    )
    assert plan_create.status_code == 201, plan_create.text
    plan = plan_create.json()
    approver_headers = _identity(tenant_id)
    plan_approval_id = client.post(
        "/v1/approvals", headers=approver_headers, json={"scope": plan["approval_scope"]}
    ).json()["id"]
    assert client.post(
        f"/v1/measurement-plans/{plan['id']}/approve", headers=approver_headers, json={"approval_id": plan_approval_id}
    ).status_code == 200
    assert client.post(f"/v1/measurement-plans/{plan['id']}/start", headers=headers).status_code == 200

    capture_resp = client.post(
        f"/v1/measurement-plans/{plan['id']}/capture-followup", headers=headers,
        json={"observed": _valid_observed(gross_margin="500.00")},
    )
    assert capture_resp.status_code == 200, capture_resp.text

    evaluate_resp = client.post(f"/v1/measurement-plans/{plan['id']}/evaluate", headers=headers)
    assert evaluate_resp.status_code == 200, evaluate_resp.text
    report = evaluate_resp.json()
    assert report["result_classification"] == "positive_observed_result"

    # 19: create and verify the sealed evidence bundle -- the complete chain.
    bundle_resp = client.post(
        f"/v1/recommendations/{recommendation['id']}/evidence-bundle", headers=headers, json={}
    )
    assert bundle_resp.status_code == 201, bundle_resp.text
    bundle = bundle_resp.json()
    assert bundle["status"] == "sealed", bundle
    assert bundle["missing_resources"] == []

    verify_resp = client.get(f"/v1/decision-outcome-evidence/{bundle['id']}/verify", headers=headers)
    assert verify_resp.status_code == 200, verify_resp.text
    verification = verify_resp.json()
    assert verification["verified"] is True
    assert verification["stored_hashes_intact"] is True
    assert verification["live_mismatches"] == []

    by_type = {item["resource_type"]: item["resource_id"] for item in bundle["manifest"]}
    assert by_type["governed_recommendation"] == recommendation["id"]
    assert by_type["margin_opportunity"] == opportunity_id
    assert by_type["execution_run"] == run_id
