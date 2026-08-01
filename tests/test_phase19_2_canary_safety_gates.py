"""Spec 92 Workstream B -- canary safety pauses, incidents, promotion hardening."""

from __future__ import annotations

from uuid import uuid4

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import update

from apps.api.main import app
from erpguard.config import settings
from erpguard.db.model_packages.canary import CanaryRoutingDecision
from erpguard.db.model_packages.execution import ExecutionRun
from erpguard.db.model_packages.skill_package import SkillPackage
from erpguard.db.session import SessionLocal, init_db
from erpguard.domain.execution.kill_switch_service import KillSwitchService
from erpguard.domain.shadow.service import ShadowService

from test_phase14_skill_compiler import _identity
from test_phase15_execution_permit_runtime import _build_approved_skill_package, _create_connection
from test_phase19_skill_deployment_lifecycle import _shadow_deployment_row


def _setup(monkeypatch) -> tuple[TestClient, dict, str]:
    monkeypatch.setattr(settings, "auth_secret", "skill-auth")
    monkeypatch.setattr(settings, "local_secret_key", Fernet.generate_key().decode())
    init_db()
    tenant_id = f"canary-safety-tenant-{uuid4().hex}"
    headers = _identity(tenant_id)
    return TestClient(app), headers, tenant_id


def _stable_and_canary_packages(client: TestClient, headers: dict, monkeypatch, tenant_id: str) -> tuple[str, str, str]:
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
    d1 = _shadow_deployment_row(tenant_id, process_key)
    assert client.post(
        f"/v1/skills/{stable_id}/promote-canary", headers=headers, json={"shadow_deployment_id": d1, "reason": "t"}
    ).status_code == 200
    assert client.post(f"/v1/skills/{stable_id}/promote-active", headers=headers, json={"reason": "t"}).status_code == 200

    d2 = _shadow_deployment_row(tenant_id, process_key)
    assert client.post(
        f"/v1/skills/{canary_id}/promote-canary", headers=headers, json={"shadow_deployment_id": d2, "reason": "t"}
    ).status_code == 200
    return process_key, stable_id, canary_id


