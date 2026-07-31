"""Phase 19 -- skill deployment lifecycle: canary -> active -> rollback.

Builds an `approved` SkillPackage through the real candidate/proof/compile
chain (reusing Phase 14's helpers), then drives `SkillDeploymentService`
directly. Shadow eligibility is exercised via a real `ShadowDeployment` row
plus a monkeypatched `ShadowService.dashboard` recommendation -- building 30+
real canonical-feed cases just to flip one boolean is not what this test is
checking; `test_phase18_shadow_mode.py` already covers the eligibility math
itself.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.config import settings
from sqlalchemy import update

from erpguard.db.model_packages.shadow import ShadowDeployment
from erpguard.db.model_packages.skill_deployment import SkillDeploymentEvent
from erpguard.db.model_packages.skill_package import SkillPackage
from erpguard.db.session import SessionLocal, init_db
from erpguard.domain.deployment.service import (
    CanaryNotEligible,
    InvalidStatusTransition,
    NoActiveSkillPackage,
    SkillDeploymentService,
)
from erpguard.domain.shadow.service import ShadowService

from test_phase14_skill_compiler import _build_submitted_candidate_with_proof, _identity


def _approved_skill_package(client: TestClient, headers: dict, tenant_id: str) -> tuple[str, str]:
    """Returns (skill_id, process_key)."""

    candidate_id, process_key, version = _build_submitted_candidate_with_proof(client, headers, tenant_id)
    compile_resp = client.post(
        f"/v1/process-candidates/{candidate_id}/compile",
        headers=headers,
        json={"connector_id": "fake", "workflow_steps": []},
    )
    assert compile_resp.status_code == 201, compile_resp.text
    skill_id = compile_resp.json()["id"]

    approve_resp = client.post(f"/v1/skills/{skill_id}/versions/{version}/approve", headers=headers)
    assert approve_resp.status_code == 200, approve_resp.text
    return skill_id, process_key


def _shadow_deployment_row(tenant_id: str, process_key: str) -> str:
    deployment_id = f"shadow_{uuid4().hex}"
    db = SessionLocal()
    try:
        db.add(
            ShadowDeployment(
                id=deployment_id,
                tenant_id=tenant_id,
                candidate_id=f"cand_{uuid4().hex}",
                proof_id=f"proof_{uuid4().hex}",
                process_key=process_key,
                active_version="1.0.0",
                candidate_version="1.1.0",
                object_type="sales_order",
                status="shadow",
                agreement_threshold=0.9,
                created_by="test",
            )
        )
        db.commit()
    finally:
        db.close()
    return deployment_id


def _setup(monkeypatch) -> tuple[TestClient, dict, str]:
    monkeypatch.setattr(settings, "auth_secret", "skill-auth")
    init_db()
    tenant_id = f"deploy-tenant-{uuid4().hex}"
    headers = _identity(tenant_id)
    return TestClient(app), headers, tenant_id


def _patch_dashboard(monkeypatch, recommendation: str) -> None:
    monkeypatch.setattr(
        ShadowService,
        "dashboard",
        lambda self, *, tenant_id, deployment_id: {"recommendation": recommendation},
    )


def test_promote_to_canary_requires_eligible_shadow_evidence(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    skill_id, process_key = _approved_skill_package(client, headers, tenant_id)
    deployment_id = _shadow_deployment_row(tenant_id, process_key)
    _patch_dashboard(monkeypatch, "continue_shadow")

    db = SessionLocal()
    try:
        with pytest.raises(CanaryNotEligible):
            SkillDeploymentService(db).promote_to_canary(
                tenant_id=tenant_id, skill_id=skill_id, shadow_deployment_id=deployment_id, actor="tester"
            )
    finally:
        db.close()


def test_promote_to_canary_requires_approved_status(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    candidate_id, process_key, version = _build_submitted_candidate_with_proof(client, headers, tenant_id)
    compile_resp = client.post(
        f"/v1/process-candidates/{candidate_id}/compile",
        headers=headers,
        json={"connector_id": "fake", "workflow_steps": []},
    )
    skill_id = compile_resp.json()["id"]  # still "compiled", never approved
    deployment_id = _shadow_deployment_row(tenant_id, process_key)
    _patch_dashboard(monkeypatch, "eligible_for_canary")

    db = SessionLocal()
    try:
        with pytest.raises(InvalidStatusTransition):
            SkillDeploymentService(db).promote_to_canary(
                tenant_id=tenant_id, skill_id=skill_id, shadow_deployment_id=deployment_id, actor="tester"
            )
    finally:
        db.close()


def test_promote_to_active_supersedes_prior_active_and_rollback_restores_it(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    skill_id_1, process_key = _approved_skill_package(client, headers, tenant_id)
    skill_id_2, other_process_key = _approved_skill_package(client, headers, tenant_id)
    _patch_dashboard(monkeypatch, "eligible_for_canary")

    # Simulate a second version compiled for the *same* process (the helper
    # always registers a fresh process) via a raw update that bypasses the
    # ORM immutability listener -- test scaffolding only, not a real path.
    db_setup = SessionLocal()
    try:
        db_setup.execute(
            update(SkillPackage).where(SkillPackage.id == skill_id_2).values(process_key=process_key)
        )
        db_setup.commit()
    finally:
        db_setup.close()

    db = SessionLocal()
    try:
        service = SkillDeploymentService(db)

        deployment_1 = _shadow_deployment_row(tenant_id, process_key)
        service.promote_to_canary(tenant_id=tenant_id, skill_id=skill_id_1, shadow_deployment_id=deployment_1, actor="a")
        active_1 = service.promote_to_active(tenant_id=tenant_id, skill_id=skill_id_1, actor="a")
        assert active_1.status == "active"
        assert service.get_active(tenant_id=tenant_id, process_key=process_key).id == skill_id_1

        deployment_2 = _shadow_deployment_row(tenant_id, process_key)
        service.promote_to_canary(tenant_id=tenant_id, skill_id=skill_id_2, shadow_deployment_id=deployment_2, actor="a")
        active_2 = service.promote_to_active(tenant_id=tenant_id, skill_id=skill_id_2, actor="a")
        assert active_2.status == "active"

        db.expire_all()
        assert service._get(tenant_id=tenant_id, skill_id=skill_id_1).status == "deprecated"
        assert service.get_active(tenant_id=tenant_id, process_key=process_key).id == skill_id_2
        active_rows = db.query(SkillDeploymentEvent).filter_by(tenant_id=tenant_id, process_key=process_key).all()
        assert any(row.event_type == "deprecate" for row in active_rows)

        restored = service.rollback(tenant_id=tenant_id, process_key=process_key, actor="a", reason="bad_metrics")
        assert restored is not None
        assert restored.id == skill_id_1
        assert restored.status == "active"

        db.expire_all()
        assert service._get(tenant_id=tenant_id, skill_id=skill_id_2).status == "rolled_back"
        assert service.get_active(tenant_id=tenant_id, process_key=process_key).id == skill_id_1
    finally:
        db.close()


def test_rollback_with_no_predecessor_leaves_no_active_package(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    skill_id, process_key = _approved_skill_package(client, headers, tenant_id)
    deployment_id = _shadow_deployment_row(tenant_id, process_key)
    _patch_dashboard(monkeypatch, "eligible_for_canary")

    db = SessionLocal()
    try:
        service = SkillDeploymentService(db)
        service.promote_to_canary(tenant_id=tenant_id, skill_id=skill_id, shadow_deployment_id=deployment_id, actor="a")
        service.promote_to_active(tenant_id=tenant_id, skill_id=skill_id, actor="a")

        restored = service.rollback(tenant_id=tenant_id, process_key=process_key, actor="a", reason="oops")
        assert restored is None
        assert service.get_active(tenant_id=tenant_id, process_key=process_key) is None
    finally:
        db.close()


def test_rollback_rejected_when_no_active_package(monkeypatch):
    _client, _headers, tenant_id = _setup(monkeypatch)
    db = SessionLocal()
    try:
        with pytest.raises(NoActiveSkillPackage):
            SkillDeploymentService(db).rollback(tenant_id=tenant_id, process_key="no_such_process", actor="a")
    finally:
        db.close()


def test_skill_deployment_events_are_immutable(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    skill_id, process_key = _approved_skill_package(client, headers, tenant_id)
    deployment_id = _shadow_deployment_row(tenant_id, process_key)
    _patch_dashboard(monkeypatch, "eligible_for_canary")

    db = SessionLocal()
    try:
        SkillDeploymentService(db).promote_to_canary(
            tenant_id=tenant_id, skill_id=skill_id, shadow_deployment_id=deployment_id, actor="a"
        )
        row = db.query(SkillDeploymentEvent).filter_by(tenant_id=tenant_id, skill_package_id=skill_id).one()
        row.reason = "tampered"
        with pytest.raises(ValueError, match="skill_deployment_event_immutable"):
            db.commit()
        db.rollback()
    finally:
        db.close()


def test_promote_and_rollback_api_round_trip(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    skill_id, process_key = _approved_skill_package(client, headers, tenant_id)
    deployment_id = _shadow_deployment_row(tenant_id, process_key)
    _patch_dashboard(monkeypatch, "eligible_for_canary")

    canary_resp = client.post(
        f"/v1/skills/{skill_id}/promote-canary",
        headers=headers,
        json={"shadow_deployment_id": deployment_id, "reason": "looks good"},
    )
    assert canary_resp.status_code == 200, canary_resp.text
    assert canary_resp.json()["status"] == "canary"

    active_resp = client.post(f"/v1/skills/{skill_id}/promote-active", headers=headers, json={"reason": "go"})
    assert active_resp.status_code == 200, active_resp.text
    assert active_resp.json()["status"] == "active"

    get_active_resp = client.get(f"/v1/processes/{process_key}/active-skill", headers=headers)
    assert get_active_resp.status_code == 200, get_active_resp.text
    assert get_active_resp.json()["active"]["id"] == skill_id

    rollback_resp = client.post(
        "/v1/skills/rollback", headers=headers, json={"process_key": process_key, "reason": "regression found"}
    )
    assert rollback_resp.status_code == 200, rollback_resp.text
    assert rollback_resp.json()["active"] is None

    get_active_after = client.get(f"/v1/processes/{process_key}/active-skill", headers=headers)
    assert get_active_after.json()["active"] is None
