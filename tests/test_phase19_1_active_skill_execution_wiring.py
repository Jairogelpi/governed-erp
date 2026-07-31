"""Phase 19.1 -- wire the Phase 19 active SkillPackage pointer into PermitService.

Reuses Phase 15's execution-permit test helpers and Phase 19's
canary-promotion monkeypatch technique (real 30-case shadow eligibility
isn't the point of this test; ShadowService.dashboard's recommendation is
stubbed the same way test_phase19_skill_deployment_lifecycle.py does).
"""

from __future__ import annotations

from uuid import uuid4

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.config import settings
from erpguard.db.model_packages.skill_package import SkillPackage
from erpguard.db.session import SessionLocal, init_db
from erpguard.domain.shadow.service import ShadowService

from test_phase15_execution_permit_runtime import (
    _build_approved_skill_package,
    _create_connection,
    _identity,
    _plan_and_approve_run,
)
from test_phase19_skill_deployment_lifecycle import _shadow_deployment_row


def _process_key_for(skill_package_id: str) -> str:
    db = SessionLocal()
    try:
        return db.query(SkillPackage).filter_by(id=skill_package_id).one().process_key
    finally:
        db.close()


def _setup(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "exec-auth")
    monkeypatch.setattr(settings, "local_secret_key", Fernet.generate_key().decode())
    init_db()
    tenant_id = f"exec-tenant-{uuid4().hex}"
    headers = _identity(tenant_id)
    return TestClient(app), headers, tenant_id


def _promote(client: TestClient, headers: dict, monkeypatch, *, skill_package_id: str, process_key: str, tenant_id: str, target: str) -> None:
    monkeypatch.setattr(
        ShadowService, "dashboard", lambda self, *, tenant_id, deployment_id: {"recommendation": "eligible_for_canary"}
    )
    deployment_id = _shadow_deployment_row(tenant_id, process_key)
    canary_resp = client.post(
        f"/v1/skills/{skill_package_id}/promote-canary",
        headers=headers,
        json={"shadow_deployment_id": deployment_id, "reason": "test"},
    )
    assert canary_resp.status_code == 200, canary_resp.text
    if target == "active":
        active_resp = client.post(f"/v1/skills/{skill_package_id}/promote-active", headers=headers, json={"reason": "go"})
        assert active_resp.status_code == 200, active_resp.text


def test_canary_package_can_still_execute(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    skill_package_id = _build_approved_skill_package(client, headers, tenant_id)
    process_key = _process_key_for(skill_package_id)
    connection_id = _create_connection(client, headers)
    _promote(client, headers, monkeypatch, skill_package_id=skill_package_id, process_key=process_key, tenant_id=tenant_id, target="canary")

    run = _plan_and_approve_run(client, headers, skill_package_id=skill_package_id, connection_id=connection_id)
    assert run["status"] == "approved"


def test_active_package_can_still_execute(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    skill_package_id = _build_approved_skill_package(client, headers, tenant_id)
    process_key = _process_key_for(skill_package_id)
    connection_id = _create_connection(client, headers)
    _promote(client, headers, monkeypatch, skill_package_id=skill_package_id, process_key=process_key, tenant_id=tenant_id, target="active")

    run = _plan_and_approve_run(client, headers, skill_package_id=skill_package_id, connection_id=connection_id)
    assert run["status"] == "approved"


def test_rolled_back_package_rejected_by_plan(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    skill_package_id = _build_approved_skill_package(client, headers, tenant_id)
    process_key = _process_key_for(skill_package_id)
    connection_id = _create_connection(client, headers)
    _promote(client, headers, monkeypatch, skill_package_id=skill_package_id, process_key=process_key, tenant_id=tenant_id, target="active")

    rollback_resp = client.post(
        "/v1/skills/rollback", headers=headers, json={"process_key": process_key, "reason": "bad"}
    )
    assert rollback_resp.status_code == 200, rollback_resp.text

    plan_resp = client.post(
        "/v1/runs/plan",
        headers=headers,
        json={
            "connection_id": connection_id,
            "skill_package_id": skill_package_id,
            "capability": "sales.order.read",
            "idempotency_key": f"idem-{uuid4().hex}",
        },
    )
    assert plan_resp.status_code == 400, plan_resp.text
    assert "inactive_skill" in plan_resp.json()["detail"]


def test_plan_resolves_active_package_via_process_key(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    skill_package_id = _build_approved_skill_package(client, headers, tenant_id)
    process_key = _process_key_for(skill_package_id)
    connection_id = _create_connection(client, headers)
    _promote(client, headers, monkeypatch, skill_package_id=skill_package_id, process_key=process_key, tenant_id=tenant_id, target="active")

    plan_resp = client.post(
        "/v1/runs/plan",
        headers=headers,
        json={
            "connection_id": connection_id,
            "process_key": process_key,
            "capability": "sales.order.read",
            "idempotency_key": f"idem-{uuid4().hex}",
        },
    )
    assert plan_resp.status_code == 201, plan_resp.text
    assert plan_resp.json()["skill_package_id"] == skill_package_id


def test_plan_with_process_key_and_no_active_package_rejected(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    connection_id = _create_connection(client, headers)

    plan_resp = client.post(
        "/v1/runs/plan",
        headers=headers,
        json={
            "connection_id": connection_id,
            "process_key": "no_such_process",
            "capability": "sales.order.read",
            "idempotency_key": f"idem-{uuid4().hex}",
        },
    )
    assert plan_resp.status_code == 400, plan_resp.text
    assert "no_active_skill_for_process" in plan_resp.json()["detail"]


def test_plan_with_neither_skill_package_id_nor_process_key_rejected(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    connection_id = _create_connection(client, headers)

    plan_resp = client.post(
        "/v1/runs/plan",
        headers=headers,
        json={
            "connection_id": connection_id,
            "capability": "sales.order.read",
            "idempotency_key": f"idem-{uuid4().hex}",
        },
    )
    assert plan_resp.status_code == 400, plan_resp.text
    assert "skill_package_id_or_process_key_required" in plan_resp.json()["detail"]
