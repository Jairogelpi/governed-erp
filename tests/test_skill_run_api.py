from fastapi.testclient import TestClient

from apps.api.main import app


client = TestClient(app)


def make_skill_payload() -> dict:
    return {
        "name": "Safe Formula Guard UI Preflight",
        "description": "Validates a sales order formula through the Fake ERP flow.",
        "runtime_type": "deterministic_browser",
        "llm_required_for_repeated_runs": False,
        "skill_package": {
            "skill_id": "safe_formula_guard_ui_preflight",
            "inputs": {"order_reference": "string"},
            "guards": ["formula_guard"],
            "workflow": [],
        },
    }


def create_skill() -> str:
    response = client.post("/v1/skills", json=make_skill_payload())
    assert response.status_code == 200
    return response.json()["skill_id"]


def test_skill_run_allow_path_persists_run_and_steps():
    skill_id = create_skill()

    response = client.post(f"/v1/skills/{skill_id}/run", json={"inputs": {"order_reference": "SO-VALID"}})

    assert response.status_code == 200
    body = response.json()
    assert body["skill_id"] == skill_id
    assert body["status"] == "success"
    assert body["decision"] == "allow"
    assert body["output"]["order_reference"] == "SO-VALID"
    assert body["token_economics"]["creation_token_cost_estimate"] == 2000
    assert body["token_economics"]["repeated_execution_token_cost"] == 0
    assert body["token_economics"]["estimated_tokens_saved"] == 2000

    run_detail = client.get(f"/v1/skills/{skill_id}/runs/{body['skill_run_id']}")
    assert run_detail.status_code == 200
    run_body = run_detail.json()
    assert run_body["status"] == "success"
    assert run_body["decision"] == "allow"
    assert [step["step_id"] for step in run_body["steps"]] == [
        "load_skill",
        "load_order",
        "formula_guard",
        "produce_result",
    ]


def test_skill_run_block_path_returns_block_decision():
    skill_id = create_skill()

    response = client.post(f"/v1/skills/{skill_id}/run", json={"inputs": {"order_reference": "SO-FORMULA-MISMATCH"}})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["decision"] == "block"
    assert body["output"]["policy_id"] == "formula_guard"
    assert body["output"]["policy_version"] == "0.1.0"
    assert body["output"]["issues"]


def test_skill_run_rejects_missing_order_reference():
    skill_id = create_skill()

    response = client.post(f"/v1/skills/{skill_id}/run", json={"inputs": {}})

    assert response.status_code == 422


def test_skill_run_rejects_unknown_skill():
    response = client.post("/v1/skills/missing-skill/run", json={"inputs": {"order_reference": "SO-VALID"}})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "skill_not_found"


def test_health_endpoint_still_works_after_skill_run_route():
    response = client.get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}