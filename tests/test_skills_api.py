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
            "inputs": {
                "order_reference": "string",
            },
            "guards": ["formula_guard"],
            "workflow": [
                {"id": "open_orders", "type": "navigate", "target": "/fake-erp/sales/orders"},
                {"id": "search_order", "type": "fill", "selector": "[data-testid='order-search']"},
                {
                    "id": "open_order",
                    "type": "click",
                    "selector_template": "[data-testid='open-order-{{order_reference}}']",
                },
                {"id": "open_formula", "type": "click", "selector": "[data-testid='formula-tab']"},
                {"id": "review_formula", "type": "guard", "guard": "formula_guard"},
            ],
        },
    }


def test_create_skill_returns_skill_and_version_ids():
    response = client.post("/v1/skills", json=make_skill_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["skill_id"].startswith("skill_")
    assert body["version_id"].startswith("skill_version_")
    assert body["name"] == "Safe Formula Guard UI Preflight"
    assert body["status"] == "draft"
    assert body["runtime_type"] == "deterministic_browser"
    assert body["llm_required_for_repeated_runs"] is False


def test_list_skills_includes_created_skill():
    created = client.post("/v1/skills", json=make_skill_payload()).json()

    response = client.get("/v1/skills")

    assert response.status_code == 200
    skills = response.json()
    assert any(skill["skill_id"] == created["skill_id"] for skill in skills)


def test_get_skill_by_id_returns_latest_version_data():
    created = client.post("/v1/skills", json=make_skill_payload()).json()

    response = client.get(f"/v1/skills/{created['skill_id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["skill_id"] == created["skill_id"]
    assert body["latest_version_id"] == created["version_id"]
    assert body["skill_package"]["skill_id"] == "safe_formula_guard_ui_preflight"
    assert body["llm_required_for_repeated_runs"] is False


def test_missing_skill_returns_404():
    response = client.get("/v1/skills/missing-skill")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "skill_not_found"


def test_health_endpoint_still_works():
    response = client.get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}