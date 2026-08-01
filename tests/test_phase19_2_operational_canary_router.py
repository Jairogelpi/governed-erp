"""Spec 92 Workstream B -- deterministic canary routing.

`routing.py`'s bucket/lane functions are pure and tested directly with no
DB. Policy lifecycle + routing persistence go through the public API,
reusing Phase 19's shadow-eligibility monkeypatch technique and the
same-process-key trick `test_phase19_1_active_skill_execution_wiring.py`
established for building two packages under one governed process.
"""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import update

from apps.api.main import app
from erpguard.config import settings
from erpguard.db.model_packages.canary import CanaryRoutingDecision
from erpguard.db.model_packages.execution import ExecutionRun
from erpguard.db.model_packages.skill_package import SkillPackage
from erpguard.db.session import SessionLocal, init_db
from erpguard.domain.canary.routing import compute_bucket, select_lane
from erpguard.domain.shadow.service import ShadowService

from test_phase14_skill_compiler import _identity
from test_phase15_execution_permit_runtime import _build_approved_skill_package, _create_connection
from test_phase19_skill_deployment_lifecycle import _shadow_deployment_row


def test_bucket_is_deterministic_for_same_inputs():
    b1 = compute_bucket(tenant_id="t1", canary_policy_id="p1", process_key="proc", business_object_key="obj-1")
    b2 = compute_bucket(tenant_id="t1", canary_policy_id="p1", process_key="proc", business_object_key="obj-1")
    assert b1 == b2
    assert 0 <= b1 < 10000


def test_bucket_differs_for_different_object():
    b1 = compute_bucket(tenant_id="t1", canary_policy_id="p1", process_key="proc", business_object_key="obj-1")
    b2 = compute_bucket(tenant_id="t1", canary_policy_id="p1", process_key="proc", business_object_key="obj-2")
    assert b1 != b2


def test_select_lane_boundary_percentages():
    assert select_lane(bucket=0, percentage_basis_points=0) == "stable"
    assert select_lane(bucket=0, percentage_basis_points=1) == "canary"
    assert select_lane(bucket=9999, percentage_basis_points=10000) == "canary"
    assert select_lane(bucket=5000, percentage_basis_points=5000) == "stable"
    assert select_lane(bucket=4999, percentage_basis_points=5000) == "canary"


def _setup(monkeypatch) -> tuple[TestClient, dict, str]:
    monkeypatch.setattr(settings, "auth_secret", "skill-auth")
    monkeypatch.setattr(settings, "local_secret_key", Fernet.generate_key().decode())
    init_db()
    tenant_id = f"canary-tenant-{uuid4().hex}"
    headers = _identity(tenant_id)
    return TestClient(app), headers, tenant_id


def _stable_and_canary_packages(client: TestClient, headers: dict, monkeypatch, tenant_id: str) -> tuple[str, str, str]:
    """Returns (process_key, stable_skill_package_id, canary_skill_package_id)."""

    stable_id = _build_approved_skill_package(client, headers, tenant_id)
    canary_id = _build_approved_skill_package(client, headers, tenant_id)

    db = SessionLocal()
    try:
        process_key = db.query(SkillPackage).filter_by(id=stable_id).one().process_key
        db.execute(update(SkillPackage).where(SkillPackage.id == canary_id).values(process_key=process_key))
        db.commit()
    finally:
        db.close()

    monkeypatch.setattr(
        ShadowService, "dashboard", lambda self, *, tenant_id, deployment_id: {"recommendation": "eligible_for_canary"}
    )
    deployment_1 = _shadow_deployment_row(tenant_id, process_key)
    assert client.post(
        f"/v1/skills/{stable_id}/promote-canary", headers=headers,
        json={"shadow_deployment_id": deployment_1, "reason": "t"},
    ).status_code == 200
    assert client.post(
        f"/v1/skills/{stable_id}/promote-active", headers=headers, json={"reason": "t"}
    ).status_code == 200

    deployment_2 = _shadow_deployment_row(tenant_id, process_key)
    assert client.post(
        f"/v1/skills/{canary_id}/promote-canary", headers=headers,
        json={"shadow_deployment_id": deployment_2, "reason": "t"},
    ).status_code == 200

    return process_key, stable_id, canary_id


def _active_policy(client, headers, tenant_id, *, process_key, stable_id, canary_id, monkeypatch, **overrides) -> dict:
    shadow_deployment_id = _shadow_deployment_row(tenant_id, process_key)
    payload = {
        "process_key": process_key,
        "stable_skill_package_id": stable_id,
        "canary_skill_package_id": canary_id,
        "shadow_deployment_id": shadow_deployment_id,
        "percentage_basis_points": 5000,
        "maximum_cases": 100,
        "maximum_total_amount": 100000,
        "allowed_capabilities": ["sales.order.read"],
        "maximum_amount": 100000,
        **overrides,
    }
    create_resp = client.post("/v1/canary-policies", headers=headers, json=payload)
    assert create_resp.status_code == 201, create_resp.text
    policy = create_resp.json()

    approver_headers = _identity(tenant_id)
    approval_id = client.post(
        "/v1/approvals", headers=approver_headers, json={"scope": policy["approval_scope"]}
    ).json()["id"]
    approve_resp = client.post(
        f"/v1/canary-policies/{policy['id']}/approve", headers=approver_headers, json={"approval_id": approval_id}
    )
    assert approve_resp.status_code == 200, approve_resp.text

    activate_resp = client.post(f"/v1/canary-policies/{policy['id']}/activate", headers=headers)
    assert activate_resp.status_code == 200, activate_resp.text
    return activate_resp.json()


