from __future__ import annotations

from erpguard.db.repositories import get_automation_draft
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.agent_builder_draft_exporter import AgentBuilderDraftExporter
from erpguard.product.agent_builder_session import AgentBuilderSessionService
from erpguard.product.draft_validator import DraftValidatorService


def test_exporter_saves_valid_builder_session_as_safe_automation_draft():
    init_db()
    session = SessionLocal()
    try:
        builder = AgentBuilderSessionService(session)
        created = builder.create({"type": "user", "id": "operator_1", "display_name": "Operator"})
        builder.select_template(created.session_id, "odoo_formula_preflight")
        builder.select_connector(created.session_id, "odoo")
        builder.configure_trigger(created.session_id, {"type": "manual"})
        builder.configure_inputs(created.session_id, {"connection_id": "conn_demo", "order_reference": "S00042"})
        builder.configure_steps(created.session_id, ["load_context", "read_record", "run_guard", "produce_decision"])
        builder.configure_guards(created.session_id, ["no_generic_writes", "no_r3_r4_writes", "no_raw_tool_execution", "requires_human_review", "formula_guard", "odoo_readonly_guard"])
        builder.check_requirements(created.session_id)

        result = AgentBuilderDraftExporter(session).save_draft(created.session_id)

        assert result.status == "saved_as_draft"
        assert result.automation_draft_id.startswith("automation_draft_")
        assert result.runtime_mode == "dry_run_only"
        assert result.write_actions is False
        assert result.safety.requires_review is True
        assert result.safety.requires_compile is True
        assert result.safety.requires_approval is True

        draft = get_automation_draft(session, result.automation_draft_id)
        assert draft is not None
        assert draft.write_actions is False
        assert DraftValidatorService(session).validate(draft.id).passed is True
    finally:
        session.close()
