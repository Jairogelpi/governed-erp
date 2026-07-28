"""Sprint 40 — Semantic Skill Discovery API integration tests."""
from __future__ import annotations

import json
import uuid

from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)
BASE = "/v1/agent-builder/discovery"


def _make_active_version(name="formula-review", guard_names=None):
    from erpguard.db.models import UISkillVersionRecord
    from erpguard.db.session import SessionLocal, init_db
    from erpguard.product.agent_candidate_activation_gate_bridge import evaluate_activation_gate
    from erpguard.product.agent_candidate_activation_request import create_activation_request
    from erpguard.product.agent_candidate_activation_service import activate_candidate_version
    from erpguard.product.agent_candidate_final_activation_gate import evaluate_final_activation_gate
    from erpguard.product.agent_candidate_human_decision import record_human_decision

    init_db()
    db = SessionLocal()
    try:
        vid = f"ver_{uuid.uuid4().hex[:16]}"
        guard_names = guard_names or ["formula_guard"]
        rec = UISkillVersionRecord(
            id=vid,
            skill_id=f"skill_{uuid.uuid4().hex[:8]}",
            compiled_skill_id=f"comp_{uuid.uuid4().hex[:8]}",
            name=name,
            status="candidate",
            steps_json='[{"type": "read", "description": "Read order formula"}]',
            guard_names_json=json.dumps(guard_names),
            runtime_type="agent_advisory",
            promotion_readiness_json="{}",
        )
        db.add(rec)
        db.commit()
        record_human_decision(vid, "approve", "reviewer", session=db)
        evaluate_activation_gate(vid, db)
        create_activation_request(vid, "operator", session=db)
        evaluate_final_activation_gate(vid, db)
        activate_candidate_version(vid, "operator", session=db)
        return vid
    finally:
        db.close()


def test_search_returns_200(client=client):
    r = client.post(f"{BASE}/search", json={"query": "formula"})
    assert r.status_code == 200
    data = r.json()
    assert "results" in data
    assert data["will_execute"] is False
    assert data["is_advisory_only"] is True


def test_search_finds_matching_skill():
    _make_active_version(name="formula-review-sprint40")
    r = client.post(f"{BASE}/search", json={"query": "formula review"})
    assert r.status_code == 200
    data = r.json()
    assert data["total_found"] >= 1


def test_similar_skills_returns_200():
    vid = _make_active_version(name="similar-ref")
    r = client.post(f"{BASE}/similar-skills", json={"version_id": vid})
    assert r.status_code == 200
    data = r.json()
    assert data["reference_version_id"] == vid
    assert data["will_execute"] is False
    assert data["is_advisory_only"] is True


def test_similar_skills_not_found():
    r = client.post(f"{BASE}/similar-skills", json={"version_id": "nonexistent-id"})
    assert r.status_code == 200
    assert r.json()["blocking_reason"] == "version_not_found"


def test_lifecycle_summary_returns_200():
    vid = _make_active_version(name="lifecycle-test")
    r = client.get(f"{BASE}/skills/{vid}/lifecycle-summary")
    assert r.status_code == 200
    data = r.json()
    assert data["governance_status"] == "active_governed"
    assert data["will_execute"] is False
    assert data["is_advisory_only"] is True


def test_lifecycle_summary_unknown_version():
    r = client.get(f"{BASE}/skills/nonexistent-id/lifecycle-summary")
    assert r.status_code == 200
    assert r.json()["blocking_reason"] == "version_not_found"


def test_governance_gaps_returns_200():
    vid = _make_active_version(name="gaps-test")
    r = client.get(f"{BASE}/skills/{vid}/governance-gaps")
    assert r.status_code == 200
    data = r.json()
    assert "gaps" in data
    assert data["will_execute"] is False
    assert data["is_advisory_only"] is True


def test_recommendations_returns_200():
    vid = _make_active_version(name="recs-test")
    r = client.get(f"{BASE}/skills/{vid}/recommendations")
    assert r.status_code == 200
    data = r.json()
    assert "recommendations" in data
    assert data["will_execute"] is False
    assert data["is_advisory_only"] is True


def test_reuse_suggestions_returns_200():
    _make_active_version(name="reuse-target")
    r = client.post(f"{BASE}/reuse-suggestions", json={"query": "formula"})
    assert r.status_code == 200
    data = r.json()
    assert "suggestions" in data
    assert data["will_execute"] is False
    assert data["is_advisory_only"] is True


def test_safety_invariants_all_endpoints():
    vid = _make_active_version(name="safety-check")
    responses = [
        client.post(f"{BASE}/search", json={"query": "safety"}).json(),
        client.post(f"{BASE}/similar-skills", json={"version_id": vid}).json(),
        client.get(f"{BASE}/skills/{vid}/lifecycle-summary").json(),
        client.get(f"{BASE}/skills/{vid}/governance-gaps").json(),
        client.get(f"{BASE}/skills/{vid}/recommendations").json(),
        client.post(f"{BASE}/reuse-suggestions", json={"query": "safety"}).json(),
    ]
    for resp in responses:
        assert resp.get("will_execute") is False, f"will_execute not False: {resp}"
        assert resp.get("can_execute") is False, f"can_execute not False: {resp}"
        assert resp.get("is_advisory_only") is True, f"is_advisory_only not True: {resp}"
