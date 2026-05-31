"""Sprint 82 - visual workflow trace service tests."""

from __future__ import annotations

from erpguard.db.session import SessionLocal, init_db
from erpguard.product.visual_browser_session import VisualBrowserSessionInput, VisualBrowserSessionService
from erpguard.product.visual_observation_snapshot import VisualObservationSnapshotInput, VisualObservationSnapshotService
from erpguard.product.visual_workflow_trace import VisualWorkflowTraceInput, VisualWorkflowTraceService
from test_visual_observation_snapshot import _payload


ALLOWED_STEPS = [
    {"step_type": "navigate", "label": "Ir a Ventas > Pedidos", "target_hint": "menu Ventas"},
    {"step_type": "filter", "label": "Filtrar pendientes", "field_hint": "Estado", "value_hint": "Pendiente"},
    {"step_type": "open_record", "label": "Abrir pedido S00001", "record_hint": "S00001"},
    {"step_type": "read_field", "label": "Leer estado", "field_hint": "Estado"},
]


def _db_session_observation():
    init_db()
    db = SessionLocal()
    session = VisualBrowserSessionService(db).create_session(
        VisualBrowserSessionInput(created_by="operator_1", target_url="https://my-erp.example.com")
    )
    observation = VisualObservationSnapshotService(db).create_snapshot(
        VisualObservationSnapshotInput(visual_session_id=session.visual_session_id, **_payload())
    )
    return db, session, observation


def _input(session_id: str, observation_id: str, **overrides):
    payload = {
        "visual_session_id": session_id,
        "created_by": "operator_1",
        "workflow_name": "Revisar pedidos pendientes",
        "workflow_goal": "Detectar pedidos que no se pueden servir",
        "observation_ids": [observation_id],
        "steps": list(ALLOWED_STEPS),
    }
    payload.update(overrides)
    return VisualWorkflowTraceInput(**payload)


def test_creates_workflow_trace_from_visual_session_and_observation_snapshot():
    db, session, observation = _db_session_observation()
    try:
        result = VisualWorkflowTraceService(db).create_trace(_input(session.visual_session_id, observation.observation_id))

        assert result.workflow_trace_id.startswith("vtrace_")
        assert result.status == "created"
        assert result.observation_ids == [observation.observation_id]
        assert len(result.steps) == 4
        assert result.safety_summary["trace_only"] is True
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
        service = VisualWorkflowTraceService(db)

        missing = service.create_trace(_input("vbs_missing", "vobs_missing"))
        revoked_result = service.create_trace(_input(revoked.visual_session_id, "vobs_missing"))
        blocked_result = service.create_trace(_input(blocked.visual_session_id, "vobs_missing"))

        assert missing.blocking_reasons == ["visual_session_not_found"]
        assert revoked_result.blocking_reasons == ["visual_session_revoked"]
        assert blocked_result.blocking_reasons == ["visual_session_blocked"]
    finally:
        db.close()


def test_blocks_required_fields_and_missing_observation_reference():
    db, session, observation = _db_session_observation()
    try:
        service = VisualWorkflowTraceService(db)
        missing_name = service.create_trace(_input(session.visual_session_id, observation.observation_id, workflow_name=""))
        empty_steps = service.create_trace(_input(session.visual_session_id, observation.observation_id, steps=[]))
        missing_observation = service.create_trace(_input(session.visual_session_id, "vobs_missing"))

        assert missing_name.blocking_reasons == ["workflow_name_required"]
        assert empty_steps.blocking_reasons == ["steps_required"]
        assert missing_observation.blocking_reasons == ["observation_not_found"]
    finally:
        db.close()


def test_blocks_non_created_observation_reference():
    db, session, _observation = _db_session_observation()
    try:
        blocked_observation = VisualObservationSnapshotService(db).create_snapshot(
            VisualObservationSnapshotInput(
                visual_session_id=session.visual_session_id,
                created_by="operator_1",
                screen_summary={},
                dom_summary={},
                visible_text=[],
            )
        )
        result = VisualWorkflowTraceService(db).create_trace(
            _input(session.visual_session_id, blocked_observation.observation_id)
        )

        assert result.blocking_reasons == ["observation_not_created"]
    finally:
        db.close()


def test_blocks_all_blocked_step_types():
    db, session, observation = _db_session_observation()
    try:
        service = VisualWorkflowTraceService(db)
        blocked_types = [
            "click", "submit_form", "write_field", "create_record", "update_record",
            "delete_record", "confirm_order", "post_invoice", "reconcile_payment",
            "move_stock", "complete_manufacturing", "send_email",
        ]
        for step_type in blocked_types:
            result = service.create_trace(
                _input(session.visual_session_id, observation.observation_id, steps=[{"step_type": step_type, "label": step_type}])
            )
            assert result.blocking_reasons == ["blocked_step_type_supplied"]
    finally:
        db.close()


def test_redacts_secret_markers_and_blocks_credential_values():
    db, session, observation = _db_session_observation()
    try:
        service = VisualWorkflowTraceService(db)
        redacted = service.create_trace(
            _input(
                session.visual_session_id,
                observation.observation_id,
                workflow_goal="review token marker",
                steps=[{"step_type": "note", "label": "api_key marker only"}],
            )
        )
        blocked = service.create_trace(
            _input(
                session.visual_session_id,
                observation.observation_id,
                steps=[{"step_type": "note", "label": "Login", "credential_touchpoint": {"field_label": "Password", "touchpoint_type": "login", "value": "secret"}}],
            )
        )

        assert redacted.workflow_goal == "<redacted>"
        assert redacted.steps[0]["label"] == "<redacted>"
        assert blocked.blocking_reasons == ["credential_value_supplied"]
    finally:
        db.close()


def test_credential_touchpoints_are_metadata_only_and_safety_flags_false():
    db, session, observation = _db_session_observation()
    try:
        result = VisualWorkflowTraceService(db).create_trace(
            _input(
                session.visual_session_id,
                observation.observation_id,
                steps=[{"step_type": "note", "label": "Login noted", "credential_touchpoint": {"field_label": "Login field", "touchpoint_type": "field_seen", "value_present": True}}],
            )
        )
        touchpoint = result.credential_touchpoints[0]
        safety = result.safety_summary

        assert touchpoint["value_stored"] is False
        assert "value" not in touchpoint
        assert safety["browser_launched"] is False
        assert safety["browser_control_performed"] is False
        assert safety["automatic_clicks_performed"] is False
        assert safety["form_submission_performed"] is False
        assert safety["action_execution_performed"] is False
        assert safety["dom_observation_performed"] is False
        assert safety["screen_capture_performed"] is False
        assert safety["workflow_recording_performed"] is False
        assert safety["simulated_workflow_recording"] is True
        assert safety["credentials_exposed"] is False
        assert safety["raw_secret_accessed"] is False
        assert safety["mcp_execution_performed"] is False
        assert safety["scheduler_used"] is False
        assert safety["erp_write_performed"] is False
    finally:
        db.close()
