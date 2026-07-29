"""Phase 14 -- Process-to-Skill compiler v2 (master spec section 18).

End-to-end through the public API: candidate -> submit -> replay -> freeze
-> proof -> compile -> approve. Only the two real, checkable exit criteria
this codebase can honestly claim are exercised precisely: raw/undeclared
native methods rejected, missing/unacceptable proof rejected. See
`erpguard/domain/skills/compiler.py`'s module docstring for exactly which
of spec 18.3's other checks are real vs. structural placeholders.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.config import settings
from erpguard.db.model_packages.identity import IdentityMembership, IdentityUser
from erpguard.db.model_packages.skill_package import SkillPackage
from erpguard.db.session import SessionLocal, init_db
from erpguard.domain.events.fake_generator import build_fake_quote_to_order_ocel
from erpguard.domain.events.ocel_service import OcelEventService
from erpguard.domain.identity.auth import issue_token
from erpguard.domain.processes.registry import ProcessRegistry


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "policies" / "processes" / "quote_to_order_v1.yaml"


def _identity(tenant_id: str, role: str = "admin") -> dict[str, str]:
    suffix = uuid4().hex
    user_id = f"skill-user-{suffix}"
    db = SessionLocal()
    db.add(IdentityUser(id=user_id, email=f"{suffix}@example.test", display_name="Skill user"))
    db.add(
        IdentityMembership(
            id=f"skill-membership-{suffix}",
            tenant_id=tenant_id,
            user_id=user_id,
            role_name=role,
            status="active",
        )
    )
    db.commit()
    db.close()
    return {"Authorization": f"Bearer {issue_token(user_id, tenant_id, 'skill-auth')}"}


def _register_process(suffix: str) -> str:
    process_key = f"skill_process_{suffix}"
    db = SessionLocal()
    try:
        base = FIXTURE.read_text(encoding="utf-8").replace("quote_to_order", process_key)
        ProcessRegistry(db).register_yaml(base)
    finally:
        db.close()
    return process_key


def _register_process_version(process_key: str, version: str) -> None:
    """Historical replay loads a version via ProcessRegistry -- submitting a
    candidate doesn't itself register a process version, so tests that
    replay a "candidate" version must register it explicitly, same fixture
    content, just a different version string."""

    db = SessionLocal()
    try:
        base = FIXTURE.read_text(encoding="utf-8").replace("quote_to_order", process_key)
        base = base.replace("version: 1.0.0", f"version: {version}")
        ProcessRegistry(db).register_yaml(base)
    finally:
        db.close()


def _seed_case(tenant_id: str) -> str:
    object_key = f"so-skill-{uuid4().hex[:8]}"
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


def _build_submitted_candidate_with_proof(client: TestClient, headers: dict, tenant_id: str) -> tuple[str, str, str]:
    """Returns (candidate_id, process_key, candidate_version)."""

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

    submit_resp = client.post(f"/v1/process-candidates/{candidate_id}/submit", headers=headers)
    assert submit_resp.status_code == 200, submit_resp.text

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
    assert proof_resp.json()["recommendation"] == "eligible_for_shadow", proof_resp.json()

    return candidate_id, process_key, "1.1.0"


def test_compile_submitted_candidate_with_acceptable_proof(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "skill-auth")
    init_db()
    tenant_id = f"skill-tenant-{uuid4().hex}"
    headers = _identity(tenant_id)
    client = TestClient(app)

    candidate_id, process_key, version = _build_submitted_candidate_with_proof(client, headers, tenant_id)

    compile_resp = client.post(
        f"/v1/process-candidates/{candidate_id}/compile",
        headers=headers,
        json={"connector_id": "fake", "workflow_steps": []},
    )
    assert compile_resp.status_code == 201, compile_resp.text
    package = compile_resp.json()
    assert package["status"] == "compiled"
    assert package["package_hash"]
    checks = {c["name"]: c["status"] for c in package["validation_result"]["checks"]}
    assert checks["proof_acceptable"] == "passed"
    assert checks["capability_existence"] == "passed"
    assert checks["policy_references_resolve"] == "passed"

    get_resp = client.get(f"/v1/skills/{package['id']}/versions/{version}", headers=headers)
    assert get_resp.status_code == 200, get_resp.text
    assert get_resp.json()["package_hash"] == package["package_hash"]


def test_compile_rejects_draft_candidate(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "skill-auth")
    init_db()
    tenant_id = f"skill-tenant-{uuid4().hex}"
    headers = _identity(tenant_id)
    client = TestClient(app)
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

    compile_resp = client.post(
        f"/v1/process-candidates/{candidate_id}/compile",
        headers=headers,
        json={"connector_id": "fake", "workflow_steps": []},
    )
    assert compile_resp.status_code == 400, compile_resp.text
    assert "not_submitted" in compile_resp.json()["detail"]


def test_compile_rejects_when_no_acceptable_proof_exists(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "skill-auth")
    init_db()
    tenant_id = f"skill-tenant-{uuid4().hex}"
    headers = _identity(tenant_id)
    client = TestClient(app)
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

    compile_resp = client.post(
        f"/v1/process-candidates/{candidate_id}/compile",
        headers=headers,
        json={"connector_id": "fake", "workflow_steps": []},
    )
    assert compile_resp.status_code == 400, compile_resp.text
    assert "no_acceptable_proof" in compile_resp.json()["detail"]


def test_compile_rejects_undeclared_connector_capability(monkeypatch):
    """The 'raw native methods rejected' exit criterion, isolated via a
    direct service call so it doesn't depend on the full candidate/proof
    setup."""

    monkeypatch.setattr(settings, "auth_secret", "skill-auth")
    init_db()
    from erpguard.connectors.fake.plugin import FakeConnector
    from erpguard.domain.processes.models import ProcessDefinitionDocument
    from erpguard.domain.skills.compiler import SkillCompilationError, compile_skill_package
    from erpguard.domain.skills.types import WorkflowStep

    document = ProcessDefinitionDocument.model_validate(json.loads(FIXTURE_JSON))
    connector = FakeConnector()

    with pytest.raises(SkillCompilationError, match="undeclared_connector_capability"):
        compile_skill_package(
            process_key="quote_to_order",
            candidate_version="1.1.0",
            candidate_definition=document,
            workflow_steps=[WorkflowStep(step_name="raw", capability="odoo.raw_execute_kw")],
            connector=connector,
            proof_id="proof_fake",
            proof_recommendation="eligible_for_shadow",
        )


FIXTURE_JSON = json.dumps(
    {
        "process_key": "quote_to_order",
        "version": "1.0.0",
        "name": "Quote-to-Order baseline",
        "objects": [{"name": "sales_order", "external_types": ["sale.order"]}],
        "events": [{"name": "sales.quote.reviewed", "object": "sales_order"}],
        "decisions": [{"name": "formula_guard", "applies_to": "sales.quote.reviewed", "outcomes": ["allow", "block"]}],
        "policies": [{"name": "no_unapproved_confirmation", "decision": "formula_guard", "blocking": True}],
        "metrics": [],
        "fixtures": [],
    }
)


def test_package_hash_is_reproducible(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "skill-auth")
    from erpguard.connectors.fake.plugin import FakeConnector
    from erpguard.domain.processes.models import ProcessDefinitionDocument
    from erpguard.domain.skills.compiler import compile_skill_package

    document = ProcessDefinitionDocument.model_validate(json.loads(FIXTURE_JSON))
    connector = FakeConnector()

    _, _, hash1 = compile_skill_package(
        process_key="quote_to_order",
        candidate_version="1.1.0",
        candidate_definition=document,
        workflow_steps=[],
        connector=connector,
        proof_id="proof_fake",
        proof_recommendation="eligible_for_shadow",
    )
    _, _, hash2 = compile_skill_package(
        process_key="quote_to_order",
        candidate_version="1.1.0",
        candidate_definition=document,
        workflow_steps=[],
        connector=connector,
        proof_id="proof_fake",
        proof_recommendation="eligible_for_shadow",
    )
    assert hash1 == hash2


def test_approved_skill_package_is_immutable(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "skill-auth")
    init_db()
    tenant_id = f"skill-tenant-{uuid4().hex}"
    headers = _identity(tenant_id)
    client = TestClient(app)

    candidate_id, process_key, version = _build_submitted_candidate_with_proof(client, headers, tenant_id)
    compile_resp = client.post(
        f"/v1/process-candidates/{candidate_id}/compile",
        headers=headers,
        json={"connector_id": "fake", "workflow_steps": []},
    )
    skill_id = compile_resp.json()["id"]

    approve_resp = client.post(f"/v1/skills/{skill_id}/versions/{version}/approve", headers=headers)
    assert approve_resp.status_code == 200, approve_resp.text
    assert approve_resp.json()["status"] == "approved"

    second_approve = client.post(f"/v1/skills/{skill_id}/versions/{version}/approve", headers=headers)
    assert second_approve.status_code == 400, second_approve.text

    db = SessionLocal()
    try:
        row = db.query(SkillPackage).filter_by(tenant_id=tenant_id, id=skill_id).one()
        row.connector_id = "tampered"
        with pytest.raises(ValueError, match="approved_skill_package_immutable"):
            db.commit()
        db.rollback()
    finally:
        db.close()


def test_skill_package_api_is_tenant_scoped(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "skill-auth")
    init_db()
    tenant_a = f"skill-tenant-a-{uuid4().hex}"
    tenant_b = f"skill-tenant-b-{uuid4().hex}"
    headers_a = _identity(tenant_a)
    headers_b = _identity(tenant_b)
    client = TestClient(app)

    candidate_id, process_key, version = _build_submitted_candidate_with_proof(client, headers_a, tenant_a)
    compile_resp = client.post(
        f"/v1/process-candidates/{candidate_id}/compile",
        headers=headers_a,
        json={"connector_id": "fake", "workflow_steps": []},
    )
    skill_id = compile_resp.json()["id"]

    assert client.get(f"/v1/skills/{skill_id}/versions/{version}", headers=headers_a).status_code == 200
    assert client.get(f"/v1/skills/{skill_id}/versions/{version}", headers=headers_b).status_code == 404
