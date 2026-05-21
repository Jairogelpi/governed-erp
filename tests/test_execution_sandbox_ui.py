"""Sprint 5 — UI tests for the execution sandbox section in the demo dashboard."""
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def test_demo_dashboard_includes_sprint5_section():
    response = client.get("/demo")

    assert response.status_code == 200
    html = response.text
    assert "Limited Approved Execution Sandbox" in html
    assert "Sprint 5" in html
    assert "ALLOW_REAL_ODOO_WRITES=false" in html
    assert "execution-requests" in html
    assert "execution-policy" in html
    assert "execution-runs" in html
    assert "blocked-writes" in html
    assert "Create execution request" in html
    assert "Run (dry-run sandbox)" in html
    assert "Get timeline" in html
    assert "List blocked writes" in html
    assert "can_execute_real_writes" in html
    assert "real_erp_writes_enabled" in html
    assert "blocked_write_count" in html
