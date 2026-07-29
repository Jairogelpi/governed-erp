from fastapi.testclient import TestClient

from apps.api.main import app


client = TestClient(app)


def test_demo_dashboard_returns_html_and_links_full_demo():
    response = client.get("/demo")

    assert response.status_code == 200
    html = response.text
    assert "ERP Agent OS" in html
    assert "Record-to-Skill" in html
    assert "Run full demo" in html
    assert "Skill Inspector v0.4" in html
    assert "Run History / Audit Timeline v0.5" in html
    assert "Approval Gate / Safe Action Plan v0.6" in html
    assert "Approval Decision Simulation v0.7" in html
    assert "Confirmed Read-Only Action Dispatcher" in html
    assert "Business Analysis & Opportunity Scanner" in html
    assert "Create non-executable draft" in html
    assert "/v1/demo/full-record-to-skill-flow" in html
    assert "/v1/product/connections/" in html
    assert "docs/demo/full_record_to_skill_success_response.json" in html


def test_health_endpoint_still_works_after_demo_dashboard_route():
    response = client.get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
