from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.config import settings
from erpguard.db.model_packages.identity import IdentityMembership, IdentityUser
from erpguard.db.session import SessionLocal, init_db
from erpguard.domain.events.ocel_service import OcelEventService
from erpguard.domain.identity.auth import issue_token
from erpguard.domain.processes.candidates import (
    CandidateEvidenceNotFound,
    CandidateService,
    CandidateValidationError,
)
from erpguard.domain.processes.registry import ProcessRegistry


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "policies" / "processes" / "quote_to_order_v1.yaml"


def _document() -> dict:
    return {
        "ocel:objects": {"so-1": {"ocel:type": "sale_order", "ocel:ovmap": {}}},
        "ocel:events": {
            "e-1": {
                "ocel:activity": "sales.quote.created",
                "ocel:timestamp": "2026-01-01T00:00:00Z",
                "ocel:omap": ["so-1"],
                "ocel:vmap": {},
            },
            "e-2": {
                "ocel:activity": "sales.quote.reviewed",
                "ocel:timestamp": "2026-01-01T00:01:00Z",
                "ocel:omap": ["so-1"],
                "ocel:vmap": {},
            },
        },
    }


def _register_process(db, suffix: str) -> str:
    process_key = f"candidate_process_{suffix}"
    base = FIXTURE.read_text(encoding="utf-8").replace("quote_to_order", process_key)
    ProcessRegistry(db).register_yaml(base)
    return process_key


def _seed_candidate_data(db, tenant_id: str, process_key: str) -> None:
    OcelEventService(db).import_ocel(tenant_id=tenant_id, document=_document(), source="test")
    base = FIXTURE.read_text(encoding="utf-8").replace("quote_to_order", process_key)
    if ProcessRegistry(db).get(process_key, "1.0.0") is None:
        ProcessRegistry(db).register_yaml(base)


def _create_candidate(db, *, tenant_id: str, process_key: str, candidate_version: str = "2.0.0"):
    return CandidateService(db).create_draft(
        tenant_id=tenant_id,
        process_key=process_key,
        base_version="1.0.0",
        candidate_version=candidate_version,
        changes={
            "add_event": {"name": "sales.quote.approved", "object": "quotation"},
        },
        evidence_refs=["case:so-1", "evt:evt_%s_e-1" % tenant_id],
        created_by="user-1",
        proposal={"reason": "structured_proposal"},
    )


def test_candidate_is_immutable_after_submission_and_keeps_evidence():
    init_db()
    db = SessionLocal()
    tenant_id = f"candidate-tenant-{uuid4().hex}"
    process_key = _register_process(db, uuid4().hex)
    _seed_candidate_data(db, tenant_id, process_key)
    try:
        candidate = _create_candidate(db, tenant_id=tenant_id, process_key=process_key)
        submitted = CandidateService(db).submit(tenant_id=tenant_id, candidate_id=candidate.id)
        assert submitted.status == "submitted"
        assert "structured_proposal" in submitted.changes_json
        submitted.changes_json = "{}"
        with pytest.raises(ValueError, match="submitted_candidate_immutable"):
            db.commit()
        db.rollback()
    finally:
        db.close()


def test_candidate_requires_valid_base_and_patch():
    init_db()
    db = SessionLocal()
    try:
        with pytest.raises(CandidateValidationError, match="base_process_version_not_found"):
            CandidateService(db).create_draft(
                tenant_id="tenant-a",
                process_key="missing",
                base_version="1.0.0",
                candidate_version="2.0.0",
                changes={"arbitrary_code": "raise RuntimeError()"},
                evidence_refs=["case:missing"],
                created_by="user-1",
            )
    finally:
        db.close()


def test_cross_tenant_candidate_access_is_not_found_and_version_is_local():
    init_db()
    db = SessionLocal()
    process_key = _register_process(db, uuid4().hex)
    tenant_a = f"tenant-a-{uuid4().hex}"
    tenant_b = f"tenant-b-{uuid4().hex}"
    _seed_candidate_data(db, tenant_a, process_key)
    _seed_candidate_data(db, tenant_b, process_key)
    try:
        candidate_a = _create_candidate(db, tenant_id=tenant_a, process_key=process_key)
        service = CandidateService(db)
        with pytest.raises(KeyError):
            service.get(tenant_id=tenant_b, candidate_id=candidate_a.id)
        with pytest.raises(KeyError):
            service.submit(tenant_id=tenant_b, candidate_id=candidate_a.id)
        candidate_b = _create_candidate(db, tenant_id=tenant_b, process_key=process_key)
        assert candidate_b.candidate_version == candidate_a.candidate_version
        assert candidate_b.tenant_id == tenant_b
    finally:
        db.close()