def _active_policy(client, headers, tenant_id, *, process_key, stable_id, canary_id, **overrides) -> dict:
    shadow_deployment_id = _shadow_deployment_row(tenant_id, process_key)
    payload = {
        "process_key": process_key,
        "stable_skill_package_id": stable_id,
        "canary_skill_package_id": canary_id,
        "shadow_deployment_id": shadow_deployment_id,
        "percentage_basis_points": 10000,
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
    assert client.post(
        f"/v1/canary-policies/{policy['id']}/approve", headers=approver_headers, json={"approval_id": approval_id}
    ).status_code == 200
    activate_resp = client.post(f"/v1/canary-policies/{policy['id']}/activate", headers=headers)
    assert activate_resp.status_code == 200, activate_resp.text
    return activate_resp.json()


def test_maximum_cases_reached_pauses_selection(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    process_key, stable_id, canary_id = _stable_and_canary_packages(client, headers, monkeypatch, tenant_id)
    _active_policy(
        client, headers, tenant_id, process_key=process_key, stable_id=stable_id, canary_id=canary_id,
        maximum_cases=1,
    )
    connection_id = _create_connection(client, headers)

    first = client.post(
        "/v1/runs/plan", headers=headers,
        json={
            "connection_id": connection_id, "process_key": process_key, "capability": "sales.order.read",
            "idempotency_key": f"idem-{uuid4().hex}",
            "routing_context": {"business_object_key": "obj-1", "capability": "sales.order.read"},
        },
    )
    assert first.status_code == 201, first.text
    assert first.json()["skill_package_id"] == canary_id

    second = client.post(
        "/v1/runs/plan", headers=headers,
        json={
            "connection_id": connection_id, "process_key": process_key, "capability": "sales.order.read",
            "idempotency_key": f"idem-{uuid4().hex}",
            "routing_context": {"business_object_key": "obj-2", "capability": "sales.order.read"},
        },
    )
    assert second.status_code == 201, second.text
    assert second.json()["skill_package_id"] == stable_id


def test_maximum_amount_reached_pauses_selection(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    process_key, stable_id, canary_id = _stable_and_canary_packages(client, headers, monkeypatch, tenant_id)
    _active_policy(
        client, headers, tenant_id, process_key=process_key, stable_id=stable_id, canary_id=canary_id,
        maximum_total_amount=100, allowed_capabilities=[],
    )
    connection_id = _create_connection(client, headers)

    over_limit = client.post(
        "/v1/runs/plan", headers=headers,
        json={
            "connection_id": connection_id, "process_key": process_key, "capability": "sales.order.read",
            "idempotency_key": f"idem-{uuid4().hex}",
            "routing_context": {"business_object_key": "obj-1", "amount": "150.00"},
        },
    )
    assert over_limit.status_code == 201, over_limit.text
    assert over_limit.json()["skill_package_id"] == stable_id


def test_kill_switch_routes_blocked(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    process_key, stable_id, canary_id = _stable_and_canary_packages(client, headers, monkeypatch, tenant_id)
    _active_policy(client, headers, tenant_id, process_key=process_key, stable_id=stable_id, canary_id=canary_id)
    connection_id = _create_connection(client, headers)

    db = SessionLocal()
    try:
        KillSwitchService(db).set(tenant_id=tenant_id, active=True)
    finally:
        db.close()

    plan_resp = client.post(
        "/v1/runs/plan", headers=headers,
        json={
            "connection_id": connection_id, "process_key": process_key, "capability": "sales.order.read",
            "idempotency_key": f"idem-{uuid4().hex}",
            "routing_context": {"business_object_key": "obj-1", "capability": "sales.order.read"},
        },
    )
    assert plan_resp.status_code == 400, plan_resp.text
    assert "kill_switch" in plan_resp.json()["detail"]


def test_critical_incident_auto_pauses_policy(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    process_key, stable_id, canary_id = _stable_and_canary_packages(client, headers, monkeypatch, tenant_id)
    policy = _active_policy(client, headers, tenant_id, process_key=process_key, stable_id=stable_id, canary_id=canary_id)

    incident_resp = client.post(
        f"/v1/canary-policies/{policy['id']}/incidents", headers=headers,
        json={"incident_type": "unexpected_invoice", "severity": "critical", "details": {}},
    )
    assert incident_resp.status_code == 201, incident_resp.text

    policy_after = client.get(f"/v1/canary-policies/{policy['id']}", headers=headers).json()
    assert policy_after["status"] == "paused"

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


def test_promotion_blocked_when_canary_policy_not_completed(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    process_key, stable_id, canary_id = _stable_and_canary_packages(client, headers, monkeypatch, tenant_id)
    _active_policy(client, headers, tenant_id, process_key=process_key, stable_id=stable_id, canary_id=canary_id)

    # canary_id is still only "canary" status with an *active* (not completed) policy.
    promote_resp = client.post(f"/v1/skills/{canary_id}/promote-active", headers=headers, json={"reason": "t"})
    assert promote_resp.status_code == 400, promote_resp.text
    assert "canary_policy_not_eligible_for_promotion" in promote_resp.json()["detail"]


def _plan_canary_cases(client, headers, connection_id, process_key, count):
    for i in range(count):
        resp = client.post(
            "/v1/runs/plan", headers=headers,
            json={
                "connection_id": connection_id, "process_key": process_key, "capability": "sales.order.read",
                "idempotency_key": f"idem-{uuid4().hex}",
                "routing_context": {"business_object_key": f"obj-{i}", "capability": "sales.order.read"},
            },
        )
        assert resp.status_code == 201, resp.text


def _mark_canary_runs_succeeded(tenant_id: str, policy_id: str) -> None:
    """The fake connector's `sales.order.read` execution path is disabled
    (`execution_not_enabled`), so these tests can't drive a real run to
    `succeeded` through the API. Seeding the terminal status directly is the
    same technique `_stable_and_canary_packages` already uses to seed
    `process_key`/`ShadowDeployment` state -- it stands in for "these 12
    canary cases were later executed and passed postconditions", which is
    exactly the evidence `_check_canary_policy_eligibility` now requires."""

    db = SessionLocal()
    try:
        decisions = (
            db.query(CanaryRoutingDecision)
            .filter_by(tenant_id=tenant_id, canary_policy_id=policy_id, selected_lane="canary")
            .filter(CanaryRoutingDecision.execution_run_id.isnot(None))
            .all()
        )
        run_ids = [row.execution_run_id for row in decisions]
        db.query(ExecutionRun).filter(ExecutionRun.id.in_(run_ids)).update(
            {"status": "succeeded"}, synchronize_session=False
        )
        db.commit()
    finally:
        db.close()


def test_promotion_permitted_with_completed_policy_and_evidence(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    process_key, stable_id, canary_id = _stable_and_canary_packages(client, headers, monkeypatch, tenant_id)
    policy = _active_policy(
        client, headers, tenant_id, process_key=process_key, stable_id=stable_id, canary_id=canary_id,
        maximum_cases=10,
    )

    connection_id = _create_connection(client, headers)
    _plan_canary_cases(client, headers, connection_id, process_key, 12)
    _mark_canary_runs_succeeded(tenant_id, policy["id"])

    complete_resp = client.post(f"/v1/canary-policies/{policy['id']}/complete", headers=headers)
    assert complete_resp.status_code == 200, complete_resp.text

    promote_resp = client.post(f"/v1/skills/{canary_id}/promote-active", headers=headers, json={"reason": "t"})
    assert promote_resp.status_code == 200, promote_resp.text
    assert promote_resp.json()["status"] == "active"


def test_promotion_blocked_when_postcondition_evidence_insufficient(monkeypatch):
    """Sec 9.9/18 "insufficient evidence blocks": a completed policy with
    enough *planned* cases but no executed/verified postcondition evidence
    must not be treated as `postcondition_success_rate == 1.0`."""

    client, headers, tenant_id = _setup(monkeypatch)
    process_key, stable_id, canary_id = _stable_and_canary_packages(client, headers, monkeypatch, tenant_id)
    policy = _active_policy(
        client, headers, tenant_id, process_key=process_key, stable_id=stable_id, canary_id=canary_id,
        maximum_cases=10,
    )

    connection_id = _create_connection(client, headers)
    _plan_canary_cases(client, headers, connection_id, process_key, 12)
    # No terminal execution seeded -- every canary run stays "planned".

    complete_resp = client.post(f"/v1/canary-policies/{policy['id']}/complete", headers=headers)
    assert complete_resp.status_code == 200, complete_resp.text

    promote_resp = client.post(f"/v1/skills/{canary_id}/promote-active", headers=headers, json={"reason": "t"})
    assert promote_resp.status_code == 400, promote_resp.text
    assert "insufficient_postcondition_success_rate" in promote_resp.json()["detail"]


def test_canary_status_alone_insufficient_when_no_policy_exists_still_works(monkeypatch):
    """Packages promoted without ever having a CanaryPolicy (Phase 19's
    original path) are unaffected by the Sec 9.9 hardening."""

    client, headers, tenant_id = _setup(monkeypatch)
    skill_id = _build_approved_skill_package(client, headers, tenant_id)
    monkeypatch.setattr(
        ShadowService, "dashboard", lambda self, *, tenant_id, deployment_id: {"recommendation": "eligible_for_canary"}
    )
    db = SessionLocal()
    process_key = db.query(SkillPackage).filter_by(id=skill_id).one().process_key
    db.close()
    deployment_id = _shadow_deployment_row(tenant_id, process_key)
    assert client.post(
        f"/v1/skills/{skill_id}/promote-canary", headers=headers,
        json={"shadow_deployment_id": deployment_id, "reason": "t"},
    ).status_code == 200

    promote_resp = client.post(f"/v1/skills/{skill_id}/promote-active", headers=headers, json={"reason": "t"})
    assert promote_resp.status_code == 200, promote_resp.text
