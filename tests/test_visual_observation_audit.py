"""Audit tests for Sprint 81 - visual observation snapshots."""

import json

from erpguard.db.session import SessionLocal, init_db
from erpguard.product.visual_browser_session import VisualBrowserSessionInput, VisualBrowserSessionService
from erpguard.product.visual_observation_snapshot import (
    VisualObservationAuditService,
    VisualObservationSnapshotInput,
    VisualObservationSnapshotService,
)
from test_visual_observation_snapshot import _payload


def test_audit_records_created_blocked_retrieved_without_raw_secrets():
    init_db()
    db = SessionLocal()
    try:
        session = VisualBrowserSessionService(db).create_session(
            VisualBrowserSessionInput(created_by="operator_1", target_url="https://safe.example.com")
        )
        service = VisualObservationSnapshotService(db)
        created = service.create_snapshot(
            VisualObservationSnapshotInput(visual_session_id=session.visual_session_id, **_payload())
        )
        blocked = service.create_snapshot(
            VisualObservationSnapshotInput(
                visual_session_id=session.visual_session_id,
                **_payload(credential_fields_detected=[{"field_label": "Token", "field_type": "text", "value": "secret"}]),
            )
        )
        service.get_snapshot(created.observation_id)
        audit = VisualObservationAuditService(db).get_audit()
        event_types = [event["event_type"] for event in audit.events]
        payload = json.dumps([event["details"] for event in audit.events]).lower()

        assert created.status == "created"
        assert blocked.status == "blocked"
        assert "visual_observation_snapshot_created" in event_types
        assert "visual_observation_snapshot_blocked" in event_types
        assert "visual_observation_snapshot_retrieved" in event_types
        for forbidden in ["password", "api_key", "token", "secret", "authorization", "bearer", "credential"]:
            assert forbidden not in payload
    finally:
        db.close()
