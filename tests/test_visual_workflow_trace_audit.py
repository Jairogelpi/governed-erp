"""Audit tests for Sprint 82 - visual workflow trace."""

import json

from erpguard.product.visual_workflow_trace import (
    VisualWorkflowTraceAuditService,
    VisualWorkflowTraceService,
)
from test_visual_workflow_trace import _db_session_observation, _input


def test_audit_records_created_blocked_retrieved_without_raw_secrets():
    db, session, observation = _db_session_observation()
    try:
        service = VisualWorkflowTraceService(db)
        created = service.create_trace(_input(session.visual_session_id, observation.observation_id))
        blocked = service.create_trace(
            _input(
                session.visual_session_id,
                observation.observation_id,
                steps=[{"step_type": "note", "label": "Login", "credential_touchpoint": {"field_label": "Token", "touchpoint_type": "field", "value": "secret"}}],
            )
        )
        service.get_trace(created.workflow_trace_id)
        audit = VisualWorkflowTraceAuditService(db).get_audit()
        event_types = [event["event_type"] for event in audit.events]
        payload = json.dumps([event["details"] for event in audit.events]).lower()

        assert created.status == "created"
        assert blocked.status == "blocked"
        assert "visual_workflow_trace_created" in event_types
        assert "visual_workflow_trace_blocked" in event_types
        assert "visual_workflow_trace_retrieved" in event_types
        for forbidden in ["password", "api_key", "token", "secret", "authorization", "bearer", "credential"]:
            assert forbidden not in payload
    finally:
        db.close()
