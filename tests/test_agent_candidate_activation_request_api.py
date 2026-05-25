"""Sprint 37 — Agent Candidate Activation Request API integration tests."""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)
BASE = "/v1/agent-builder/advisory"


def _make_db_version():
    from erpguard.db.models import UISkillVersionRecord
    from erpguard.db.session import SessionLocal, init_db
    init_db()
    db = SessionLocal()
    try:
        vid = f"ver_{uuid.uuid4().hex[:16]}"
        rec = UISkillVersionRecord(
            id=vid,
            skill_id=f"skill_{uuid.uuid4().hex[:8]}",
            compiled_skill_id=f"comp_{uuid.uuid4().hex[:8]}",
            name="api-activation-request-test",
            status="candidate",
            steps_json="[]",
            guard_names_json="[]",
            runtime_type="agent_advisory",
            promotion_readiness_json="{}",
        )
        db.add(rec)
        db.commit()
        return vid
    finally:
        db.close()


def _approve_and_gate(vid):
    client.post(
        f"{BASE}/candidates/{vid}/decision",
        json={"decision": "approve", "actor": "reviewer"},
    )
    client.get(f"{BASE}/candidates/{vid}/activation-gate")


def test_eligibility_404_unknown():
    r = client.get(f"{BASE}/candidates/nonexistent-id/activation-request/eligibility")
    assert r.status_code == 404


def test_activation_request_404_unknown():
    r = client.post(
        f"{BASE}/candidates/nonexistent-id/activation-request",
        json={"requested_by": "operator"},
    )
    assert r.status_code == 404


def test_status_404_unknown():
    r = client.get(f"{BASE}/candidates/nonexistent-id/activation-request/status")
    assert r.status_code == 404


def test_final_gate_404_unknown():
    r = client.get(f"{BASE}/candidates/nonexistent-id/activation-request/final-gate")
    assert r.status_code == 404


def test_audit_404_unknown():
    r = client.get(f"{BASE}/candidates/nonexistent-id/activation-request/audit")
    assert r.status_code == 404


def test_eligibility_not_eligible_without_approve():
    vid = _make_db_version()
    r = client.get(f"{BASE}/candidates/{vid}/activation-request/eligibility")
    assert r.status_code == 200
    body = r.json()
    assert body["eligible"] is False
    assert body["can_execute"] is False


def test_full_activation_request_pipeline():
    vid = _make_db_version()
    _approve_and_gate(vid)

    # 1. Eligibility
    r = client.get(f"{BASE}/candidates/{vid}/activation-request/eligibility")
    assert r.status_code == 200
    assert r.json()["eligible"] is True

    # 2. Create request
    r = client.post(
        f"{BASE}/candidates/{vid}/activation-request",
        json={"requested_by": "governance_operator", "rationale": "approved by committee"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["request_status"] == "pending_review"
    assert body["request_id"] != ""
    assert body["can_execute"] is False
    assert body["is_advisory_only"] is True

    # 3. Status
    r = client.get(f"{BASE}/candidates/{vid}/activation-request/status")
    assert r.status_code == 200
    body = r.json()
    assert body["request_status"] == "pending_review"
    assert body["can_execute"] is False

    # 4. Final gate
    r = client.get(f"{BASE}/candidates/{vid}/activation-request/final-gate")
    assert r.status_code == 200
    body = r.json()
    assert body["gate_passed"] is True
    assert body["activation_allowed"] is False
    assert body["can_execute"] is False

    # 5. Audit
    r = client.get(f"{BASE}/candidates/{vid}/activation-request/audit")
    assert r.status_code == 200
    body = r.json()
    assert body["event_count"] >= 2
    assert body["can_execute"] is False
    assert body["is_advisory_only"] is True
