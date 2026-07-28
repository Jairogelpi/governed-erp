"""Sprint 35 — Agent Candidate Approval API integration tests."""
from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)

BASE = "/v1/agent-builder/advisory"


def test_promotion_readiness_404():
    r = client.get(f"{BASE}/candidates/nonexistent-id/promotion-readiness")
    assert r.status_code == 404


def test_evidence_completeness_404():
    r = client.get(f"{BASE}/candidates/nonexistent-id/evidence-completeness")
    assert r.status_code == 404


def test_risk_summary_404():
    r = client.get(f"{BASE}/candidates/nonexistent-id/risk-summary")
    assert r.status_code == 404


def test_approval_packet_404():
    r = client.post(f"{BASE}/candidates/nonexistent-id/approval-packet")
    assert r.status_code == 404


def test_approval_request_404():
    r = client.post(f"{BASE}/candidates/nonexistent-id/approval-request")
    assert r.status_code == 404


def test_approval_audit_404():
    r = client.get(f"{BASE}/candidates/nonexistent-id/approval-audit")
    assert r.status_code == 404


def test_promotion_readiness_schema():
    """If a version exists, response has required safety fields."""
    import json
    import uuid
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
            name="api-test-candidate",
            status="candidate",
            steps_json="[]",
            guard_names_json="[]",
            runtime_type="agent_advisory",
            promotion_readiness_json=json.dumps({
                "source": "agent_handoff_packet",
                "readiness_score": 85,
                "evidence_items": [],
            }),
        )
        db.add(rec)
        db.commit()

        r = client.get(f"{BASE}/candidates/{vid}/promotion-readiness")
        assert r.status_code == 200
        body = r.json()
        assert body["can_execute"] is False
        assert body["can_approve"] is False
        assert body["is_advisory_only"] is True
        assert "blocking_items" in body
        assert "advisory_items" in body
    finally:
        db.close()


def test_full_approval_pipeline():
    """End-to-end: readiness → completeness → risk → packet → request → audit."""
    import json
    import uuid
    from erpguard.db.models import UISkillVersionRecord
    from erpguard.db.session import SessionLocal, init_db
    from erpguard.product.agent_candidate_evidence_completeness import _REQUIRED_EVIDENCE_SOURCES

    init_db()
    db = SessionLocal()
    try:
        vid = f"ver_{uuid.uuid4().hex[:16]}"
        promotion_readiness = {
            "source": "agent_handoff_packet",
            "readiness_score": 85,
            "evidence_items": [
                {"source": s, "status": "passed", "label": s}
                for s in _REQUIRED_EVIDENCE_SOURCES
            ],
        }
        rec = UISkillVersionRecord(
            id=vid,
            skill_id=f"skill_{uuid.uuid4().hex[:8]}",
            compiled_skill_id=f"comp_{uuid.uuid4().hex[:8]}",
            name="pipeline-test-candidate",
            status="candidate",
            steps_json="[]",
            guard_names_json=json.dumps(["no_generic_writes"]),
            runtime_type="agent_advisory",
            promotion_readiness_json=json.dumps(promotion_readiness),
        )
        db.add(rec)
        db.commit()
    finally:
        db.close()

    r = client.get(f"{BASE}/candidates/{vid}/promotion-readiness")
    assert r.status_code == 200
    assert r.json()["can_execute"] is False
    assert r.json()["is_advisory_only"] is True

    r = client.get(f"{BASE}/candidates/{vid}/evidence-completeness")
    assert r.status_code == 200
    assert r.json()["can_execute"] is False

    r = client.get(f"{BASE}/candidates/{vid}/risk-summary")
    assert r.status_code == 200
    assert r.json()["can_execute"] is False

    r = client.post(f"{BASE}/candidates/{vid}/approval-packet")
    assert r.status_code == 200
    body = r.json()
    assert body["can_execute"] is False
    assert body["can_approve"] is False
    assert body["is_advisory_only"] is True
    approval_packet_id = body["approval_packet_id"]
    assert approval_packet_id != ""

    r = client.post(f"{BASE}/candidates/{vid}/approval-request")
    assert r.status_code == 200
    body = r.json()
    assert body["bridge_complete"] is True
    assert body["can_execute"] is False
    assert body["can_approve"] is False

    r = client.get(f"{BASE}/candidates/{vid}/approval-audit")
    assert r.status_code == 200
    body = r.json()
    assert body["event_count"] >= 3
    assert body["approval_packet_id"] == approval_packet_id
    assert body["can_execute"] is False
    assert body["is_advisory_only"] is True
