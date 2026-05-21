from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def test_demo_dashboard_includes_sprint3_section():
    response = client.get("/demo")

    assert response.status_code == 200
    html = response.text
    assert "Safe Skill Review &amp; Compilation" in html or "Safe Skill Review & Compilation" in html
    assert "Review draft" in html
    assert "Validate draft" in html
    assert "Compile to skill" in html
    assert "Run dry-run proof" in html
    assert "/v1/product/automation-drafts/" in html
    assert "/v1/product/skills/" in html
    assert "dry-run-proof" in html
    assert "compile-skill" in html
    assert "requires_approval_before_activation" in html
