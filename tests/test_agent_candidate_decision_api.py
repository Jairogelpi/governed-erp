"""Sprint 36 — Agent Candidate Decision API integration tests."""
from __future__ import annotations

import json
import uuid

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)
BASE = "/v1/agent-builder/advisory"


def _make_db_version():
    """Create a candidate version directly in the shared DB."""
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
            name="api-decision-test",
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


def test_decision_404_unknown_version():
    r = client.post(
        f"{BASE}/candidates/nonexistent-id/decision",
        json={"decision": "approve", "actor": "reviewer"},
    )
    assert r.status_code == 404


def test_decision_history_404():
    r = client.get(f"{BASE}/candidates/nonexistent-id/decision-history")
    assert r.status_code == 404


def test_activation_gate_404():
    r = client.get(f"{BASE}/candidates/nonexistent-id/activation-gate")
    assert r.status_code == 404


def test_governance_summary_404():
    r = client.get(f"{BASE}/candidates/nonexistent-id/governance-summary")
    assert r.status_code == 404


def test_decision_audit_404():
    r = client.get(f"{BASE}/candidates/nonexistent-id/decision-audit")
    assert r.status_code == 404


def test_submit_approve_decision():
    vid = _make_db_version()
    r = client.post(
        f"{BASE}/candidates/{vid}/decision",
        json={"decision": "approve", "actor": "human_reviewer"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["decision"] == "approve"
    assert body["governance_status"] == "approved_pending_activation"
    assert body["can_execute"] is False
    assert body["can_approve"] is False
    assert body["is_advisory_only"] is True


def test_submit_invalid_decision_blocked():
    vid = _make_db_version()
    r = client.post(
        f"{BASE}/candidates/{vid}/decision",
        json={"decision": "activate", "actor": "reviewer"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["decision_id"] == ""
    assert body["blocking_reason"] != ""


def test_full_decision_pipeline():
    vid = _make_db_version()

    # 1. Submit decision
    r = client.post(
        f"{BASE}/candidates/{vid}/decision",
        json={"decision": "approve", "actor": "governance_team"},
    )
    assert r.status_code == 200
    assert r.json()["governance_status"] == "approved_pending_activation"

    # 2. Decision history
    r = client.get(f"{BASE}/candidates/{vid}/decision-history")
    assert r.status_code == 200
    body = r.json()
    assert body["decision_count"] == 1
    assert body["latest_decision"] == "approve"
    assert body["can_execute"] is False

    # 3. Activation gate
    r = client.get(f"{BASE}/candidates/{vid}/activation-gate")
    assert r.status_code == 200
    body = r.json()
    assert body["gate_passed"] is True
    assert body["activation_allowed"] is False  # never activates
    assert body["can_execute"] is False
    assert body["can_approve"] is False

    # 4. Governance summary
    r = client.get(f"{BASE}/candidates/{vid}/governance-summary")
    assert r.status_code == 200
    body = r.json()
    assert body["governance_status"] == "approved_pending_activation"
    assert body["can_execute"] is False
    assert body["is_advisory_only"] is True

    # 5. Decision audit
    r = client.get(f"{BASE}/candidates/{vid}/decision-audit")
    assert r.status_code == 200
    body = r.json()
    assert body["event_count"] >= 2  # decision + gate
    assert body["can_execute"] is False
    assert body["is_advisory_only"] is True
