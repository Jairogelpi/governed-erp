"""Sprint 42 — Action plan API integration tests."""
from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)
BASE = "/v1/operator-console"


def test_create_action_plan_prepare_for_run():
    r = client.post(f"{BASE}/action-plan", json={"goal": "preparar para preview", "actor": "operator"})
    assert r.status_code == 200
    data = r.json()
    assert data["plan_type"] == "prepare_for_run"
    assert data["will_execute"] is False
    assert data["can_execute"] is False
    assert data["is_advisory_only"] is True


def test_create_action_plan_activate_candidate():
    r = client.post(f"{BASE}/action-plan", json={"goal": "activar candidato"})
    assert r.status_code == 200
    assert r.json()["plan_type"] == "activate_candidate"


def test_create_action_plan_fix_gaps():
    r = client.post(f"{BASE}/action-plan", json={"goal": "corregir gaps de governance"})
    assert r.status_code == 200
    assert r.json()["plan_type"] == "fix_governance_gaps"


def test_create_action_plan_find_reusable():
    r = client.post(f"{BASE}/action-plan", json={"goal": "encontrar reutilizable"})
    assert r.status_code == 200
    assert r.json()["plan_type"] == "find_reusable_skill"


def test_create_action_plan_inspect_lifecycle():
    r = client.post(f"{BASE}/action-plan", json={"goal": "inspeccionar ciclo completo"})
    assert r.status_code == 200
    assert r.json()["plan_type"] == "inspect_lifecycle"


def test_plan_has_steps():
    r = client.post(f"{BASE}/action-plan", json={"goal": "preparar para preview"})
    data = r.json()
    assert data["total_steps"] >= 1
    assert len(data["steps"]) == data["total_steps"]


def test_all_steps_require_operator_click():
    r = client.post(f"{BASE}/action-plan", json={"goal": "activar candidato"})
    for step in r.json()["steps"]:
        assert step["requires_operator_click"] is True
        assert step["executable"] is False


def test_plan_id_has_prefix():
    r = client.post(f"{BASE}/action-plan", json={"goal": "preparar para preview"})
    assert r.json()["plan_id"].startswith("aplan_")


def test_advisory_summary_present():
    r = client.post(f"{BASE}/action-plan", json={"goal": "preparar para preview"})
    assert len(r.json()["advisory_summary"]) > 0


def test_with_version_id():
    r = client.post(f"{BASE}/action-plan", json={"goal": "preparar para preview", "version_id": "ver_xyz"})
    assert r.status_code == 200
    assert r.json()["version_id"] == "ver_xyz"


def test_step_fields_complete():
    r = client.post(f"{BASE}/action-plan", json={"goal": "preparar para preview"})
    step = r.json()["steps"][0]
    for field in ("step_number", "title", "description", "endpoint_hint", "method_hint",
                  "severity", "prereqs_met", "requires_operator_click", "executable"):
        assert field in step, f"missing field: {field}"


def test_audit_returns_list():
    client.post(f"{BASE}/action-plan", json={"goal": "preparar para preview"})
    r = client.get(f"{BASE}/action-plan/audit")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data["entries"], list)
    assert data["event_count"] >= 1
    assert data["will_execute"] is False
    assert data["is_advisory_only"] is True


def test_audit_accumulates():
    before = client.get(f"{BASE}/action-plan/audit").json()["event_count"]
    client.post(f"{BASE}/action-plan", json={"goal": "activar candidato"})
    after = client.get(f"{BASE}/action-plan/audit").json()["event_count"]
    assert after >= before + 1


def test_audit_entry_fields():
    client.post(f"{BASE}/action-plan", json={"goal": "fix governance gaps"})
    entry = client.get(f"{BASE}/action-plan/audit").json()["entries"][0]
    for field in ("plan_id", "plan_type", "goal", "step_count", "blocking_count", "created_at"):
        assert field in entry


def test_plan_types_endpoint():
    r = client.get(f"{BASE}/action-plan/plan-types")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 6
    assert data["will_execute"] is False
    assert data["is_advisory_only"] is True
    names = {t["plan_type"] for t in data["plan_types"]}
    assert "prepare_for_run" in names
    assert "activate_candidate" in names


def test_safety_invariants_all_endpoints():
    responses = [
        client.post(f"{BASE}/action-plan", json={"goal": "preparar para preview"}).json(),
        client.get(f"{BASE}/action-plan/audit").json(),
        client.get(f"{BASE}/action-plan/plan-types").json(),
    ]
    for resp in responses:
        assert resp.get("will_execute") is False
        assert resp.get("can_execute") is False
        assert resp.get("is_advisory_only") is True
