from __future__ import annotations

from erpguard.db.session import SessionLocal, init_db
from erpguard.product.agent_builder_preview import AgentBuilderPreviewService
from erpguard.product.agent_builder_session import AgentBuilderSessionService


def test_preview_generates_safe_workflow_json():
    init_db()
    session = SessionLocal()
    try:
        builder = AgentBuilderSessionService(session)
        created = builder.create({"type": "user", "id": "operator_1", "display_name": "Operator"})
        builder.select_template(created.session_id, "odoo_formula_preflight")
        builder.select_connector(created.session_id, "odoo")
        builder.configure_trigger(created.session_id, {"type": "manual"})
        builder.configure_inputs(created.session_id, {"connection_id": "conn_demo", "order_reference": "S00042"})
        builder.configure_steps(created.session_id, ["load_context", "read_record", "run_guard", "produce_decision", "produce_audit_summary"])
        builder.configure_guards(created.session_id, ["no_generic_writes", "no_r3_r4_writes", "no_raw_tool_execution", "requires_human_review", "formula_guard", "odoo_readonly_guard"])

        preview = AgentBuilderPreviewService(session).preview(created.session_id)

        assert preview.session_id == created.session_id
        assert preview.runtime_mode == "dry_run_only"
        assert preview.write_actions is False
        assert preview.safety.can_execute_real_writes is False
        assert preview.workflow["template_id"] == "odoo_formula_preflight"
        assert [step["type"] for step in preview.workflow["steps"]] == [
            "load_context",
            "read_record",
            "run_guard",
            "produce_decision",
            "produce_audit_summary",
        ]
    finally:
        session.close()