def test_no_routing_context_routes_stable(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    process_key, stable_id, canary_id = _stable_and_canary_packages(client, headers, monkeypatch, tenant_id)
    _active_policy(client, headers, tenant_id, process_key=process_key, stable_id=stable_id, canary_id=canary_id, monkeypatch=monkeypatch)

    connection_id = _create_connection(client, headers)
    plan_resp = client.post(
        "/v1/runs/plan", headers=headers,
        json={
            "connection_id": connection_id, "process_key": process_key, "capability": "sales.order.read",
            "idempotency_key": f"idem-{uuid4().hex}",
        },
    )
    assert plan_resp.status_code == 201, plan_resp.text
    assert plan_resp.json()["skill_package_id"] == stable_id


def test_inactive_policy_routes_stable(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    process_key, stable_id, canary_id = _stable_and_canary_packages(client, headers, monkeypatch, tenant_id)
    # No policy created at all.
    connection_id = _create_connection(client, headers)
    plan_resp = client.post(
        "/v1/runs/plan", headers=headers,
        json={
            "connection_id": connection_id, "process_key": process_key, "capability": "sales.order.read",
            "idempotency_key": f"idem-{uuid4().hex}",
            "routing_context": {"business_object_key": "obj-1", "capability": "sales.order.read"},
        },
    )
    assert plan_resp.status_code == 201, plan_resp.text
    assert plan_resp.json()["skill_package_id"] == stable_id


def test_outside_scope_routes_stable(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    process_key, stable_id, canary_id = _stable_and_canary_packages(client, headers, monkeypatch, tenant_id)
    _active_policy(
        client, headers, tenant_id, process_key=process_key, stable_id=stable_id, canary_id=canary_id,
        monkeypatch=monkeypatch, allowed_capabilities=["some.other.capability"],
    )
    connection_id = _create_connection(client, headers)
    plan_resp = client.post(
        "/v1/runs/plan", headers=headers,
        json={
            "connection_id": connection_id, "process_key": process_key, "capability": "sales.order.read",
            "idempotency_key": f"idem-{uuid4().hex}",
            "routing_context": {"business_object_key": "obj-1", "capability": "sales.order.read"},
        },
    )
    assert plan_resp.status_code == 201, plan_resp.text
    assert plan_resp.json()["skill_package_id"] == stable_id


def test_same_object_always_selects_same_lane_and_decision_is_persisted_and_immutable(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    process_key, stable_id, canary_id = _stable_and_canary_packages(client, headers, monkeypatch, tenant_id)
    policy = _active_policy(
        client, headers, tenant_id, process_key=process_key, stable_id=stable_id, canary_id=canary_id,
        monkeypatch=monkeypatch, percentage_basis_points=10000,  # force canary every time
    )
    connection_id = _create_connection(client, headers)
    plan_resp = client.post(
        "/v1/runs/plan", headers=headers,
        json={
            "connection_id": connection_id, "process_key": process_key, "capability": "sales.order.read",
            "idempotency_key": f"idem-{uuid4().hex}",
            "routing_context": {"business_object_key": "obj-fixed", "capability": "sales.order.read"},
        },
    )
    assert plan_resp.status_code == 201, plan_resp.text
    assert plan_resp.json()["skill_package_id"] == canary_id

    decisions_resp = client.get(f"/v1/canary-policies/{policy['id']}/routing-decisions", headers=headers)
    assert decisions_resp.status_code == 200
    decisions = decisions_resp.json()
    assert len(decisions) == 1
    assert decisions[0]["selected_lane"] == "canary"
    assert decisions[0]["execution_run_id"] is not None

    db = SessionLocal()
    try:
        row = db.query(CanaryRoutingDecision).filter_by(id=decisions[0]["id"]).one()
        row.selection_reason = "tampered"
        with pytest.raises(ValueError, match="canary_routing_decision_immutable"):
            db.commit()
        db.rollback()
    finally:
        db.close()


def test_dashboard_reports_real_cumulative_amount_and_unexpected_side_effects(monkeypatch):
    """Sec 9.8: `cumulative_amount` and `unexpected_side_effects` must reflect
    actual run data, not the hardcoded-zero stubs the dashboard used to
    return. The fake connector's `sales.order.read` execution path can't
    produce a real line-item write or a real forbidden-effect postcondition
    failure, so the two scenarios are seeded directly on the `ExecutionRun`
    rows the routing decisions already point at -- same direct-DB technique
    `_mark_canary_runs_succeeded` uses elsewhere in this suite."""

    client, headers, tenant_id = _setup(monkeypatch)
    process_key, stable_id, canary_id = _stable_and_canary_packages(client, headers, monkeypatch, tenant_id)
    policy = _active_policy(
        client, headers, tenant_id, process_key=process_key, stable_id=stable_id, canary_id=canary_id,
        monkeypatch=monkeypatch, percentage_basis_points=10000,  # force canary every time
    )
    connection_id = _create_connection(client, headers)

    run_ids = []
    for i in range(2):
        plan_resp = client.post(
            "/v1/runs/plan", headers=headers,
            json={
                "connection_id": connection_id, "process_key": process_key, "capability": "sales.order.read",
                "idempotency_key": f"idem-{uuid4().hex}",
                "routing_context": {"business_object_key": f"obj-amt-{i}", "capability": "sales.order.read"},
            },
        )
        assert plan_resp.status_code == 201, plan_resp.text
        run_ids.append(plan_resp.json()["id"])

    db = SessionLocal()
    try:
        priced_run = db.query(ExecutionRun).filter_by(id=run_ids[0]).one()
        plan_payload = json.loads(priced_run.action_plan_json)
        plan_payload["capability_payload"] = {"lines": [{"quantity": 2, "price_unit": 125.0}]}
        priced_run.action_plan_json = json.dumps(plan_payload)
        priced_run.status = "succeeded"
        priced_run.verification_result_json = json.dumps({"postcondition": {"verified": True}})

        side_effect_run = db.query(ExecutionRun).filter_by(id=run_ids[1]).one()
        side_effect_run.status = "failed"
        side_effect_run.verification_result_json = json.dumps(
            {"postcondition": {"verified": False, "summary": "forbidden_effect_observed:invoice_created"}}
        )
        db.commit()
    finally:
        db.close()

    dashboard_resp = client.get(f"/v1/canary-policies/{policy['id']}/dashboard", headers=headers)
    assert dashboard_resp.status_code == 200, dashboard_resp.text
    dashboard = dashboard_resp.json()
    assert dashboard["cumulative_amount"] == 250.0
    assert dashboard["unexpected_side_effects"] == 1
    # These runs used sales.order.read directly (no GovernedActionDraft/
    # GovernedRecommendation chain), so there is nothing to trace an
    # opportunity value back through -- stays null, never guessed.
    assert dashboard["estimated_opportunity_value"] is None


def test_two_active_policies_for_same_process_rejected(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    # Build the second canary candidate up front, before any ShadowDeployment
    # fixture exists for this tenant -- the operational shadow feed reprocesses
    # every existing ShadowDeployment on each new OCEL import
    # (`_build_approved_skill_package` seeds one), and these test-only stub
    # deployments aren't meant to receive real events.
    second_canary_id = _build_approved_skill_package(client, headers, tenant_id)
    process_key, stable_id, canary_id = _stable_and_canary_packages(client, headers, monkeypatch, tenant_id)

    db = SessionLocal()
    try:
        db.execute(update(SkillPackage).where(SkillPackage.id == second_canary_id).values(process_key=process_key))
        db.commit()
    finally:
        db.close()

    _active_policy(client, headers, tenant_id, process_key=process_key, stable_id=stable_id, canary_id=canary_id, monkeypatch=monkeypatch)

    deployment = _shadow_deployment_row(tenant_id, process_key)
    assert client.post(
        f"/v1/skills/{second_canary_id}/promote-canary", headers=headers,
        json={"shadow_deployment_id": deployment, "reason": "t"},
    ).status_code == 200

    shadow_deployment_id = _shadow_deployment_row(tenant_id, process_key)
    create_resp = client.post(
        "/v1/canary-policies", headers=headers,
        json={
            "process_key": process_key, "stable_skill_package_id": stable_id,
            "canary_skill_package_id": second_canary_id, "shadow_deployment_id": shadow_deployment_id,
            "percentage_basis_points": 1000, "maximum_cases": 10, "maximum_total_amount": 1000,
            "allowed_capabilities": ["sales.order.read"], "maximum_amount": 1000,
        },
    )
    policy2 = create_resp.json()
    approver_headers = _identity(tenant_id)
    approval_id = client.post(
        "/v1/approvals", headers=approver_headers, json={"scope": policy2["approval_scope"]}
    ).json()["id"]
    client.post(f"/v1/canary-policies/{policy2['id']}/approve", headers=approver_headers, json={"approval_id": approval_id})

    activate_resp = client.post(f"/v1/canary-policies/{policy2['id']}/activate", headers=headers)
    assert activate_resp.status_code == 400, activate_resp.text
    assert "already_active" in activate_resp.json()["detail"]


def test_another_tenant_cannot_inspect_policy(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    process_key, stable_id, canary_id = _stable_and_canary_packages(client, headers, monkeypatch, tenant_id)
    policy = _active_policy(client, headers, tenant_id, process_key=process_key, stable_id=stable_id, canary_id=canary_id, monkeypatch=monkeypatch)

    other_headers = _identity(f"other-tenant-{uuid4().hex}")
    resp = client.get(f"/v1/canary-policies/{policy['id']}", headers=other_headers)
    assert resp.status_code == 404, resp.text
