"""Sprint 38 — Agent Candidate Activation API integration tests."""
from __future__ import annotations

import uuid

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
            name="api-activation-test",
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


def _full_prereqs(vid):
    client.post(f"{BASE}/candidates/{vid}/decision",
                json={"decision": "approve", "actor": "reviewer"})
    client.get(f"{BASE}/candidates/{vid}/activation-gate")
    client.post(f"{BASE}/candidates/{vid}/activation-request",
                json={"requested_by": "operator"})
    client.get(f"{BASE}/candidates/{vid}/activation-request/final-gate")


def test_eligibility_404():
    r = client.get(f"{BASE}/candidates/nonexistent-id/activation/eligibility")
    assert r.status_code == 404


def test_activate_404():
    r = client.post(f"{BASE}/candidates/nonexistent-id/activation/activate",
                    json={"actor": "operator"})
    assert r.status_code == 404


def test_status_404():
    r = client.get(f"{BASE}/candidates/nonexistent-id/activation/status")
    assert r.status_code == 404


def test_audit_404():
    r = client.get(f"{BASE}/candidates/nonexistent-id/activation/audit")
    assert r.status_code == 404


def test_summary_404():
    r = client.get(f"{BASE}/candidates/nonexistent-id/activation/summary")
    assert r.status_code == 404


def test_eligibility_not_eligible_without_prereqs():
    vid = _make_db_version()
    r = client.get(f"{BASE}/candidates/{vid}/activation/eligibility")
    assert r.status_code == 200
    body = r.json()
    assert body["eligible"] is False
    assert body["can_execute"] is False


def test_full_activation_pipeline():
    vid = _make_db_version()
    _full_prereqs(vid)

    # 1. Eligibility
    r = client.get(f"{BASE}/candidates/{vid}/activation/eligibility")
    assert r.status_code == 200
    assert r.json()["eligible"] is True

    # 2. Activate
    r = client.post(f"{BASE}/candidates/{vid}/activation/activate",
                    json={"actor": "governance_operator"})
    assert r.status_code == 200
    body = r.json()
    assert body["activated"] is True
    assert body["version_status"] == "active"
    assert body["is_active"] is True
    assert body["is_executed"] is False
    assert body["can_execute"] is False
    assert body["is_advisory_only"] is True

    # 3. Status
    r = client.get(f"{BASE}/candidates/{vid}/activation/status")
    assert r.status_code == 200
    body = r.json()
    assert body["version_status"] == "active"
    assert body["is_active"] is True
    assert body["is_executed"] is False

    # 4. Audit
    r = client.get(f"{BASE}/candidates/{vid}/activation/audit")
    assert r.status_code == 200
    body = r.json()
    assert body["event_count"] >= 1
    assert body["can_execute"] is False

    # 5. Summary
    r = client.get(f"{BASE}/candidates/{vid}/activation/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["governance_status"] == "active_governed"
    assert body["is_executed"] is False
    assert body["is_advisory_only"] is True
