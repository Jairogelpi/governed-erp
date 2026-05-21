"""Sprint 6 — UI tests for the live read section in the demo dashboard."""
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def test_demo_dashboard_includes_sprint6_section():
    response = client.get("/demo")

    assert response.status_code == 200
    html = response.text
    assert "Controlled Real Read Execution" in html
    assert "Live Evidence" in html
    assert "Sprint 6" in html
    assert "ALLOW_REAL_ODOO_READS=true" in html
    assert "ALLOW_REAL_ODOO_WRITES=false" in html
    assert "live-read-execution-request" in html
    assert "live-read-policy" in html
    assert "connection-context" in html
    assert "live-read-runs" in html
    assert "live-evidence" in html
    assert "Check connection context" in html
    assert "Check live read policy" in html
    assert "Create live read request" in html
    assert "Run live read" in html
    assert "Get live evidence" in html
    assert "can_execute_real_writes" in html
    assert "allow_real_odoo_reads" in html
    assert "real_read_count" in html
