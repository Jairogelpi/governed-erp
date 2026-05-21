from fastapi.testclient import TestClient

from apps.api.main import app


client = TestClient(app)


def test_demo_dashboard_includes_business_analysis_section():
    response = client.get("/demo")

    assert response.status_code == 200
    html = response.text
    assert "Business Analysis & Opportunity Scanner" in html
    assert "Run business analysis" in html
    assert "Create non-executable draft" in html
    assert "ROI" in html
    assert "/v1/product/connections/" in html
