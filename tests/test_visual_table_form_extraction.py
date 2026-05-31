"""Sprint 83 - visual table/form extraction service tests."""

from __future__ import annotations

from erpguard.db.session import SessionLocal, init_db
from erpguard.product.visual_browser_session import VisualBrowserSessionInput, VisualBrowserSessionService
from erpguard.product.visual_observation_snapshot import VisualObservationSnapshotInput, VisualObservationSnapshotService
from erpguard.product.visual_table_form_extraction import (
    VisualTableFormExtractionInput,
    VisualTableFormExtractionService,
)
from erpguard.product.visual_workflow_trace import VisualWorkflowTraceInput, VisualWorkflowTraceService


def _db_session_observation_trace(*, tables=None, forms=None, buttons=None):
    init_db()
    db = SessionLocal()
    session = VisualBrowserSessionService(db).create_session(
        VisualBrowserSessionInput(created_by="operator_1", target_url="https://my-erp.example.com")
    )
    observation = VisualObservationSnapshotService(db).create_snapshot(
        VisualObservationSnapshotInput(
            visual_session_id=session.visual_session_id,
            created_by="operator_1",
            screen_summary={"title": "Pedidos"},
            dom_summary={"page_type": "list"},
            visible_text=["Pedidos"],
            tables=tables or [{"label": "Pedidos", "columns": ["Referencia", "Cliente", "Estado", "Total"], "row_count": 12}],
            forms=forms or [{"label": "Pedido", "fields": [{"field_label": "Cliente", "field_type": "text", "value": "ACME"}], "field_count": 1}],
            buttons=buttons or [{"label": "Crear"}, {"label": "Confirmar"}, {"label": "Delete"}],
        )
    )
    trace = VisualWorkflowTraceService(db).create_trace(
        VisualWorkflowTraceInput(
            visual_session_id=session.visual_session_id,
            created_by="operator_1",
            workflow_name="Revisar pedidos",
            workflow_goal="Extraer estructura",
            observation_ids=[observation.observation_id],
            steps=[{"step_type": "read_table", "label": "Leer tabla"}],
        )
    )
    return db, session, observation, trace


def _extract(db, observation_id, **kwargs):
    return VisualTableFormExtractionService(db).create_extraction(
        VisualTableFormExtractionInput(
            observation_id=observation_id,
            created_by=kwargs.get("created_by", "operator_1"),
            workflow_trace_id=kwargs.get("workflow_trace_id", ""),
            extraction_goal=kwargs.get("extraction_goal", "Extract visible order list structure"),
        )
    )


def test_creates_extraction_from_observation_snapshot():
    db, _session, observation, trace = _db_session_observation_trace()
    try:
        result = _extract(db, observation.observation_id, workflow_trace_id=trace.workflow_trace_id)

        assert result.extraction_id.startswith("vextract_")
        assert result.status == "created"
        assert result.observation_id == observation.observation_id
        assert result.workflow_trace_id == trace.workflow_trace_id
        assert result.table_structures
        assert result.form_structures
        assert result.button_structures
    finally:
        db.close()


def test_blocks_missing_or_non_created_observation_and_bad_workflow_trace():
    db, session, observation, trace = _db_session_observation_trace()
    try:
        blocked_observation = VisualObservationSnapshotService(db).create_snapshot(
            VisualObservationSnapshotInput(visual_session_id=session.visual_session_id, created_by="operator_1")
        )
        other_session = VisualBrowserSessionService(db).create_session(
            VisualBrowserSessionInput(created_by="operator_1", target_url="https://other.example.com")
        )
        other_observation = VisualObservationSnapshotService(db).create_snapshot(
            VisualObservationSnapshotInput(
                visual_session_id=other_session.visual_session_id,
                created_by="operator_1",
                screen_summary={"title": "Other"},
                visible_text=["Other"],
            )
        )
        other_trace = VisualWorkflowTraceService(db).create_trace(
            VisualWorkflowTraceInput(
                visual_session_id=other_session.visual_session_id,
                workflow_name="Other",
                observation_ids=[other_observation.observation_id],
                steps=[{"step_type": "note", "label": "Other"}],
            )
        )
        blocked_trace = VisualWorkflowTraceService(db).create_trace(
            VisualWorkflowTraceInput(
                visual_session_id=session.visual_session_id,
                workflow_name="Bad",
                observation_ids=[observation.observation_id],
                steps=[{"step_type": "click", "label": "Click"}],
            )
        )

        assert _extract(db, "vobs_missing").blocking_reasons == ["observation_not_found"]
        assert _extract(db, blocked_observation.observation_id).blocking_reasons == ["observation_not_created"]
        assert _extract(db, observation.observation_id, workflow_trace_id="vtrace_missing").blocking_reasons == ["workflow_trace_not_found"]
        assert _extract(db, observation.observation_id, workflow_trace_id=blocked_trace.workflow_trace_id).blocking_reasons == ["workflow_trace_not_created"]
        assert _extract(db, observation.observation_id, workflow_trace_id=other_trace.workflow_trace_id).blocking_reasons == ["workflow_trace_session_mismatch"]
    finally:
        db.close()


