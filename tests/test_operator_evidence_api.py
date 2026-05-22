from __future__ import annotations

from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)


def test_assemble_evidence_pack():
    r = client.post("/v1/operator/evidence-packs", json={
        "created_by": "api_test",
        "scenario_label": "API Test Pack",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["pack_id"].startswith("evpack_")
    assert body["evidence_status"] == "ready"
    assert body["sprint_chain"] == "20-26"


def test_assemble_with_seed_result():
    r = client.post("/v1/operator/evidence-packs", json={
        "created_by": "api_test",
        "seed_result": {"version_id": "ui_skv_test", "run_id": "run_test"},
    })
    assert r.status_code == 200
    body = r.json()
    assert body["seed_result"]["version_id"] == "ui_skv_test"


def test_get_evidence_pack():
    created = client.post("/v1/operator/evidence-packs", json={"created_by": "api_get_test"}).json()
    pack_id = created["pack_id"]
    r = client.get(f"/v1/operator/evidence-packs/{pack_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["pack_id"] == pack_id
    assert body["created_by"] == "api_get_test"


def test_get_nonexistent_pack_returns_404():
    r = client.get("/v1/operator/evidence-packs/evpack_doesnotexist")
    assert r.status_code == 404
    assert "evidence_pack_not_found" in r.json()["error"]["code"]


def test_get_pack_safety_report():
    pack_id = client.post("/v1/operator/evidence-packs", json={}).json()["pack_id"]
    r = client.get(f"/v1/operator/evidence-packs/{pack_id}/safety-report")
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] == "safe"
    assert body["invariants_enforced"] > 0
    assert body["invariants_violated"] == 0


def test_safety_report_nonexistent_pack_404():
    r = client.get("/v1/operator/evidence-packs/evpack_missing/safety-report")
    assert r.status_code == 404


def test_get_pack_final_report():
    pack_id = client.post("/v1/operator/evidence-packs", json={}).json()["pack_id"]
    r = client.get(f"/v1/operator/evidence-packs/{pack_id}/final-report")
    assert r.status_code == 200
    body = r.json()
    assert body["safety_verdict"] == "safe"
    assert body["invariants_enforced"] > 0
    assert body["operation_count"] > 0
    assert "ERPGuard" in body["product"]


def test_final_report_nonexistent_pack_404():
    r = client.get("/v1/operator/evidence-packs/evpack_missing/final-report")
    assert r.status_code == 404


def test_get_demo_runbook():
    r = client.get("/v1/operator/demo-runbook")
    assert r.status_code == 200
    body = r.json()
    assert body["operation_count"] > 0
    assert len(body["operations"]) == body["operation_count"]
    assert len(body["kill_switches"]) >= 2
    assert len(body["safety_flags"]) >= 3


def test_runbook_operations_have_safety_notes():
    r = client.get("/v1/operator/demo-runbook")
    for op in r.json()["operations"]:
        assert isinstance(op["safety_notes"], list)
        assert len(op["safety_notes"]) > 0


def test_assemble_pack_safety_checks_complete():
    pack_id = client.post("/v1/operator/evidence-packs", json={}).json()["pack_id"]
    body = client.get(f"/v1/operator/evidence-packs/{pack_id}").json()
    sc = body["safety_checks"]
    assert sc["verdict"] == "safe"
    assert sc["invariants_violated"] == 0
    assert len(sc["invariants"]) > 0


def test_assemble_pack_runbook_summary_complete():
    pack_id = client.post("/v1/operator/evidence-packs", json={}).json()["pack_id"]
    body = client.get(f"/v1/operator/evidence-packs/{pack_id}").json()
    rb = body["runbook_summary"]
    assert rb["operation_count"] > 0


def test_assemble_pack_test_evidence_complete():
    pack_id = client.post("/v1/operator/evidence-packs", json={}).json()["pack_id"]
    body = client.get(f"/v1/operator/evidence-packs/{pack_id}").json()
    te = body["test_evidence"]
    assert te["total_sprints_covered"] >= 7
    assert te["all_invariants_enforced"] is True
