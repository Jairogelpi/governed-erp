"""Phase 15 -- Execution Permit runtime (master spec section 19).

End-to-end through the public API: candidate -> submit -> replay -> freeze
-> proof -> compile -> approve skill -> connection -> plan run -> approve
run -> execute run. Exercises the three exit criteria precisely: altered/
expired/reused permits fail, approval reuse fails, FakeConnector E2E
passes (meaning the pipeline runs cleanly through to FakeConnector's
always-blocked response, not that a write happens -- see
`erpguard/domain/execution/permit_service.py`'s module docstring).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.config import settings
from erpguard.db.model_packages.execution import ExecutionRun
from erpguard.db.model_packages.identity import IdentityMembership, IdentityUser
from erpguard.db.session import SessionLocal, init_db
from erpguard.domain.events.fake_generator import build_fake_quote_to_order_ocel
from erpguard.domain.events.ocel_service import OcelEventService
from erpguard.domain.identity.auth import issue_token
from erpguard.domain.processes.registry import ProcessRegistry


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "policies" / "processes" / "quote_to_order_v1.yaml"


def _identity(tenant_id: str, role: str = "admin") -> dict[str, str]:
    suffix = uuid4().hex
    user_id = f"exec-user-{suffix}"
    db = SessionLocal()
    db.add(IdentityUser(id=user_id, email=f"{suffix}@example.test", display_name="Exec user"))
    db.add(
        IdentityMembership(
            id=f"exec-membership-{suffix}",
            tenant_id=tenant_id,
            user_id=user_id,
            role_name=role,
            status="active",
        )
    )
    db.commit()
    db.close()
    return {"Authorization": f"Bearer {issue_token(user_id, tenant_id, 'exec-auth')}"}


def _register_process(suffix: str) -> str:
    process_key = f"exec_process_{suffix}"
    db = SessionLocal()
    try:
        base = FIXTURE.read_text(encoding="utf-8").replace("quote_to_order", process_key)
        ProcessRegistry(db).register_yaml(base)
    finally:
        db.close()
    return process_key


def _register_process_version(process_key: str, version: str) -> None:
    db = SessionLocal()
    try:
        base = FIXTURE.read_text(encoding="utf-8").replace("quote_to_order", process_key)
        base = base.replace("version: 1.0.0", f"version: {version}")
        ProcessRegistry(db).register_yaml(base)
    finally:
        db.close()


def _seed_case(tenant_id: str) -> str:
    object_key = f"so-exec-{uuid4().hex[:8]}"
    db = SessionLocal()
    try:
        OcelEventService(db).import_ocel(
            tenant_id=tenant_id,
            document=build_fake_quote_to_order_ocel(tenant_id=tenant_id, object_key=object_key, formula_valid=True),
            source="test",
        )
    finally:
        db.close()
    return object_key


def _build_approved_skill_package(client: TestClient, headers: dict, tenant_id: str) -> str:
    """Returns skill_package_id, connector_id="fake"."""

    process_key = _register_process(uuid4().hex)
    object_key = _seed_case(tenant_id)

    create_resp = client.post(
        "/v1/process-candidates",
        headers=headers,
        json={
            "process_key": process_key,
            "base_version": "1.0.0",
            "candidate_version": "1.1.0",
            "changes": {"add_metric": {"name": "extra_metric", "kind": "duration", "start_event": "sales.quote.created", "end_event": "sales.order.created"}},
            "evidence_refs": [f"case:{object_key}"],
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    candidate_id = create_resp.json()["id"]
    assert client.post(f"/v1/process-candidates/{candidate_id}/submit", headers=headers).status_code == 200

    _register_process_version(process_key, "1.1.0")

    baseline = client.post(
        f"/v1/processes/{process_key}/versions/1.0.0/replays", headers=headers, json={"object_type": "sales_order"}
    )
    assert baseline.status_code == 201, baseline.text
    candidate_replay = client.post(
        f"/v1/processes/{process_key}/versions/1.1.0/replays", headers=headers, json={"object_type": "sales_order"}
    )
    assert candidate_replay.status_code == 201, candidate_replay.text
    assert client.post(f"/v1/replays/{baseline.json()['id']}/freeze", headers=headers).status_code == 200
    assert client.post(f"/v1/replays/{candidate_replay.json()['id']}/freeze", headers=headers).status_code == 200

    proof_resp = client.post(
        f"/v1/replays/{candidate_replay.json()['id']}/proofs",
        headers=headers,
        json={"baseline_replay_id": baseline.json()["id"], "benchmark_version": "erpriskbench-1.0.0"},
    )
    assert proof_resp.status_code == 201, proof_resp.text
    assert proof_resp.json()["recommendation"] == "eligible_for_shadow"

    compile_resp = client.post(
        f"/v1/process-candidates/{candidate_id}/compile",
        headers=headers,
        json={
            "connector_id": "fake",
            "workflow_steps": [{"step_name": "read_order", "capability": "sales.order.read"}],
        },
    )
    assert compile_resp.status_code == 201, compile_resp.text
    skill_id = compile_resp.json()["id"]

    approve_resp = client.post(f"/v1/skills/{skill_id}/versions/1.1.0/approve", headers=headers)
    assert approve_resp.status_code == 200, approve_resp.text

    return skill_id


def _create_connection(client: TestClient, headers: dict) -> str:
    resp = client.post(
        "/v1/connections",
        headers=headers,
        json={
            "name": f"conn-{uuid4().hex[:8]}",
            "connector_type": "fake",
            "endpoint": "https://fake.example.test",
            "auth_type": "api_key",
            "secret": "fake-secret-value",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _plan_and_approve_run(client: TestClient, headers: dict, *, skill_package_id: str, connection_id: str, idempotency_key: str | None = None) -> dict:
    plan_resp = client.post(
        "/v1/runs/plan",
        headers=headers,
        json={
            "connection_id": connection_id,
            "skill_package_id": skill_package_id,
            "capability": "sales.order.read",
            "idempotency_key": idempotency_key or f"idem-{uuid4().hex}",
        },
    )
    assert plan_resp.status_code == 201, plan_resp.text
    run = plan_resp.json()

    approval_resp = client.post("/v1/approvals", headers=headers, json={"scope": "run:execute"})
    assert approval_resp.status_code == 201, approval_resp.text
    approval_id = approval_resp.json()["id"]

    approve_resp = client.post(
        f"/v1/runs/{run['id']}/approve", headers=headers, json={"approval_ids": [approval_id], "ttl_seconds": 900}
    )
    assert approve_resp.status_code == 200, approve_resp.text
    return approve_resp.json()


def test_fake_connector_e2e_permit_pipeline_passes(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "exec-auth")
    monkeypatch.setattr(settings, "local_secret_key", Fernet.generate_key().decode())
    init_db()
    tenant_id = f"exec-tenant-{uuid4().hex}"
    headers = _identity(tenant_id)
    client = TestClient(app)

    skill_package_id = _build_approved_skill_package(client, headers, tenant_id)
    connection_id = _create_connection(client, headers)
    run = _plan_and_approve_run(client, headers, skill_package_id=skill_package_id, connection_id=connection_id)

    execute_resp = client.post(f"/v1/runs/{run['id']}/execute", headers=headers)
    assert execute_resp.status_code == 200, execute_resp.text
    executed = execute_resp.json()
    assert executed["status"] == "blocked"
    assert executed["verification_result"]["connector_result"]["status"] == "blocked"
    assert executed["verification_result"]["connector_result"]["errors"] == ["execution_not_enabled"]


def test_altered_permit_fails(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "exec-auth")
    monkeypatch.setattr(settings, "local_secret_key", Fernet.generate_key().decode())
    init_db()
    tenant_id = f"exec-tenant-{uuid4().hex}"
    headers = _identity(tenant_id)
    client = TestClient(app)

    skill_package_id = _build_approved_skill_package(client, headers, tenant_id)
    connection_id = _create_connection(client, headers)
    run = _plan_and_approve_run(client, headers, skill_package_id=skill_package_id, connection_id=connection_id)

    db = SessionLocal()
    try:
        row = db.query(ExecutionRun).filter_by(id=run["id"]).one()
        row.operation_hash = "tampered-hash"
        db.commit()
    finally:
        db.close()

    execute_resp = client.post(f"/v1/runs/{run['id']}/execute", headers=headers)
    assert execute_resp.status_code == 409, execute_resp.text
    assert "altered" in execute_resp.json()["detail"]


def test_expired_permit_fails(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "exec-auth")
    monkeypatch.setattr(settings, "local_secret_key", Fernet.generate_key().decode())
    init_db()
    tenant_id = f"exec-tenant-{uuid4().hex}"
    headers = _identity(tenant_id)
    client = TestClient(app)

    skill_package_id = _build_approved_skill_package(client, headers, tenant_id)
    connection_id = _create_connection(client, headers)
    run = _plan_and_approve_run(client, headers, skill_package_id=skill_package_id, connection_id=connection_id)

    db = SessionLocal()
    try:
        row = db.query(ExecutionRun).filter_by(id=run["id"]).one()
        row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    finally:
        db.close()

    execute_resp = client.post(f"/v1/runs/{run['id']}/execute", headers=headers)
    assert execute_resp.status_code == 409, execute_resp.text
    assert "expired" in execute_resp.json()["detail"]


def test_reused_permit_fails(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "exec-auth")
    monkeypatch.setattr(settings, "local_secret_key", Fernet.generate_key().decode())
    init_db()
    tenant_id = f"exec-tenant-{uuid4().hex}"
    headers = _identity(tenant_id)
    client = TestClient(app)

    skill_package_id = _build_approved_skill_package(client, headers, tenant_id)
    connection_id = _create_connection(client, headers)
    run = _plan_and_approve_run(client, headers, skill_package_id=skill_package_id, connection_id=connection_id)

    first = client.post(f"/v1/runs/{run['id']}/execute", headers=headers)
    assert first.status_code == 200, first.text

    second = client.post(f"/v1/runs/{run['id']}/execute", headers=headers)
    assert second.status_code == 409, second.text
    assert "reused" in second.json()["detail"]


def test_revoked_permit_fails_verification(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "exec-auth")
    monkeypatch.setattr(settings, "local_secret_key", Fernet.generate_key().decode())
    init_db()
    tenant_id = f"exec-tenant-{uuid4().hex}"
    headers = _identity(tenant_id)
    client = TestClient(app)

    skill_package_id = _build_approved_skill_package(client, headers, tenant_id)
    connection_id = _create_connection(client, headers)
    run = _plan_and_approve_run(client, headers, skill_package_id=skill_package_id, connection_id=connection_id)

    revoke_resp = client.post(f"/v1/runs/{run['id']}/revoke", headers=headers)
    assert revoke_resp.status_code == 200, revoke_resp.text

    execute_resp = client.post(f"/v1/runs/{run['id']}/execute", headers=headers)
    assert execute_resp.status_code == 409, execute_resp.text
    assert "revoked" in execute_resp.json()["detail"]


def test_approval_reuse_fails(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "exec-auth")
    monkeypatch.setattr(settings, "local_secret_key", Fernet.generate_key().decode())
    init_db()
    tenant_id = f"exec-tenant-{uuid4().hex}"
    headers = _identity(tenant_id)
    client = TestClient(app)

    skill_package_id = _build_approved_skill_package(client, headers, tenant_id)
    connection_id = _create_connection(client, headers)

    approval_resp = client.post("/v1/approvals", headers=headers, json={"scope": "run:execute"})
    approval_id = approval_resp.json()["id"]

    plan1 = client.post(
        "/v1/runs/plan",
        headers=headers,
        json={
            "connection_id": connection_id,
            "skill_package_id": skill_package_id,
            "capability": "sales.order.read",
            "idempotency_key": f"idem-{uuid4().hex}",
        },
    )
    assert plan1.status_code == 201, plan1.text
    approve1 = client.post(
        f"/v1/runs/{plan1.json()['id']}/approve", headers=headers, json={"approval_ids": [approval_id]}
    )
    assert approve1.status_code == 200, approve1.text

    plan2 = client.post(
        "/v1/runs/plan",
        headers=headers,
        json={
            "connection_id": connection_id,
            "skill_package_id": skill_package_id,
            "capability": "sales.order.read",
            "idempotency_key": f"idem-{uuid4().hex}",
        },
    )
    assert plan2.status_code == 201, plan2.text
    approve2 = client.post(
        f"/v1/runs/{plan2.json()['id']}/approve", headers=headers, json={"approval_ids": [approval_id]}
    )
    assert approve2.status_code == 400, approve2.text
    assert "already_used" in approve2.json()["detail"]


def test_kill_switch_blocks_issuance_and_verification(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "exec-auth")
    monkeypatch.setattr(settings, "local_secret_key", Fernet.generate_key().decode())
    init_db()
    tenant_id = f"exec-tenant-{uuid4().hex}"
    headers = _identity(tenant_id)
    client = TestClient(app)

    skill_package_id = _build_approved_skill_package(client, headers, tenant_id)
    connection_id = _create_connection(client, headers)
    run = _plan_and_approve_run(client, headers, skill_package_id=skill_package_id, connection_id=connection_id)

    kill_resp = client.post("/v1/runs/kill-switch", headers=headers, json={"active": True})
    assert kill_resp.status_code == 200, kill_resp.text
    assert kill_resp.json()["active"] is True

    execute_resp = client.post(f"/v1/runs/{run['id']}/execute", headers=headers)
    assert execute_resp.status_code == 400, execute_resp.text
    assert "kill_switch" in execute_resp.json()["detail"]

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
    assert "kill_switch" in plan_resp.json()["detail"]


def test_run_api_is_tenant_scoped(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "exec-auth")
    monkeypatch.setattr(settings, "local_secret_key", Fernet.generate_key().decode())
    init_db()
    tenant_a = f"exec-tenant-a-{uuid4().hex}"
    tenant_b = f"exec-tenant-b-{uuid4().hex}"
    headers_a = _identity(tenant_a)
    headers_b = _identity(tenant_b)
    client = TestClient(app)

    skill_package_id = _build_approved_skill_package(client, headers_a, tenant_a)
    connection_id = _create_connection(client, headers_a)
    run = _plan_and_approve_run(client, headers_a, skill_package_id=skill_package_id, connection_id=connection_id)

    resp = client.get(f"/v1/runs/{run['id']}", headers=headers_b)
    assert resp.status_code == 404, resp.text


def test_idempotency_key_returns_same_run_for_same_operation_and_rejects_conflict(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "exec-auth")
    monkeypatch.setattr(settings, "local_secret_key", Fernet.generate_key().decode())
    init_db()
    tenant_id = f"exec-tenant-{uuid4().hex}"
    headers = _identity(tenant_id)
    client = TestClient(app)

    skill_package_id = _build_approved_skill_package(client, headers, tenant_id)
    connection_id = _create_connection(client, headers)
    idempotency_key = f"idem-{uuid4().hex}"

    body = {
        "connection_id": connection_id,
        "skill_package_id": skill_package_id,
        "capability": "sales.order.read",
        "idempotency_key": idempotency_key,
    }
    first = client.post("/v1/runs/plan", headers=headers, json=body)
    assert first.status_code == 201, first.text
    second = client.post("/v1/runs/plan", headers=headers, json=body)
    assert second.status_code == 201, second.text
    assert first.json()["id"] == second.json()["id"]

    # Same key, different underlying operation (different connection) -- must
    # not silently issue a second permit under the same key.
    other_connection_id = _create_connection(client, headers)
    conflicting = dict(body, connection_id=other_connection_id)
    conflict_resp = client.post("/v1/runs/plan", headers=headers, json=conflicting)
    assert conflict_resp.status_code == 400, conflict_resp.text
    assert "idempotency" in conflict_resp.json()["detail"]
