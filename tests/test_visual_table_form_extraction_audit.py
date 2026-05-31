"""Audit tests for Sprint 83 - visual table/form extraction."""

import json

from erpguard.product.visual_table_form_extraction import (
    VisualTableFormExtractionAuditService,
    VisualTableFormExtractionInput,
    VisualTableFormExtractionService,
)
from test_visual_table_form_extraction import _db_session_observation_trace


def test_audit_records_created_blocked_retrieved_without_raw_secrets():
    db, _session, observation, trace = _db_session_observation_trace()
    try:
        service = VisualTableFormExtractionService(db)
        created = service.create_extraction(
            VisualTableFormExtractionInput(
                observation_id=observation.observation_id,
                workflow_trace_id=trace.workflow_trace_id,
                created_by="operator_1",
            )
        )
        blocked = service.create_extraction(
            VisualTableFormExtractionInput(observation_id="vobs_missing", created_by="operator_1")
        )
        service.get_extraction(created.extraction_id)
        audit = VisualTableFormExtractionAuditService(db).get_audit()
        event_types = [event["event_type"] for event in audit.events]
        payload = json.dumps([event["details"] for event in audit.events]).lower()

        assert created.status == "created"
        assert blocked.status == "blocked"
        assert "visual_table_form_extraction_created" in event_types
        assert "visual_table_form_extraction_blocked" in event_types
        assert "visual_table_form_extraction_retrieved" in event_types
        for forbidden in ["password", "api_key", "token", "secret", "authorization", "bearer"]:
            assert forbidden not in payload
    finally:
        db.close()
