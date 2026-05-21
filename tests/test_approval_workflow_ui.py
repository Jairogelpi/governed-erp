from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def test_demo_dashboard_includes_sprint4_section():
    response = client.get("/demo")

    assert response.status_code == 200
    html = response.text
    assert "Skill Approval" in html
    assert "Activation Gates" in html or "activation-gate" in html
    assert "Submit approval request" in html
    assert "Approve (dry-run only)" in html
    assert "Run activation gate" in html
    assert "Governance summary" in html
    assert "/v1/product/skills/" in html
    assert "approval-request" in html
    assert "approval-decision" in html
    assert "activation-gate" in html
    assert "governance-summary" in html
    assert "can_execute_real_writes" in html
    assert "approved_for_real_execution" in html
