from __future__ import annotations

from erpguard.product.operator_demo_seed import OperatorDemoSeedService


def test_seed_returns_all_ids():
    svc = OperatorDemoSeedService()
    result = svc.seed(operator="test_op")
    assert result.session_id
    assert result.draft_id
    assert result.skill_id
    assert result.compiled_skill_id
    assert result.version_id
    assert result.run_id
    assert result.schedule_id


def test_seed_scenario_label():
    svc = OperatorDemoSeedService()
    result = svc.seed()
    assert "Formula Review" in result.scenario_label or "ERP" in result.scenario_label


def test_seed_erp_target():
    svc = OperatorDemoSeedService()
    result = svc.seed()
    assert "127.0.0.1" in result.erp_target or "localhost" in result.erp_target


def test_seed_safety_invariants():
    svc = OperatorDemoSeedService()
    result = svc.seed()
    assert len(result.safety_invariants) > 0
    joined = " ".join(result.safety_invariants)
    assert "fake" in joined.lower() or "erp" in joined.lower()
    assert "no_llm" in joined.lower() or "llm" in joined.lower()


def test_seed_notes():
    svc = OperatorDemoSeedService()
    result = svc.seed()
    assert len(result.notes) > 0
    joined = " ".join(result.notes)
    assert result.session_id in joined
    assert result.version_id in joined


def test_seed_ids_have_prefixes():
    svc = OperatorDemoSeedService()
    result = svc.seed()
    assert len(result.session_id) > 8
    assert len(result.version_id) > 8
    assert result.schedule_id.startswith("sch_")


def test_seed_idempotent_creates_new_resources():
    svc = OperatorDemoSeedService()
    r1 = svc.seed()
    r2 = svc.seed()
    assert r1.session_id != r2.session_id
    assert r1.version_id != r2.version_id
    assert r1.schedule_id != r2.schedule_id


def test_seed_post_to_api():
    from fastapi.testclient import TestClient
    from apps.api.main import app
    client = TestClient(app)
    r = client.post("/v1/operator/demo-seed", json={"operator": "api_test_op"})
    assert r.status_code == 200
    body = r.json()
    assert body["session_id"]
    assert body["version_id"]
    assert body["run_id"]
    assert body["schedule_id"]
    assert len(body["safety_invariants"]) > 0
