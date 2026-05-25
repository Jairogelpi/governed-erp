"""Sprint 39 — Agent Skill Run Preview API integration tests."""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)
BASE = "/v1/agent-builder/advisory"


def _make_and_activate_version():
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
        rec = UISkillVersionRecord(
            id=vid,
            skill_id=f"skill_{uuid.uuid4().hex[:8]}",
            compiled_skill_id=f"comp_{uuid.uuid4().hex[:8]}",
            name="api-preview-test",
            status="candidate",
            steps_json="[]",
            guard_names_json="[]",
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


def test_eligibility_not_found():
    r = client.get(f"{BASE}/candidates/nonexistent-id/run-preview/eligibility")
    assert r.status_code == 404


def test_plan_not_found():
    r = client.post(f"{BASE}/candidates/nonexistent-id/run-preview/plan")
    assert r.status_code == 404


def test_execution_gate_not_found():
    r = client.get(f"{BASE}/candidates/nonexistent-id/run-preview/execution-gate")
    assert r.status_code == 404


def test_run_preview_not_found():
    r = client.post(f"{BASE}/candidates/nonexistent-id/run-preview")
    assert r.status_code == 404


def test_audit_not_found():
    r = client.get(f"{BASE}/candidates/nonexistent-id/run-preview/audit")
    assert r.status_code == 404


def test_eligibility_active_version():
    vid = _make_and_activate_version()
    r = client.get(f"{BASE}/candidates/{vid}/run-preview/eligibility")
    assert r.status_code == 200
    data = r.json()
    assert data["eligible"] is True
    assert data["will_execute"] is False
    assert data["can_execute"] is False
    assert data["is_advisory_only"] is True


def test_full_pipeline_integration():
    vid = _make_and_activate_version()

    elig = client.get(f"{BASE}/candidates/{vid}/run-preview/eligibility").json()
    assert elig["eligible"] is True

    plan = client.post(f"{BASE}/candidates/{vid}/run-preview/plan").json()
    assert plan["plan_ready"] is True
    assert plan["will_execute"] is False
    assert plan["plan_is_dry_run"] is True

    gate = client.get(f"{BASE}/candidates/{vid}/run-preview/execution-gate").json()
    assert gate["gate_passed"] is True
    assert gate["execution_ready"] is True
    assert gate["will_execute"] is False

    preview = client.post(f"{BASE}/candidates/{vid}/run-preview").json()
    assert preview["preview_ready"] is True
    assert preview["will_execute"] is False
    assert preview["can_execute"] is False
    assert preview["is_advisory_only"] is True

    audit = client.get(f"{BASE}/candidates/{vid}/run-preview/audit").json()
    steps = [e["step"] for e in audit["events"]]
    assert "run_preview_completed" in steps


def test_execution_ready_field():
    vid = _make_and_activate_version()
    gate = client.get(f"{BASE}/candidates/{vid}/run-preview/execution-gate").json()
    assert "execution_ready" in gate
    assert gate["execution_ready"] is True


def test_safety_invariants_on_all_endpoints():
    vid = _make_and_activate_version()

    for response in [
        client.get(f"{BASE}/candidates/{vid}/run-preview/eligibility").json(),
        client.post(f"{BASE}/candidates/{vid}/run-preview/plan").json(),
        client.get(f"{BASE}/candidates/{vid}/run-preview/execution-gate").json(),
        client.post(f"{BASE}/candidates/{vid}/run-preview").json(),
    ]:
        assert response.get("will_execute") is False, f"will_execute not False: {response}"
        assert response.get("can_execute") is False, f"can_execute not False: {response}"
        assert response.get("is_advisory_only") is True, f"is_advisory_only not True: {response}"
