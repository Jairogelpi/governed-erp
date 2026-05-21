from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import app


client = TestClient(app)


def _create_session() -> str:
    response = client.post(
        "/v1/agent-builder/sessions",
        json={"created_by": {"type": "user", "id": "operator_1", "display_name": "Operator"}},
    )
    assert response.status_code == 200
    return response.json()["session_id"]


def test_agent_builder_api_full_safe_flow_to_draft():
    session_id = _create_session()
    assert client.post(f"/v1/agent-builder/sessions/{session_id}/select-template", json={"template_id": "odoo_formula_preflight"}).status_code == 200
    assert client.post(f"/v1/agent-builder/sessions/{session_id}/select-connector", json={"connector_id": "odoo"}).status_code == 200
    assert client.post(f"/v1/agent-builder/sessions/{session_id}/configure-trigger", json={"trigger": {"type": "manual"}}).status_code == 200
    assert client.post(f"/v1/agent-builder/sessions/{session_id}/configure-inputs", json={"inputs": {"connection_id": "conn_demo", "order_reference": "S00042"}}).status_code == 200
    assert client.post(f"/v1/agent-builder/sessions/{session_id}/configure-steps", json={"steps": ["load_context", "read_record", "run_guard", "produce_decision"]}).status_code == 200
    assert client.post(f"/v1/agent-builder/sessions/{session_id}/configure-guards", json={"guards": ["no_generic_writes", "no_r3_r4_writes", "no_raw_tool_execution", "requires_human_review", "formula_guard", "odoo_readonly_guard"]}).status_code == 200

    requirements = client.post(f"/v1/agent-builder/sessions/{session_id}/check-requirements")
    assert requirements.status_code == 200
    assert requirements.json()["passed"] is True

    preview = client.get(f"/v1/agent-builder/sessions/{session_id}/preview")
    assert preview.status_code == 200
    assert preview.json()["write_actions"] is False

    save = client.post(f"/v1/agent-builder/sessions/{session_id}/save-draft")
    assert save.status_code == 200
    body = save.json()
    assert body["status"] == "saved_as_draft"
    assert body["automation_draft_id"].startswith("automation_draft_")
    assert body["write_actions"] is False
    assert body["safety"]["requires_approval"] is True

    timeline = client.get(f"/v1/agent-builder/sessions/{session_id}/timeline")
    assert timeline.status_code == 200
    assert any(event["event_type"] == "draft_saved" for event in timeline.json()["events"])


def test_agent_builder_api_blocks_forbidden_step():
    session_id = _create_session()
    client.post(f"/v1/agent-builder/sessions/{session_id}/select-template", json={"template_id": "odoo_formula_preflight"})
    client.post(f"/v1/agent-builder/sessions/{session_id}/select-connector", json={"connector_id": "odoo"})
    client.post(f"/v1/agent-builder/sessions/{session_id}/configure-inputs", json={"inputs": {"connection_id": "conn_demo"}})

    response = client.post(f"/v1/agent-builder/sessions/{session_id}/configure-steps", json={"steps": ["load_context", "shell_command"]})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "forbidden_builder_step"


def test_agent_builder_step_library_endpoint_lists_allowed_and_forbidden_steps():
    response = client.get("/v1/agent-builder/step-library")

    assert response.status_code == 200
    body = response.json()
    assert "load_context" in [step["step_type"] for step in body["allowed_steps"]]
    assert "shell_command" in body["forbidden_step_types"]
    assert "odoo_write" in body["forbidden_step_types"]
