from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import app


client = TestClient(app)


def test_marketplace_connector_endpoints():
    list_response = client.get("/v1/marketplace/connectors")
    assert list_response.status_code == 200
    connectors = list_response.json()["connectors"]
    assert any(connector["connector_id"] == "odoo" and connector["status"] == "implemented" for connector in connectors)
    assert any(connector["connector_id"] == "gmail" and connector["status"] == "placeholder" for connector in connectors)

    detail_response = client.get("/v1/marketplace/connectors/odoo")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["connector_id"] == "odoo"
    assert detail["execution_enabled"] is False


def test_marketplace_skill_template_endpoints():
    list_response = client.get("/v1/marketplace/skill-templates")
    assert list_response.status_code == 200
    templates = list_response.json()["templates"]
    assert any(template["template_id"] == "odoo_formula_preflight" for template in templates)

    detail_response = client.get("/v1/marketplace/skill-templates/odoo_formula_preflight")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["risk_level"] == "R2"
    assert "formula_guard" in detail["required_guards"]
    assert detail["safety_summary"]["write_actions_enabled"] is False


def test_marketplace_requirements_and_install_draft_flow():
    requirements = client.post(
        "/v1/marketplace/skill-templates/odoo_formula_preflight/check-requirements",
        json={"configuration": {"connection_id": "conn_api_demo"}},
    )
    assert requirements.status_code == 200
    assert requirements.json()["can_install"] is True

    install = client.post(
        "/v1/marketplace/skill-templates/odoo_formula_preflight/install-draft",
        json={"configuration": {"connection_id": "conn_api_demo"}},
    )
    assert install.status_code == 200
    body = install.json()
    assert body["status"] == "draft_installed"
    assert body["draft"]["draft_id"].startswith("automation_draft_")
    assert body["draft"]["write_actions"] is False
    assert body["draft"]["runtime_mode"] == "dry_run_only"
    assert body["review"]["status"] == "ready_to_compile"

    installed = client.get("/v1/marketplace/installed")
    assert installed.status_code == 200
    assert any(item["draft_id"] == body["draft"]["draft_id"] for item in installed.json()["installed"])


def test_marketplace_blocks_placeholder_template_install():
    response = client.post(
        "/v1/marketplace/skill-templates/gmail_lead_intake_placeholder/install-draft",
        json={"configuration": {"connection_id": "gmail_demo"}},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "template_requirements_not_met"


def test_marketplace_missing_template_returns_controlled_error():
    response = client.get("/v1/marketplace/skill-templates/missing_template")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "template_not_found"
