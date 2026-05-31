"""Sprint 81 - visual observation snapshot service tests."""

from __future__ import annotations

from erpguard.db.session import SessionLocal, init_db
from erpguard.product.visual_browser_session import (
    VisualBrowserSessionInput,
    VisualBrowserSessionService,
)
from erpguard.product.visual_observation_snapshot import (
    VisualObservationSnapshotInput,
    VisualObservationSnapshotService,
)


def _db_and_session():
    init_db()
    db = SessionLocal()
    session = VisualBrowserSessionService(db).create_session(
        VisualBrowserSessionInput(
            created_by="operator_1",
            target_url="https://my-erp.example.com/web",
            intended_erp_hint="odoo",
        )
    )
    return db, session


def _payload(**overrides):
    payload = {
        "created_by": "operator_1",
        "observation_source": "mocked_payload",
        "screen_summary": {"title": "Pedidos", "url_path": "/web#model=sale.order"},
        "dom_summary": {"page_type": "list", "framework_hint": "odoo"},
        "visible_text": ["Pedidos", "S00001", "Cliente", "Total"],
        "tables": [{"label": "Pedidos", "columns": ["Referencia", "Cliente"], "row_count": 12}],
        "forms": [{"label": "Filtro", "field_count": 1}],
        "buttons": [{"label": "Crear"}, {"label": "Confirmar"}, {"label": "Publicar"}, {"label": "Delete"}],
        "credential_fields_detected": [{"field_label": "Password", "field_type": "password", "value_present": False}],
        "dangerous_action_candidates": [],
    }
    payload.update(overrides)
    return payload


def _create(service, visual_session_id, payload):
    return service.create_snapshot(
        VisualObservationSnapshotInput(
            visual_session_id=visual_session_id,
            **payload,
        )
    )


def test_creates_observation_snapshot_from_visual_session_and_detects_dangerous_buttons():
    db, session = _db_and_session()
    try:
        result = _create(VisualObservationSnapshotService(db), session.visual_session_id, _payload())

        assert result.observation_id.startswith("vobs_")
        assert result.status == "created"
        assert result.target_host == "my-erp.example.com"
        assert result.detected_tables[0]["row_count"] == 12
        assert result.detected_forms[0]["field_count"] == 1
        labels = {item["label"] for item in result.dangerous_action_candidates}
        assert {"Confirmar", "Publicar", "Delete"}.issubset(labels)
        for candidate in result.dangerous_action_candidates:
            assert candidate["risk_level"] == "high"
            assert candidate["requires_human_approval"] is True
            assert candidate["auto_execute_allowed"] is False
    finally:
        db.close()


def test_blocks_missing_revoked_and_blocked_visual_sessions():
    init_db()
    db = SessionLocal()
    try:
        browser = VisualBrowserSessionService(db)
        revoked = browser.create_session(VisualBrowserSessionInput(created_by="operator_1"))
        browser.revoke_session(revoked.visual_session_id, actor="operator_1")
        blocked = browser.create_session(VisualBrowserSessionInput(created_by=""))
        service = VisualObservationSnapshotService(db)

        missing_result = _create(service, "vbs_missing", _payload())
        revoked_result = _create(service, revoked.visual_session_id, _payload())
        blocked_result = _create(service, blocked.visual_session_id, _payload())

        assert missing_result.blocking_reasons == ["visual_session_not_found"]
        assert revoked_result.blocking_reasons == ["visual_session_revoked"]
        assert blocked_result.blocking_reasons == ["visual_session_blocked"]
    finally:
        db.close()


def test_blocks_missing_observation_payload():
    db, session = _db_and_session()
    try:
        result = _create(
            VisualObservationSnapshotService(db),
            session.visual_session_id,
            _payload(screen_summary={}, dom_summary={}, visible_text=[], tables=[], forms=[], buttons=[]),
        )

        assert result.status == "blocked"
        assert result.blocking_reasons == ["observation_payload_required"]
    finally:
        db.close()


def test_redacts_secret_markers_from_text_and_summaries():
    db, session = _db_and_session()
    try:
        result = _create(
            VisualObservationSnapshotService(db),
            session.visual_session_id,
            _payload(
                screen_summary={"title": "token visible", "url_path": "/web"},
                dom_summary={"page_type": "secret panel", "framework_hint": "odoo"},
                visible_text=["normal", "api_key marker only"],
            ),
        )

        assert result.screen_summary["title"] == "<redacted>"
        assert result.dom_summary["page_type"] == "<redacted>"
        assert result.visible_text_redacted == ["normal", "<redacted>"]
        assert set(result.redaction_summary["redacted_fields"])
    finally:
        db.close()


def test_blocks_credential_visibility_and_raw_values():
    db, session = _db_and_session()
    try:
        visible = _create(
            VisualObservationSnapshotService(db),
            session.visual_session_id,
            _payload(credential_fields_detected=[{"field_label": "Password", "field_type": "password", "value_present": True}]),
        )
        raw_value = _create(
            VisualObservationSnapshotService(db),
            session.visual_session_id,
            _payload(credential_fields_detected=[{"field_label": "Token", "field_type": "text", "value": "abc123"}]),
        )

        assert visible.blocking_reasons == ["credential_visibility_forbidden"]
        assert raw_value.blocking_reasons == ["raw_secret_marker_detected"]
    finally:
        db.close()


def test_safety_summary_never_performs_real_browser_or_execution_work():
    db, session = _db_and_session()
    try:
        result = _create(VisualObservationSnapshotService(db), session.visual_session_id, _payload())
        safety = result.safety_summary

        assert safety["observation_only"] is True
        assert safety["browser_launched"] is False
        assert safety["browser_control_performed"] is False
        assert safety["automatic_clicks_performed"] is False
        assert safety["form_submission_performed"] is False
        assert safety["action_execution_performed"] is False
        assert safety["dom_observation_performed"] is False
        assert safety["simulated_dom_observation"] is True
        assert safety["screen_capture_performed"] is False
        assert safety["simulated_screen_observation"] is True
        assert safety["workflow_recording_performed"] is False
        assert safety["credentials_exposed"] is False
        assert safety["raw_secret_accessed"] is False
        assert safety["mcp_execution_performed"] is False
        assert safety["scheduler_used"] is False
        assert safety["erp_write_performed"] is False
    finally:
        db.close()
