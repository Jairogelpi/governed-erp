"""Sprint 7 — UI tests for the write readiness section in the demo dashboard."""
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def test_demo_dashboard_includes_sprint7_section():
    response = client.get("/demo")
    assert response.status_code == 200
    html = response.text
    assert "Write Capability Readiness" in html
    assert "Sprint 7" in html
    assert "ALLOW_REAL_ODOO_WRITES=false" in html
    assert "can_execute_real_writes=false" in html
    assert "approved_for_real_execution=false" in html
    assert "wr-assessment-output" in html
    assert "wr-summary-output" in html
    assert "wr-impact-output" in html
    assert "wr-rollback-output" in html
    assert "wr-certification-output" in html
    assert "wrRunAssessment" in html
    assert "wrGetSummary" in html
    assert "wrGenerateImpact" in html
    assert "wrDraftRollback" in html
    assert "wrCertify" in html
    assert "write-readiness-assessment" in html
    assert "write-readiness-summary" in html
    assert "write-readiness-certification" in html
    assert "impact-preview" in html
    assert "rollback-plan" in html
    assert "overall_risk_level" in html
    assert "can_certify_write_readiness" in html
    assert "dual_approval_required" in html
