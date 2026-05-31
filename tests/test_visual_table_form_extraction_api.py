"""API tests for Sprint 83 - visual table/form extraction."""

from fastapi.testclient import TestClient

from apps.api.main import app
from test_visual_table_form_extraction import _db_session_observation_trace


def test_api_create_get_list_and_audit_table_form_extraction():
    db, _session, observation, trace = _db_session_observation_trace()
    db.close()
    client = TestClient(app)

    created = client.post(
        f"/v1/operator-console/visual-browser/observation-snapshot/{observation.observation_id}/table-form-extraction",
        json={
            "created_by": "operator_1",
            "workflow_trace_id": trace.workflow_trace_id,
            "extraction_goal": "Extract visible order list structure",
        },
    )
    payload = created.json()
    retrieved = client.get(
        f"/v1/operator-console/visual-browser/table-form-extraction/{payload['extraction_id']}"
    )
    listed = client.get("/v1/operator-console/visual-browser/table-form-extractions")
    audit = client.get("/v1/operator-console/visual-browser/table-form-extraction-audit")

    assert created.status_code == 200
    assert payload["status"] == "created"
    assert retrieved.status_code == 200
    assert retrieved.json()["extraction_id"] == payload["extraction_id"]
    assert listed.status_code == 200
    assert any(item["extraction_id"] == payload["extraction_id"] for item in listed.json()["extractions"])
    assert audit.status_code == 200
    assert any(event["event_type"] == "visual_table_form_extraction_created" for event in audit.json()["events"])
