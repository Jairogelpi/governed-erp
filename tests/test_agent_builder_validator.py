from __future__ import annotations

from erpguard.db.session import SessionLocal, init_db
from erpguard.product.agent_builder_session import AgentBuilderSessionService
from erpguard.product.agent_builder_validator import AgentBuilderValidator


def _session_with_basics(session):
    builder = AgentBuilderSessionService(session)
    created = builder.create({"type": "user", "id": "operator_1", "display_name": "Operator"})
    builder.select_template(created.session_id, "odoo_formula_preflight")
    builder.select_connector(created.session_id, "odoo")
    builder.configure_trigger(created.session_id, {"type": "manual"})
    builder.configure_inputs(created.session_id, {"connection_id": "conn_demo"})
    return builder, created.session_id


def test_validator_blocks_forbidden_step_type():
    init_db()
    session = SessionLocal()
    try:
        builder, session_id = _session_with_basics(session)
        builder.configure_steps(session_id, ["load_context", "shell_command"])
        builder.configure_guards(session_id, ["no_generic_writes", "no_r3_r4_writes", "no_raw_tool_execution", "requires_human_review", "formula_guard", "odoo_readonly_guard"])

        result = AgentBuilderValidator(session).validate(session_id)

        assert result.passed is False
        assert "forbidden_step_type" in [issue.code for issue in result.issues]
    finally:
        session.close()


def test_validator_blocks_missing_mandatory_guards():
    init_db()
    session = SessionLocal()
    try:
        builder, session_id = _session_with_basics(session)
        builder.configure_steps(session_id, ["load_context", "read_record", "run_guard"])
        builder.configure_guards(session_id, ["formula_guard"])

        result = AgentBuilderValidator(session).validate(session_id)

        assert result.passed is False
        assert "missing_mandatory_guard" in [issue.code for issue in result.issues]
    finally:
        session.close()


def test_validator_passes_safe_builder_session_and_records_requirement_result():
    init_db()
    session = SessionLocal()
    try:
        builder, session_id = _session_with_basics(session)
        builder.configure_steps(session_id, ["load_context", "read_record", "run_guard", "produce_decision"])
        builder.configure_guards(session_id, ["no_generic_writes", "no_r3_r4_writes", "no_raw_tool_execution", "requires_human_review", "formula_guard", "odoo_readonly_guard"])

        result = AgentBuilderValidator(session).validate(session_id)

        assert result.passed is True
        assert result.runtime_mode == "dry_run_only"
        assert result.write_actions is False
        assert result.requires_review is True
        assert result.requires_compile is True
        assert result.requires_approval is True
    finally:
        session.close()