def test_evidence_must_exist_and_be_related_to_the_base():
    init_db()
    db = SessionLocal()
    tenant_id = f"evidence-tenant-{uuid4().hex}"
    process_key = _register_process(db, uuid4().hex)
    try:
        with pytest.raises(CandidateEvidenceNotFound, match="candidate_evidence_not_found"):
            CandidateService(db).create_draft(
                tenant_id=tenant_id,
                process_key=process_key,
                base_version="1.0.0",
                candidate_version="2.0.0",
                changes={"add_event": {"name": "sales.quote.approved", "object": "quotation"}},
                evidence_refs=["case:invented"],
                created_by="user-1",
            )
        _seed_candidate_data(db, tenant_id, process_key)
        with pytest.raises(CandidateValidationError, match="invalid_candidate_patch"):
            CandidateService(db).create_draft(
                tenant_id=tenant_id,
                process_key=process_key,
                base_version="1.0.0",
                candidate_version="2.1.0",
                changes={"raw_odoo_method": "action_confirm"},
                evidence_refs=["case:so-1"],
                created_by="user-1",
            )
    finally:
        db.close()


def test_candidate_digests_are_stable_for_same_base_patch_and_result():
    init_db()
    db = SessionLocal()
    process_key = _register_process(db, uuid4().hex)
    tenant_a = f"digest-a-{uuid4().hex}"
    tenant_b = f"digest-b-{uuid4().hex}"
    _seed_candidate_data(db, tenant_a, process_key)
    _seed_candidate_data(db, tenant_b, process_key)
    try:
        first = _create_candidate(db, tenant_id=tenant_a, process_key=process_key)
        second = _create_candidate(db, tenant_id=tenant_b, process_key=process_key)
        assert first.base_definition_digest == second.base_definition_digest
        assert first.patch_digest == second.patch_digest
        assert first.candidate_definition_digest == second.candidate_definition_digest
        assert first.validation_status == second.validation_status == "valid"
    finally:
        db.close()


def _identity(tenant_id: str, role: str = "admin") -> tuple[str, dict[str, str]]:
    suffix = uuid4().hex
    user_id = f"candidate-user-{suffix}"
    db = SessionLocal()
    db.add(IdentityUser(id=user_id, email=f"{suffix}@example.test", display_name="Candidate user"))
    db.add(
        IdentityMembership(
            id=f"candidate-membership-{suffix}",
            tenant_id=tenant_id,
            user_id=user_id,
            role_name=role,
            status="active",
        )
    )
    db.commit()
    db.close()
    return user_id, {"Authorization": f"Bearer {issue_token(user_id, tenant_id, 'candidate-auth')}"}


def test_candidate_api_is_protected_and_tenant_scoped(monkeypatch):
    init_db()
    monkeypatch.setattr(settings, "auth_secret", "candidate-auth")
    db = SessionLocal()
    process_key = _register_process(db, uuid4().hex)
    tenant_a = f"api-tenant-a-{uuid4().hex}"
    tenant_b = f"api-tenant-b-{uuid4().hex}"
    _seed_candidate_data(db, tenant_a, process_key)
    _seed_candidate_data(db, tenant_b, process_key)
    db.close()
    _, headers_a = _identity(tenant_a)
    _, headers_b = _identity(tenant_b)
    client = TestClient(app)
    payload = {
        "process_key": process_key,
        "base_version": "1.0.0",
        "candidate_version": "2.0.0",
        "changes": {"add_event": {"name": "sales.quote.approved", "object": "quotation"}},
        "evidence_refs": ["case:so-1"],
        "structured_proposal": {"reason": "tenant-scoped"},
    }
    created = client.post("/v1/process-candidates", headers=headers_a, json=payload)
    assert created.status_code == 201
    candidate_id = created.json()["id"]
    assert client.get(f"/v1/process-candidates/{candidate_id}", headers=headers_b).status_code == 404
    assert client.post(f"/v1/process-candidates/{candidate_id}/submit", headers=headers_b).status_code == 404
    own = client.post("/v1/process-candidates", headers=headers_b, json=payload)
    assert own.status_code == 201
    assert own.json()["tenant_id"] == tenant_b
