"""Sprint 8 — UI tests for the write pilot section in the demo dashboard."""
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def test_demo_dashboard_includes_sprint8_section():
    response = client.get("/demo")
    assert response.status_code == 200
    html = response.text
    assert "First Real Write Pilot" in html
    assert "mail.message.create" in html
    assert "Sprint 8" in html
    assert "ALLOW_R1_REAL_WRITE_PILOT=false" in html
    assert "ALLOW_GENERIC_REAL_ODOO_WRITES=false" in html
    assert "ALLOW_R3_R4_REAL_WRITES=false" in html
    assert "wp-request-output" in html
    assert "wp-policy-output" in html
    assert "wp-run-output" in html
    assert "wp-evidence-output" in html
    assert "wp-history-output" in html
    assert "wpCreateRequest" in html
    assert "wpCheckPolicy" in html
    assert "wpExecute" in html
    assert "wpGetEvidence" in html
    assert "write-pilot/request" in html
    assert "write-pilot/requests" in html
    assert "write-pilot/runs" in html
    assert "allow_r1_real_write_pilot" in html
    assert "allow_generic_real_odoo_writes" in html
    assert "target_model" in html
    assert "double human approval" in html
    assert "sale.order.action_confirm" in html
    assert "stock.picking.button_validate" in html
