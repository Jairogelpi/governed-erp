"""UI tests for Sprint 81 - visual observation snapshot."""

from fastapi.testclient import TestClient

from apps.api.main import app


def test_ui_exposes_visual_observation_snapshot_section():
    client = TestClient(app)

    response = client.get("/demo")

    assert response.status_code == 200
    assert b"Visual Observation Snapshot" in response.content
    assert b"Sprint 81 creates sanitized screen/DOM observation snapshots" in response.content
    assert b"visualObservationSessionId" in response.content
    assert b"visualObservationJson" in response.content
    assert b"visualObservationCreate" in response.content
    assert b"visualObservationAudit" in response.content