def test_infers_supported_business_object_hints_from_tables():
    cases = [
        (["Referencia", "Pedido", "Cliente", "Estado", "Total"], "sale_order"),
        (["Factura", "Cliente", "Total", "Pendiente", "Fecha"], "invoice"),
        (["Producto", "Cantidad", "Ubicación", "Reservado"], "stock_item"),
        (["Producto", "Estado", "Cantidad", "Lista de materiales"], "manufacturing_order"),
        (["Nombre", "Email", "Teléfono", "Empresa"], "partner"),
        (["Producto", "Código", "Precio", "Disponible"], "product"),
    ]
    for columns, expected in cases:
        db, _session, observation, _trace = _db_session_observation_trace(
            tables=[{"label": expected, "columns": columns, "row_count": 1}]
        )
        try:
            result = _extract(db, observation.observation_id)
            assert result.table_structures[0]["likely_object_type"] == expected
            assert result.table_structures[0]["confidence"] > 0
        finally:
            db.close()


def test_buttons_are_never_auto_executable_and_dangerous_buttons_are_high_risk():
    db, _session, observation, _trace = _db_session_observation_trace(buttons=[{"label": "Crear"}, {"label": "Confirmar"}, {"label": "Delete"}])
    try:
        result = _extract(db, observation.observation_id)

        assert all(button["auto_execute_allowed"] is False for button in result.button_structures)
        dangerous = [button for button in result.button_structures if button["is_dangerous"]]
        assert dangerous
        assert all(button["risk_level"] == "high" for button in dangerous)
        assert all(button["requires_human_approval"] is True for button in dangerous)
    finally:
        db.close()


def test_form_field_values_are_not_persisted_and_credential_values_block():
    db, _session, observation, _trace = _db_session_observation_trace(
        forms=[{"label": "Partner", "fields": [{"field_label": "Nombre", "field_type": "text", "value": "ACME"}]}]
    )
    try:
        result = _extract(db, observation.observation_id)
        field = result.form_structures[0]["fields"][0]
        assert "value" not in field
        assert field["value_redacted"] is True
    finally:
        db.close()

    db, _session, observation, _trace = _db_session_observation_trace(
        forms=[{"label": "Login", "fields": [{"field_label": "Password", "field_type": "password", "value": "secret"}]}]
    )
    try:
        blocked = _extract(db, observation.observation_id)
        assert blocked.blocking_reasons == ["credential_value_detected"]
    finally:
        db.close()


def test_redacts_secret_markers_and_safety_summary_flags():
    db, _session, observation, _trace = _db_session_observation_trace(
        tables=[{"label": "token table", "columns": ["Referencia"], "row_count": 1}]
    )
    try:
        result = _extract(db, observation.observation_id, extraction_goal="secret marker")
        safety = result.safety_summary

        assert result.extraction_goal == "<redacted>"
        assert result.table_structures[0]["label"] == "<redacted>"
        assert safety["extraction_only"] is True
        assert safety["browser_launched"] is False
        assert safety["browser_control_performed"] is False
        assert safety["automatic_clicks_performed"] is False
        assert safety["form_submission_performed"] is False
        assert safety["action_execution_performed"] is False
        assert safety["real_dom_inspection_performed"] is False
        assert safety["real_screen_capture_performed"] is False
        assert safety["workflow_recording_performed"] is False
        assert safety["credentials_exposed"] is False
        assert safety["raw_secret_accessed"] is False
        assert safety["mcp_execution_performed"] is False
        assert safety["scheduler_used"] is False
        assert safety["erp_write_performed"] is False
    finally:
        db.close()
