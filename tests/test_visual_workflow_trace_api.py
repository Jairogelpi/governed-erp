"""API tests for Sprint 82 - visual workflow trace."""

from fastapi.testclient import TestClient

from apps.api.main import app
from test_visual_workflow_trace import ALLOWED_STEPS, _db_session_observation


def test_api_create_get_list_and_audit_workflow_trace():
    db, session, observation = _db_session_observation()
    db.close()
    client = TestClient(app)

    created = client.post(
        f"/v1/operator-console/visual-browser/session/{session.visual_session_id}/workflow-trace",
        json={
            "created_by": "operator_1",
            "workflow_name": "Revisar pedidos pendientes",
            "workflow_goal": "Detectar pedidos que no se pueden servir",
            "observation_ids": [observation.observation_id],
            "steps": ALLOWED_STEPS,
        },
    )
    payload = created.json()
    retrieved = client.get(
        f"/v1/operator-console/visual-browser/workflow-trace/{payload['workflow_trace_id']}"
    )
    listed = client.get("/v1/operator-console/visual-browser/workflow-traces")
    audit = client.get("/v1/operator-console/visual-browser/workflow-trace-audit")

    assert created.status_code == 200
    assert payload["status"] == "created"
    assert retrieved.status_code == 200
    assert retrieved.json()["workflow_trace_id"] == payload["workflow_trace_id"]
    assert listed.status_code == 200
    assert any(item["workflow_trace_id"] == payload["workflow_trace_id"] for item in listed.json()["traces"])
    assert audit.status_code == 200
    assert any(event["event_type"] == "visual_workflow_trace_created" for event in audit.json()["events"])
