"""UI tests for Sprint 82 - visual workflow trace."""

from fastapi.testclient import TestClient

from apps.api.main import app


def test_ui_exposes_visual_workflow_recording_trace_section():
    client = TestClient(app)

    response = client.get("/demo")

    assert response.status_code == 200
    assert b"Visual Workflow Recording Trace" in response.content
    assert b"Sprint 82 creates sanitized workflow traces from supplied/mock events only" in response.content
    assert b"visualWorkflowSessionId" in response.content
    assert b"visualWorkflowStepsJson" in response.content
    assert b"visualWorkflowCreate" in response.content
    assert b"visualWorkflowAudit" in response.content
