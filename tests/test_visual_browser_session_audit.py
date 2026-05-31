"""Audit tests for Sprint 80 - visual browser session shell."""

import json

from erpguard.db.session import SessionLocal, init_db
from erpguard.product.visual_browser_session import (
    VisualBrowserSessionAuditService,
    VisualBrowserSessionInput,
    VisualBrowserSessionService,
)


def test_audit_records_created_blocked_revoked_retrieved_without_secrets():
    init_db()
    session = SessionLocal()
    try:
        service = VisualBrowserSessionService(session)
        created = service.create_session(
            VisualBrowserSessionInput(
                created_by="operator_1",
                target_url="https://safe.example.com",
            )
        )
        blocked = service.create_session(
            VisualBrowserSessionInput(
                created_by="operator_1",
                target_url="ftp://token-secret.example.com",
            )
        )
        service.get_session(created.visual_session_id)
        service.revoke_session(created.visual_session_id, actor="operator_1")

        audit = VisualBrowserSessionAuditService(session).get_audit()
        event_types = [event["event_type"] for event in audit.events]
        payload = json.dumps([event["details"] for event in audit.events]).lower()

        assert created.visual_session_id
        assert blocked.status == "blocked"
        assert "visual_browser_session_created" in event_types
        assert "visual_browser_session_blocked" in event_types
        assert "visual_browser_session_retrieved" in event_types
        assert "visual_browser_session_revoked" in event_types
        for forbidden in ["password", "api_key", "token", "secret", "authorization", "credential"]:
            assert forbidden not in payload
    finally:
        session.close()
