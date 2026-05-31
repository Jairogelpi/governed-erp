"""UI tests for Sprint 83 - visual table/form extraction."""

from fastapi.testclient import TestClient

from apps.api.main import app


def test_ui_exposes_visual_table_form_extraction_section():
    client = TestClient(app)

    response = client.get("/demo")

    assert response.status_code == 200
    assert b"Visual Table/Form Extraction" in response.content
    assert b"Sprint 83 derives sanitized table/form structures" in response.content
    assert b"visualExtractionObservationId" in response.content
    assert b"visualExtractionWorkflowTraceId" in response.content
    assert b"visualExtractionCreate" in response.content
    assert b"visualExtractionAudit" in response.content
