from __future__ import annotations

from erpguard.db.session import SessionLocal, init_db
from erpguard.product.agent_builder_session import AgentBuilderSessionService


def test_create_builder_session_starts_safe_created_state():
    init_db()
    session = SessionLocal()
    try:
        builder = AgentBuilderSessionService(session)
        created = builder.create({"type": "user", "id": "operator_1", "display_name": "Operator"})

        assert created.session_id.startswith("builder_")
        assert created.status == "created"
        assert created.next_step == "select_template"
        assert created.safety.generic_writes_enabled is False
        assert created.safety.r3_r4_writes_enabled is False
        assert created.safety.freeform_tool_execution_enabled is False
    finally:
        session.close()


def test_builder_state_progresses_through_template_connector_trigger_inputs_steps_and_guards():
    init_db()
    session = SessionLocal()
    try:
        builder = AgentBuilderSessionService(session)
        created = builder.create({"type": "user", "id": "operator_1", "display_name": "Operator"})
        builder.select_template(created.session_id, "odoo_formula_preflight")
        builder.select_connector(created.session_id, "odoo")
        builder.configure_trigger(created.session_id, {"type": "manual", "label": "Operator starts preflight"})
        builder.configure_inputs(created.session_id, {"connection_id": "conn_demo", "order_reference": "S00042"})
        builder.configure_steps(created.session_id, ["load_context", "read_record", "run_guard", "produce_decision"])
        updated = builder.configure_guards(
            created.session_id,
            ["no_generic_writes", "no_r3_r4_writes", "no_raw_tool_execution", "requires_human_review", "formula_guard", "odoo_readonly_guard"],
        )

        assert updated.status == "guards_configured"
        assert updated.template_id == "odoo_formula_preflight"
        assert updated.connector_id == "odoo"
        assert updated.trigger["type"] == "manual"
        assert "run_guard" in [step["type"] for step in updated.steps]
        assert "formula_guard" in updated.guards
    finally:
        session.close()


def test_builder_timeline_records_events_in_order():
    init_db()
    session = SessionLocal()
    try:
        builder = AgentBuilderSessionService(session)
        created = builder.create({"type": "user", "id": "operator_1", "display_name": "Operator"})
        builder.select_template(created.session_id, "odoo_formula_preflight")
        builder.select_connector(created.session_id, "odoo")

        timeline = builder.timeline(created.session_id)

        assert [event.event_type for event in timeline][:3] == ["session_created", "template_selected", "connector_selected"]
        assert all(event.status == "ok" for event in timeline)
    finally:
        session.close()
