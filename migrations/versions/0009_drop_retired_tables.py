"""Drop the 95 orphaned tables identified by the C8.1 ORM audit.
This is a destructive, irreversible-for-data migration: downgrade
recreates the tables with their original schema but empty. It does
not and cannot restore dropped rows.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0009_drop_retired_tables"
down_revision = "0008_candidate_integrity"
branch_labels = None
depends_on = None


DROP_TABLES = [
    "action_dispatch_eligibility_events",
    "action_dispatch_execution_audit_events",
    "action_dispatch_result_records",
    "action_plan_step_tokens",
    "active_skill_runs",
    "active_skill_run_events",
    "advisory_proposals",
    "advisory_sessions",
    "agent_builder_events",
    "agent_builder_sessions",
    "agent_candidate_activation_events",
    "agent_candidate_activation_requests",
    "agent_candidate_activation_request_events",
    "agent_candidate_approval_events",
    "agent_candidate_approval_packets",
    "agent_candidate_decisions",
    "agent_candidate_decision_events",
    "agent_draft_bridge_events",
    "agent_draft_handoff_events",
    "agent_draft_handoff_packets",
    "agent_handoff_version_events",
    "agent_handoff_version_links",
    "agent_proposal_draft_links",
    "agent_skill_run_preview_events",
    "audit_exports",
    "clarification_answers",
    "clarification_audit_events",
    "connector_auth_profiles",
    "connector_credential_audit_events",
    "connector_read_evidence",
    "connector_setup_audit_events",
    "connector_setup_sessions",
    "credential_vault_audit_events",
    "credential_vault_entries",
    "erp_fingerprinting_audit_events",
    "erp_fingerprinting_plans",
    "execution_requests",
    "execution_runs",
    "external_connector_audit_events",
    "fake_erp_execution_audit_events",
    "fake_erp_execution_evidence",
    "fake_erp_execution_evidence_packs",
    "fake_erp_execution_records",
    "fake_erp_regression_audit_events",
    "fake_erp_regression_cases",
    "fake_erp_regression_runs",
    "generated_capability_audit_events",
    "generated_capability_sets",
    "invariant_results",
    "kill_switch_events",
    "manual_dry_run_audit_events",
    "manual_dry_run_evidence",
    "mapping_confirmations",
    "oauth_states",
    "oauth_token_records",
    "odoo_connection_tests",
    "odoo_connection_test_audit_events",
    "odoo_read_evidence_audit_events",
    "odoo_read_evidence_packs",
    "odoo_read_mappings",
    "odoo_read_mapping_audit_events",
    "odoo_read_only_adapter_audit_events",
    "odoo_read_only_adapter_sessions",
    "odoo_read_only_demo_audit_events",
    "odoo_read_only_demo_flows",
    "operator_action_plan_events",
    "operator_console_queries",
    "operator_console_sessions",
    "operator_evidence_packs",
    "platform_audit_events",
    "preflight_cases",
    "r2_evidence_reviews",
    "r2_execution_reports",
    "r2_promotion_gates",
    "r2_rollback_rehearsals",
    "r2_write_pilot_evidence",
    "read_only_connector_activations",
    "read_only_connector_activation_audit_events",
    "read_only_connector_activation_requests",
    "safe_discovery_audit_events",
    "safe_discovery_plans",
    "skill_run_queue_entries",
    "skill_schedules",
    "skill_schedule_events",
    "ui_skill_version_events",
    "ui_skill_version_records",
    "visual_browser_sessions",
    "visual_browser_session_audit_events",
    "visual_observation_audit_events",
    "visual_observation_snapshots",
    "visual_table_form_extractions",
    "visual_table_form_extraction_audit_events",
    "visual_workflow_traces",
    "visual_workflow_trace_audit_events",
    "write_pilot_evidence",
]


def upgrade() -> None:
    bind = op.get_bind()
    existing = set(inspect(bind).get_table_names())
    for name in DROP_TABLES:
        if name in existing:
            op.drop_table(name)


def downgrade() -> None:
    """Schema-only downgrade: recreates empty tables, data is gone."""
    bind = op.get_bind()
    existing = set(inspect(bind).get_table_names())

    if "action_dispatch_eligibility_events" not in existing:
        op.create_table(
            "action_dispatch_eligibility_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("action_key", sa.Text(), nullable=False, default='unknown'),
            sa.Column("endpoint_hint", sa.Text(), nullable=False, default=''),
            sa.Column("token_id", sa.Text(), nullable=True),
            sa.Column("version_id", sa.Text(), nullable=True),
            sa.Column("eligible", sa.Boolean(), nullable=False, default=False),
            sa.Column("blocked_reason", sa.Text(), nullable=True),
            sa.Column("policy_name", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "action_dispatch_execution_audit_events" not in existing:
        op.create_table(
            "action_dispatch_execution_audit_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("dispatch_id", sa.Text(), nullable=False),
            sa.Column("action_key", sa.Text(), nullable=False, default='unknown'),
            sa.Column("event_type", sa.Text(), nullable=False, default='requested'),
            sa.Column("status", sa.Text(), nullable=False, default='blocked'),
            sa.Column("handler_type", sa.Text(), nullable=False, default='internal_read_only'),
            sa.Column("endpoint_hint", sa.Text(), nullable=False, default=''),
            sa.Column("method_hint", sa.Text(), nullable=False, default='GET'),
            sa.Column("token_id", sa.Text(), nullable=True),
            sa.Column("version_id", sa.Text(), nullable=True),
            sa.Column("detail_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "action_dispatch_result_records" not in existing:
        op.create_table(
            "action_dispatch_result_records",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("action_key", sa.Text(), nullable=False, default='unknown'),
            sa.Column("status", sa.Text(), nullable=False, default='blocked'),
            sa.Column("handler_type", sa.Text(), nullable=False, default='internal_read_only'),
            sa.Column("endpoint_hint", sa.Text(), nullable=False, default=''),
            sa.Column("method_hint", sa.Text(), nullable=False, default='GET'),
            sa.Column("token_id", sa.Text(), nullable=True),
            sa.Column("version_id", sa.Text(), nullable=True),
            sa.Column("parameters_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("result_payload_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("result_summary", sa.Text(), nullable=False, default=''),
            sa.Column("blocking_reasons_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("token_confirmed", sa.Boolean(), nullable=False, default=False),
            sa.Column("eligibility_passed", sa.Boolean(), nullable=False, default=False),
            sa.Column("dispatch_performed", sa.Boolean(), nullable=False, default=False),
            sa.Column("erp_writes_performed", sa.Boolean(), nullable=False, default=False),
            sa.Column("browser_control_performed", sa.Boolean(), nullable=False, default=False),
            sa.Column("mcp_execution_performed", sa.Boolean(), nullable=False, default=False),
            sa.Column("llm_runtime_used", sa.Boolean(), nullable=False, default=False),
            sa.Column("system_state_mutated", sa.Boolean(), nullable=False, default=False),
            sa.Column("skill_mutated", sa.Boolean(), nullable=False, default=False),
            sa.Column("activation_performed", sa.Boolean(), nullable=False, default=False),
            sa.Column("scheduling_performed", sa.Boolean(), nullable=False, default=False),
            sa.Column("audit_recorded", sa.Boolean(), nullable=False, default=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "action_plan_step_tokens" not in existing:
        op.create_table(
            "action_plan_step_tokens",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("plan_id", sa.Text(), nullable=False),
            sa.Column("step_number", sa.Integer(), nullable=False, default=0),
            sa.Column("step_title", sa.Text(), nullable=False, default=''),
            sa.Column("endpoint_hint", sa.Text(), nullable=False, default=''),
            sa.Column("method_hint", sa.Text(), nullable=False, default='GET'),
            sa.Column("severity", sa.Text(), nullable=False, default='required'),
            sa.Column("risk_level", sa.Text(), nullable=False, default='low'),
            sa.Column("risk_summary", sa.Text(), nullable=False, default=''),
            sa.Column("status", sa.Text(), nullable=False, default='pending'),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "active_skill_runs" not in existing:
        op.create_table(
            "active_skill_runs",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("version_id", sa.Text(), nullable=False),
            sa.Column("skill_id", sa.Text(), nullable=False),
            sa.Column("actor", sa.Text(), nullable=False, default='manual_operator'),
            sa.Column("trigger", sa.Text(), nullable=False, default='manual'),
            sa.Column("status", sa.Text(), nullable=False, default='requested'),
            sa.Column("target_base_url", sa.Text(), nullable=False),
            sa.Column("inputs_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("replay_run_id", sa.Text(), nullable=True),
            sa.Column("gate_result_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("input_validation_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("summary_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "active_skill_run_events" not in existing:
        op.create_table(
            "active_skill_run_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("run_id", sa.Text(), nullable=False),
            sa.Column("event_type", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False, default='info'),
            sa.Column("detail", sa.Text(), nullable=False, default=''),
            sa.Column("payload_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "advisory_proposals" not in existing:
        op.create_table(
            "advisory_proposals",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("session_id", sa.Text(), nullable=False),
            sa.Column("request_text", sa.Text(), nullable=False),
            sa.Column("intent_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("process_category", sa.Text(), nullable=False, default='unknown'),
            sa.Column("entity_mappings_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("workflow_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("guards_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("risk_summary_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("clarification_questions_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("revision_number", sa.Integer(), nullable=False, default=1),
            sa.Column("status", sa.Text(), nullable=False, default='draft'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "advisory_sessions" not in existing:
        op.create_table(
            "advisory_sessions",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("request_text", sa.Text(), nullable=False, default=''),
            sa.Column("latest_proposal_id", sa.Text(), nullable=True),
            sa.Column("created_by_actor_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "agent_builder_events" not in existing:
        op.create_table(
            "agent_builder_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("session_id", sa.Text(), nullable=False),
            sa.Column("event_type", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("input_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("output_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("error_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "agent_builder_sessions" not in existing:
        op.create_table(
            "agent_builder_sessions",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("template_id", sa.Text(), nullable=True),
            sa.Column("connector_id", sa.Text(), nullable=True),
            sa.Column("trigger_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("inputs_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("outputs_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("steps_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("guards_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("requirement_result_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("safety_preview_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("automation_draft_id", sa.Text(), nullable=True),
            sa.Column("created_by_actor_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "agent_candidate_activation_events" not in existing:
        op.create_table(
            "agent_candidate_activation_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("version_id", sa.Text(), nullable=False),
            sa.Column("skill_id", sa.Text(), nullable=False),
            sa.Column("step", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("detail_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "agent_candidate_activation_requests" not in existing:
        op.create_table(
            "agent_candidate_activation_requests",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("version_id", sa.Text(), nullable=False),
            sa.Column("skill_id", sa.Text(), nullable=False),
            sa.Column("requested_by", sa.Text(), nullable=False),
            sa.Column("rationale", sa.Text(), nullable=False, default=''),
            sa.Column("request_status", sa.Text(), nullable=False, default='pending_review'),
            sa.Column("detail_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "agent_candidate_activation_request_events" not in existing:
        op.create_table(
            "agent_candidate_activation_request_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("version_id", sa.Text(), nullable=False),
            sa.Column("step", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("detail_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "agent_candidate_approval_events" not in existing:
        op.create_table(
            "agent_candidate_approval_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("version_id", sa.Text(), nullable=False),
            sa.Column("step", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("detail_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "agent_candidate_approval_packets" not in existing:
        op.create_table(
            "agent_candidate_approval_packets",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("version_id", sa.Text(), nullable=False),
            sa.Column("skill_id", sa.Text(), nullable=False),
            sa.Column("packet_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("status", sa.Text(), nullable=False, default='pending_human_review'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "agent_candidate_decisions" not in existing:
        op.create_table(
            "agent_candidate_decisions",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("version_id", sa.Text(), nullable=False),
            sa.Column("decision", sa.Text(), nullable=False),
            sa.Column("actor", sa.Text(), nullable=False),
            sa.Column("rationale", sa.Text(), nullable=False, default=''),
            sa.Column("detail_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "agent_candidate_decision_events" not in existing:
        op.create_table(
            "agent_candidate_decision_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("version_id", sa.Text(), nullable=False),
            sa.Column("step", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("detail_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "agent_draft_bridge_events" not in existing:
        op.create_table(
            "agent_draft_bridge_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("draft_id", sa.Text(), nullable=False),
            sa.Column("proposal_id", sa.Text(), nullable=False),
            sa.Column("step", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("detail_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "agent_draft_handoff_events" not in existing:
        op.create_table(
            "agent_draft_handoff_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("draft_id", sa.Text(), nullable=False),
            sa.Column("proposal_id", sa.Text(), nullable=False),
            sa.Column("step", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("detail_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "agent_draft_handoff_packets" not in existing:
        op.create_table(
            "agent_draft_handoff_packets",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("draft_id", sa.Text(), nullable=False),
            sa.Column("proposal_id", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False, default='pending_human_review'),
            sa.Column("packet_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "agent_handoff_version_events" not in existing:
        op.create_table(
            "agent_handoff_version_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("packet_id", sa.Text(), nullable=False),
            sa.Column("step", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("detail_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "agent_handoff_version_links" not in existing:
        op.create_table(
            "agent_handoff_version_links",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("packet_id", sa.Text(), nullable=False),
            sa.Column("draft_id", sa.Text(), nullable=False),
            sa.Column("proposal_id", sa.Text(), nullable=False),
            sa.Column("version_id", sa.Text(), nullable=False),
            sa.Column("skill_id", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "agent_proposal_draft_links" not in existing:
        op.create_table(
            "agent_proposal_draft_links",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("proposal_id", sa.Text(), nullable=False),
            sa.Column("draft_id", sa.Text(), nullable=False),
            sa.Column("session_id", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "agent_skill_run_preview_events" not in existing:
        op.create_table(
            "agent_skill_run_preview_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("version_id", sa.Text(), nullable=False),
            sa.Column("skill_id", sa.Text(), nullable=False),
            sa.Column("step", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("detail_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "audit_exports" not in existing:
        op.create_table(
            "audit_exports",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("tenant_id", sa.Text(), nullable=False),
            sa.Column("export_type", sa.Text(), nullable=False),
            sa.Column("filters_json", sa.Text(), nullable=False),
            sa.Column("record_count", sa.Integer(), nullable=False, default=0),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("result_json", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "clarification_answers" not in existing:
        op.create_table(
            "clarification_answers",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("proposal_id", sa.Text(), nullable=False),
            sa.Column("question_id", sa.Text(), nullable=False),
            sa.Column("answer_text", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "clarification_audit_events" not in existing:
        op.create_table(
            "clarification_audit_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("proposal_id", sa.Text(), nullable=False),
            sa.Column("event_type", sa.Text(), nullable=False),
            sa.Column("detail_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "connector_auth_profiles" not in existing:
        op.create_table(
            "connector_auth_profiles",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("connector_id", sa.Text(), nullable=False),
            sa.Column("display_name", sa.Text(), nullable=False),
            sa.Column("auth_type", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("requested_scopes_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("credential_ref", sa.Text(), nullable=False),
            sa.Column("secret_fingerprint", sa.Text(), nullable=False),
            sa.Column("created_by_actor_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("oauth_readiness_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "connector_credential_audit_events" not in existing:
        op.create_table(
            "connector_credential_audit_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("profile_id", sa.Text(), nullable=False),
            sa.Column("event_type", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("actor_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("details_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "connector_read_evidence" not in existing:
        op.create_table(
            "connector_read_evidence",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("auth_profile_id", sa.Text(), nullable=False),
            sa.Column("connector_id", sa.Text(), nullable=False),
            sa.Column("operation", sa.Text(), nullable=False),
            sa.Column("fixture_mode", sa.Boolean(), nullable=False, default=True),
            sa.Column("record_count", sa.Integer(), nullable=False, default=0),
            sa.Column("redacted_fields_count", sa.Integer(), nullable=False, default=0),
            sa.Column("result_summary_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("policy_passed", sa.Boolean(), nullable=False, default=True),
            sa.Column("read_only", sa.Boolean(), nullable=False, default=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "connector_setup_audit_events" not in existing:
        op.create_table(
            "connector_setup_audit_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("session_id", sa.Text(), nullable=False),
            sa.Column("event_type", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("submitted_by", sa.Text(), nullable=False, default='operator'),
            sa.Column("detail_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "connector_setup_sessions" not in existing:
        op.create_table(
            "connector_setup_sessions",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("connector_name", sa.Text(), nullable=False),
            sa.Column("erp_url", sa.Text(), nullable=False),
            sa.Column("erp_url_host", sa.Text(), nullable=False, default=''),
            sa.Column("environment_type", sa.Text(), nullable=False, default='unknown'),
            sa.Column("submitted_by", sa.Text(), nullable=False, default='operator'),
            sa.Column("status", sa.Text(), nullable=False, default='draft'),
            sa.Column("credential_mode", sa.Text(), nullable=False, default='not_provided'),
            sa.Column("credential_ref", sa.Text(), nullable=True),
            sa.Column("detected_adapter_type", sa.Text(), nullable=True),
            sa.Column("blocking_reasons_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "credential_vault_audit_events" not in existing:
        op.create_table(
            "credential_vault_audit_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("credential_ref", sa.Text(), nullable=False),
            sa.Column("setup_session_id", sa.Text(), nullable=False),
            sa.Column("event_type", sa.Text(), nullable=False),
            sa.Column("auth_type", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("username_redacted", sa.Text(), nullable=True),
            sa.Column("secret_fingerprint", sa.Text(), nullable=False),
            sa.Column("created_by", sa.Text(), nullable=False),
            sa.Column("details_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "credential_vault_entries" not in existing:
        op.create_table(
            "credential_vault_entries",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("credential_ref", sa.Text(), nullable=False, unique=True),
            sa.Column("setup_session_id", sa.Text(), nullable=False),
            sa.Column("connector_name", sa.Text(), nullable=False),
            sa.Column("erp_url_host", sa.Text(), nullable=False),
            sa.Column("auth_type", sa.Text(), nullable=False),
            sa.Column("username_redacted", sa.Text(), nullable=True),
            sa.Column("secret_fingerprint", sa.Text(), nullable=False),
            sa.Column("secret_length", sa.Integer(), nullable=True),
            sa.Column("secret_last4", sa.Text(), nullable=True),
            sa.Column("status", sa.Text(), nullable=False, default='sealed'),
            sa.Column("created_by", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("blocking_reasons_json", sa.Text(), nullable=False, default='[]'),
        )
    if "erp_fingerprinting_audit_events" not in existing:
        op.create_table(
            "erp_fingerprinting_audit_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("fingerprint_plan_id", sa.Text(), nullable=False),
            sa.Column("setup_session_id", sa.Text(), nullable=False),
            sa.Column("credential_ref", sa.Text(), nullable=False),
            sa.Column("event_type", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("details_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "erp_fingerprinting_plans" not in existing:
        op.create_table(
            "erp_fingerprinting_plans",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("fingerprint_plan_id", sa.Text(), nullable=False, unique=True),
            sa.Column("setup_session_id", sa.Text(), nullable=False),
            sa.Column("credential_ref", sa.Text(), nullable=False),
            sa.Column("connector_name", sa.Text(), nullable=False),
            sa.Column("erp_url_host", sa.Text(), nullable=False),
            sa.Column("environment_type", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False, default='planned'),
            sa.Column("adapter_candidates_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("planned_checks_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("risk_summary_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("next_safe_step", sa.Text(), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=False, default=0.0),
            sa.Column("created_by", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("blocking_reasons_json", sa.Text(), nullable=False, default='[]'),
        )
    if "execution_requests" not in existing:
        op.create_table(
            "execution_requests",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("skill_id", sa.Text(), nullable=False),
            sa.Column("skill_version_id", sa.Text(), nullable=False),
            sa.Column("approval_request_id", sa.Text(), nullable=True),
            sa.Column("requested_by_json", sa.Text(), nullable=False),
            sa.Column("inputs_json", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("can_execute_real_writes", sa.Boolean(), nullable=False, default=False),
            sa.Column("real_erp_writes_enabled", sa.Boolean(), nullable=False, default=False),
            sa.Column("idempotency_key", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "execution_runs" not in existing:
        op.create_table(
            "execution_runs",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("execution_request_id", sa.Text(), nullable=False),
            sa.Column("skill_id", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("plan_json", sa.Text(), nullable=False),
            sa.Column("result_json", sa.Text(), nullable=False),
            sa.Column("can_execute_real_writes", sa.Boolean(), nullable=False, default=False),
            sa.Column("real_erp_writes_enabled", sa.Boolean(), nullable=False, default=False),
            sa.Column("blocked_write_count", sa.Integer(), nullable=False, default=0),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "external_connector_audit_events" not in existing:
        op.create_table(
            "external_connector_audit_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("auth_profile_id", sa.Text(), nullable=False),
            sa.Column("connector_id", sa.Text(), nullable=False),
            sa.Column("event_type", sa.Text(), nullable=False),
            sa.Column("operation", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("fixture_mode", sa.Boolean(), nullable=False, default=True),
            sa.Column("actor_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("details_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "fake_erp_execution_audit_events" not in existing:
        op.create_table(
            "fake_erp_execution_audit_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("execution_id", sa.Text(), nullable=False),
            sa.Column("version_id", sa.Text(), nullable=False),
            sa.Column("dry_run_id", sa.Text(), nullable=False),
            sa.Column("actor_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("event_type", sa.Text(), nullable=False, default='requested'),
            sa.Column("status", sa.Text(), nullable=False, default='info'),
            sa.Column("detail_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "fake_erp_execution_evidence" not in existing:
        op.create_table(
            "fake_erp_execution_evidence",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("execution_id", sa.Text(), nullable=False),
            sa.Column("version_id", sa.Text(), nullable=False),
            sa.Column("skill_id", sa.Text(), nullable=False),
            sa.Column("dry_run_id", sa.Text(), nullable=False),
            sa.Column("actor_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("execution_target", sa.Text(), nullable=False, default='fake_erp'),
            sa.Column("inputs_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("steps_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("safety_summary_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "fake_erp_execution_evidence_packs" not in existing:
        op.create_table(
            "fake_erp_execution_evidence_packs",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("execution_id", sa.Text(), nullable=False),
            sa.Column("version_id", sa.Text(), nullable=False),
            sa.Column("skill_id", sa.Text(), nullable=False),
            sa.Column("dry_run_id", sa.Text(), nullable=False),
            sa.Column("actor_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("inputs_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("result_snapshot_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("steps_snapshot_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("safety_summary_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("audit_snapshot_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "fake_erp_execution_records" not in existing:
        op.create_table(
            "fake_erp_execution_records",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("version_id", sa.Text(), nullable=False),
            sa.Column("skill_id", sa.Text(), nullable=False),
            sa.Column("dry_run_id", sa.Text(), nullable=False),
            sa.Column("actor_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("execution_target", sa.Text(), nullable=False, default='fake_erp'),
            sa.Column("inputs_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("status", sa.Text(), nullable=False, default='blocked'),
            sa.Column("step_count", sa.Integer(), nullable=False, default=0),
            sa.Column("steps_executed", sa.Integer(), nullable=False, default=0),
            sa.Column("steps_blocked", sa.Integer(), nullable=False, default=0),
            sa.Column("result_summary", sa.Text(), nullable=False, default=''),
            sa.Column("safety_summary_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("evidence_pack_id", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "fake_erp_regression_audit_events" not in existing:
        op.create_table(
            "fake_erp_regression_audit_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("regression_run_id", sa.Text(), nullable=False),
            sa.Column("case_id", sa.Text(), nullable=False),
            sa.Column("version_id", sa.Text(), nullable=False),
            sa.Column("execution_id", sa.Text(), nullable=True),
            sa.Column("evidence_pack_id", sa.Text(), nullable=True),
            sa.Column("actor_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("event_type", sa.Text(), nullable=False, default='requested'),
            sa.Column("status", sa.Text(), nullable=False, default='info'),
            sa.Column("detail_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "fake_erp_regression_cases" not in existing:
        op.create_table(
            "fake_erp_regression_cases",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("version_id", sa.Text(), nullable=False),
            sa.Column("dry_run_id", sa.Text(), nullable=False),
            sa.Column("name", sa.Text(), nullable=False, default=''),
            sa.Column("execution_target", sa.Text(), nullable=False, default='fake_erp'),
            sa.Column("inputs_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("expected_outcomes_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "fake_erp_regression_runs" not in existing:
        op.create_table(
            "fake_erp_regression_runs",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("case_id", sa.Text(), nullable=False),
            sa.Column("version_id", sa.Text(), nullable=False),
            sa.Column("dry_run_id", sa.Text(), nullable=False),
            sa.Column("execution_id", sa.Text(), nullable=True),
            sa.Column("evidence_pack_id", sa.Text(), nullable=True),
            sa.Column("actor_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("inputs_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("execution_target", sa.Text(), nullable=False, default='fake_erp'),
            sa.Column("status", sa.Text(), nullable=False, default='blocked'),
            sa.Column("comparison_summary_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("result_summary", sa.Text(), nullable=False, default=''),
            sa.Column("safety_summary_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "generated_capability_audit_events" not in existing:
        op.create_table(
            "generated_capability_audit_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("capability_set_id", sa.Text(), nullable=False),
            sa.Column("discovery_plan_id", sa.Text(), nullable=False),
            sa.Column("fingerprint_plan_id", sa.Text(), nullable=False),
            sa.Column("setup_session_id", sa.Text(), nullable=False),
            sa.Column("credential_ref", sa.Text(), nullable=False),
            sa.Column("event_type", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("created_by", sa.Text(), nullable=False),
            sa.Column("details_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "generated_capability_sets" not in existing:
        op.create_table(
            "generated_capability_sets",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("capability_set_id", sa.Text(), nullable=False, unique=True),
            sa.Column("discovery_plan_id", sa.Text(), nullable=False),
            sa.Column("fingerprint_plan_id", sa.Text(), nullable=False),
            sa.Column("setup_session_id", sa.Text(), nullable=False),
            sa.Column("credential_ref", sa.Text(), nullable=False),
            sa.Column("adapter_id", sa.Text(), nullable=False),
            sa.Column("adapter_type", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False, default='generated'),
            sa.Column("capabilities_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("blocked_capabilities_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("source_surface_snapshot_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("policy_summary_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_by", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("blocking_reasons_json", sa.Text(), nullable=False, default='[]'),
        )
    if "invariant_results" not in existing:
        op.create_table(
            "invariant_results",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("preflight_case_id", sa.Text(), nullable=False),
            sa.Column("invariant_id", sa.Text(), nullable=False),
            sa.Column("invariant_type", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("severity", sa.Text(), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("evidence_json", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "kill_switch_events" not in existing:
        op.create_table(
            "kill_switch_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("tenant_id", sa.Text(), nullable=False),
            sa.Column("switch_name", sa.Text(), nullable=False),
            sa.Column("action", sa.Text(), nullable=False),
            sa.Column("activated_by_json", sa.Text(), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "manual_dry_run_audit_events" not in existing:
        op.create_table(
            "manual_dry_run_audit_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("run_id", sa.Text(), nullable=False),
            sa.Column("version_id", sa.Text(), nullable=False),
            sa.Column("actor_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("event_type", sa.Text(), nullable=False, default='requested'),
            sa.Column("status", sa.Text(), nullable=False, default='info'),
            sa.Column("detail_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "manual_dry_run_evidence" not in existing:
        op.create_table(
            "manual_dry_run_evidence",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("run_id", sa.Text(), nullable=False),
            sa.Column("version_id", sa.Text(), nullable=False),
            sa.Column("skill_id", sa.Text(), nullable=False),
            sa.Column("actor_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("mode", sa.Text(), nullable=False, default='dry_run'),
            sa.Column("inputs_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("preview_reference_id", sa.Text(), nullable=True),
            sa.Column("source_plan_id", sa.Text(), nullable=True),
            sa.Column("source_step_number", sa.Integer(), nullable=True),
            sa.Column("gate_result_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("simulated_steps_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("would_execute_steps_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("blocked_steps_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("safety_summary_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "mapping_confirmations" not in existing:
        op.create_table(
            "mapping_confirmations",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("proposal_id", sa.Text(), nullable=False),
            sa.Column("mapping_key", sa.Text(), nullable=False),
            sa.Column("action", sa.Text(), nullable=False),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "oauth_states" not in existing:
        op.create_table(
            "oauth_states",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("state_token", sa.Text(), nullable=False, unique=True),
            sa.Column("profile_id", sa.Text(), nullable=False),
            sa.Column("connector_id", sa.Text(), nullable=False),
            sa.Column("redirect_uri", sa.Text(), nullable=False),
            sa.Column("scope_requested", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False, default='pending'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "oauth_token_records" not in existing:
        op.create_table(
            "oauth_token_records",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("profile_id", sa.Text(), nullable=False),
            sa.Column("connector_id", sa.Text(), nullable=False),
            sa.Column("vault_ref", sa.Text(), nullable=False),
            sa.Column("secret_fingerprint", sa.Text(), nullable=False),
            sa.Column("scope_granted_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("scope_compliant", sa.Boolean(), nullable=False, default=False),
            sa.Column("has_refresh_token", sa.Boolean(), nullable=False, default=False),
            sa.Column("token_type", sa.Text(), nullable=False, default='Bearer'),
            sa.Column("placeholder_mode", sa.Boolean(), nullable=False, default=True),
            sa.Column("status", sa.Text(), nullable=False, default='active'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "odoo_connection_tests" not in existing:
        op.create_table(
            "odoo_connection_tests",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("connection_test_id", sa.Text(), nullable=False, unique=True),
            sa.Column("adapter_session_id", sa.Text(), nullable=False),
            sa.Column("activation_id", sa.Text(), nullable=False),
            sa.Column("setup_session_id", sa.Text(), nullable=False),
            sa.Column("credential_ref", sa.Text(), nullable=False),
            sa.Column("adapter_type", sa.Text(), nullable=False, default='odoo'),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("network_test_allowed", sa.Boolean(), nullable=False, default=False),
            sa.Column("external_http_performed", sa.Boolean(), nullable=False, default=False),
            sa.Column("login_attempted", sa.Boolean(), nullable=False, default=False),
            sa.Column("login_succeeded", sa.Boolean(), nullable=False, default=False),
            sa.Column("odoo_rpc_performed", sa.Boolean(), nullable=False, default=False),
            sa.Column("odoo_server_version", sa.Text(), nullable=True),
            sa.Column("business_data_read", sa.Boolean(), nullable=False, default=False),
            sa.Column("schema_inspection_performed", sa.Boolean(), nullable=False, default=False),
            sa.Column("permission_inspection_performed", sa.Boolean(), nullable=False, default=False),
            sa.Column("odoo_write_performed", sa.Boolean(), nullable=False, default=False),
            sa.Column("credentials_exposed", sa.Boolean(), nullable=False, default=False),
            sa.Column("raw_secret_accessed", sa.Boolean(), nullable=False, default=False),
            sa.Column("requested_by", sa.Text(), nullable=False),
            sa.Column("blocking_reasons_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "odoo_connection_test_audit_events" not in existing:
        op.create_table(
            "odoo_connection_test_audit_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("connection_test_id", sa.Text(), nullable=False),
            sa.Column("adapter_session_id", sa.Text(), nullable=False),
            sa.Column("activation_id", sa.Text(), nullable=False),
            sa.Column("setup_session_id", sa.Text(), nullable=False),
            sa.Column("credential_ref", sa.Text(), nullable=False),
            sa.Column("event_type", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("actor", sa.Text(), nullable=False),
            sa.Column("details_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "odoo_read_evidence_audit_events" not in existing:
        op.create_table(
            "odoo_read_evidence_audit_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("evidence_pack_id", sa.Text(), nullable=False),
            sa.Column("read_mapping_id", sa.Text(), nullable=False),
            sa.Column("connection_test_id", sa.Text(), nullable=False),
            sa.Column("adapter_session_id", sa.Text(), nullable=False),
            sa.Column("activation_id", sa.Text(), nullable=False),
            sa.Column("setup_session_id", sa.Text(), nullable=False),
            sa.Column("credential_ref", sa.Text(), nullable=False),
            sa.Column("object_type", sa.Text(), nullable=False),
            sa.Column("event_type", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("actor", sa.Text(), nullable=False),
            sa.Column("details_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "odoo_read_evidence_packs" not in existing:
        op.create_table(
            "odoo_read_evidence_packs",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("evidence_pack_id", sa.Text(), nullable=False, unique=True),
            sa.Column("read_mapping_id", sa.Text(), nullable=False),
            sa.Column("connection_test_id", sa.Text(), nullable=False),
            sa.Column("adapter_session_id", sa.Text(), nullable=False),
            sa.Column("activation_id", sa.Text(), nullable=False),
            sa.Column("setup_session_id", sa.Text(), nullable=False),
            sa.Column("credential_ref", sa.Text(), nullable=False),
            sa.Column("object_type", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False, default='created'),
            sa.Column("canonical_object_snapshot_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("source_snapshot_redacted_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("field_allowlist_used_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("redacted_fields_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("safety_summary_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("chain_summary_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_by", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("blocking_reasons_json", sa.Text(), nullable=False, default='[]'),
        )
    if "odoo_read_mappings" not in existing:
        op.create_table(
            "odoo_read_mappings",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("read_mapping_id", sa.Text(), nullable=False, unique=True),
            sa.Column("connection_test_id", sa.Text(), nullable=False),
            sa.Column("adapter_session_id", sa.Text(), nullable=False),
            sa.Column("activation_id", sa.Text(), nullable=False),
            sa.Column("setup_session_id", sa.Text(), nullable=False),
            sa.Column("credential_ref", sa.Text(), nullable=False),
            sa.Column("object_type", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("allow_business_read", sa.Boolean(), nullable=False, default=False),
            sa.Column("business_data_read", sa.Boolean(), nullable=False, default=False),
            sa.Column("canonical_object_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("source_snapshot_redacted_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("field_allowlist_used_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("redacted_fields_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("external_http_performed", sa.Boolean(), nullable=False, default=False),
            sa.Column("odoo_rpc_performed", sa.Boolean(), nullable=False, default=False),
            sa.Column("odoo_read_performed", sa.Boolean(), nullable=False, default=False),
            sa.Column("odoo_write_performed", sa.Boolean(), nullable=False, default=False),
            sa.Column("schema_inspection_performed", sa.Boolean(), nullable=False, default=False),
            sa.Column("permission_inspection_performed", sa.Boolean(), nullable=False, default=False),
            sa.Column("credentials_exposed", sa.Boolean(), nullable=False, default=False),
            sa.Column("raw_secret_accessed", sa.Boolean(), nullable=False, default=False),
            sa.Column("requested_by", sa.Text(), nullable=False),
            sa.Column("blocking_reasons_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "odoo_read_mapping_audit_events" not in existing:
        op.create_table(
            "odoo_read_mapping_audit_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("read_mapping_id", sa.Text(), nullable=False),
            sa.Column("connection_test_id", sa.Text(), nullable=False),
            sa.Column("adapter_session_id", sa.Text(), nullable=False),
            sa.Column("activation_id", sa.Text(), nullable=False),
            sa.Column("setup_session_id", sa.Text(), nullable=False),
            sa.Column("credential_ref", sa.Text(), nullable=False),
            sa.Column("object_type", sa.Text(), nullable=False),
            sa.Column("event_type", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("actor", sa.Text(), nullable=False),
            sa.Column("details_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "odoo_read_only_adapter_audit_events" not in existing:
        op.create_table(
            "odoo_read_only_adapter_audit_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("adapter_session_id", sa.Text(), nullable=False),
            sa.Column("activation_id", sa.Text(), nullable=False),
            sa.Column("capability_set_id", sa.Text(), nullable=False),
            sa.Column("setup_session_id", sa.Text(), nullable=False),
            sa.Column("credential_ref", sa.Text(), nullable=False),
            sa.Column("event_type", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("actor", sa.Text(), nullable=False),
            sa.Column("details_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "odoo_read_only_adapter_sessions" not in existing:
        op.create_table(
            "odoo_read_only_adapter_sessions",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("adapter_session_id", sa.Text(), nullable=False, unique=True),
            sa.Column("activation_id", sa.Text(), nullable=False),
            sa.Column("capability_set_id", sa.Text(), nullable=False),
            sa.Column("setup_session_id", sa.Text(), nullable=False),
            sa.Column("credential_ref", sa.Text(), nullable=False),
            sa.Column("adapter_id", sa.Text(), nullable=False),
            sa.Column("adapter_type", sa.Text(), nullable=False, default='odoo'),
            sa.Column("mode", sa.Text(), nullable=False, default='read_only'),
            sa.Column("status", sa.Text(), nullable=False, default='prepared'),
            sa.Column("created_by", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("blocking_reasons_json", sa.Text(), nullable=False, default='[]'),
        )
    if "odoo_read_only_demo_audit_events" not in existing:
        op.create_table(
            "odoo_read_only_demo_audit_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("demo_flow_id", sa.Text(), nullable=False),
            sa.Column("activation_id", sa.Text(), nullable=False),
            sa.Column("adapter_session_id", sa.Text(), nullable=False),
            sa.Column("connection_test_id", sa.Text(), nullable=False),
            sa.Column("event_type", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("actor", sa.Text(), nullable=False),
            sa.Column("details_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "odoo_read_only_demo_flows" not in existing:
        op.create_table(
            "odoo_read_only_demo_flows",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("demo_flow_id", sa.Text(), nullable=False, unique=True),
            sa.Column("activation_id", sa.Text(), nullable=False),
            sa.Column("adapter_session_id", sa.Text(), nullable=False),
            sa.Column("connection_test_id", sa.Text(), nullable=False),
            sa.Column("read_mapping_ids_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("evidence_pack_ids_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("requested_object_types_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("object_summaries_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("status", sa.Text(), nullable=False, default='blocked'),
            sa.Column("safety_summary_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_by", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("blocking_reasons_json", sa.Text(), nullable=False, default='[]'),
        )
    if "operator_action_plan_events" not in existing:
        op.create_table(
            "operator_action_plan_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("plan_type", sa.Text(), nullable=False, default='unknown'),
            sa.Column("goal", sa.Text(), nullable=False, default=''),
            sa.Column("version_id_context", sa.Text(), nullable=True),
            sa.Column("step_count", sa.Integer(), nullable=False, default=0),
            sa.Column("blocking_count", sa.Integer(), nullable=False, default=0),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "operator_console_queries" not in existing:
        op.create_table(
            "operator_console_queries",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("session_id", sa.Text(), nullable=False),
            sa.Column("query_text", sa.Text(), nullable=False),
            sa.Column("detected_intent", sa.Text(), nullable=False, default='unknown'),
            sa.Column("intent_confidence", sa.Float(), nullable=False, default=0.0),
            sa.Column("version_id_context", sa.Text(), nullable=True),
            sa.Column("response_summary", sa.Text(), nullable=False, default=''),
            sa.Column("result_type", sa.Text(), nullable=False, default=''),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "operator_console_sessions" not in existing:
        op.create_table(
            "operator_console_sessions",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("actor", sa.Text(), nullable=False, default='operator'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "operator_evidence_packs" not in existing:
        op.create_table(
            "operator_evidence_packs",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("created_by", sa.Text(), nullable=False),
            sa.Column("scenario_label", sa.Text(), nullable=False),
            sa.Column("sprint_chain", sa.Text(), nullable=False),
            sa.Column("seed_result_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("safety_checks_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("runbook_summary_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("test_evidence_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("evidence_status", sa.Text(), nullable=False, default='assembling'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "platform_audit_events" not in existing:
        op.create_table(
            "platform_audit_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("tenant_id", sa.Text(), nullable=False),
            sa.Column("event_category", sa.Text(), nullable=False),
            sa.Column("event_type", sa.Text(), nullable=False),
            sa.Column("actor_json", sa.Text(), nullable=False),
            sa.Column("details_json", sa.Text(), nullable=False),
            sa.Column("severity", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "preflight_cases" not in existing:
        op.create_table(
            "preflight_cases",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("connection_id", sa.Text(), nullable=False),
            sa.Column("actor_json", sa.Text(), nullable=False),
            sa.Column("action_json", sa.Text(), nullable=False),
            sa.Column("canonical_action", sa.Text(), nullable=False),
            sa.Column("canonical_object", sa.Text(), nullable=False),
            sa.Column("state_snapshot_json", sa.Text(), nullable=False),
            sa.Column("simulation_json", sa.Text(), nullable=True),
            sa.Column("decision", sa.Text(), nullable=False),
            sa.Column("risk_level", sa.Text(), nullable=False),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "r2_evidence_reviews" not in existing:
        op.create_table(
            "r2_evidence_reviews",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("run_id", sa.Text(), nullable=False),
            sa.Column("skill_id", sa.Text(), nullable=False),
            sa.Column("delta_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("fields_changed", sa.Integer(), nullable=False, default=0),
            sa.Column("fields_unchanged", sa.Integer(), nullable=False, default=0),
            sa.Column("drift_detected", sa.Boolean(), nullable=False, default=False),
            sa.Column("drift_details_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "r2_execution_reports" not in existing:
        op.create_table(
            "r2_execution_reports",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("run_id", sa.Text(), nullable=False),
            sa.Column("skill_id", sa.Text(), nullable=False),
            sa.Column("report_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("residual_risk_score", sa.Integer(), nullable=False, default=0),
            sa.Column("risk_level", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "r2_promotion_gates" not in existing:
        op.create_table(
            "r2_promotion_gates",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("run_id", sa.Text(), nullable=False),
            sa.Column("skill_id", sa.Text(), nullable=False),
            sa.Column("gate_status", sa.Text(), nullable=False),
            sa.Column("blocked", sa.Boolean(), nullable=False, default=True),
            sa.Column("checks_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("blocking_reasons_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "r2_rollback_rehearsals" not in existing:
        op.create_table(
            "r2_rollback_rehearsals",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("run_id", sa.Text(), nullable=False),
            sa.Column("skill_id", sa.Text(), nullable=False),
            sa.Column("instructions_valid", sa.Boolean(), nullable=False, default=False),
            sa.Column("missing_fields_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("dry_run_steps_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("rehearsal_passed", sa.Boolean(), nullable=False, default=False),
            sa.Column("notes", sa.Text(), nullable=False, default=''),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "r2_write_pilot_evidence" not in existing:
        op.create_table(
            "r2_write_pilot_evidence",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("run_id", sa.Text(), nullable=False),
            sa.Column("request_id", sa.Text(), nullable=False),
            sa.Column("skill_id", sa.Text(), nullable=False),
            sa.Column("action_taken", sa.Text(), nullable=False),
            sa.Column("target_model", sa.Text(), nullable=False),
            sa.Column("target_record_id", sa.Text(), nullable=False),
            sa.Column("pre_snapshot_json", sa.Text(), nullable=False),
            sa.Column("post_snapshot_json", sa.Text(), nullable=False),
            sa.Column("rollback_instructions_json", sa.Text(), nullable=False),
            sa.Column("idempotency_key", sa.Text(), nullable=False),
            sa.Column("allow_r2_real_write_pilot", sa.Boolean(), nullable=False, default=False),
            sa.Column("allow_generic_real_odoo_writes", sa.Boolean(), nullable=False, default=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "read_only_connector_activations" not in existing:
        op.create_table(
            "read_only_connector_activations",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("activation_id", sa.Text(), nullable=False, unique=True),
            sa.Column("activation_request_id", sa.Text(), nullable=False),
            sa.Column("capability_set_id", sa.Text(), nullable=False),
            sa.Column("setup_session_id", sa.Text(), nullable=False),
            sa.Column("credential_ref", sa.Text(), nullable=False),
            sa.Column("adapter_id", sa.Text(), nullable=False),
            sa.Column("adapter_type", sa.Text(), nullable=False),
            sa.Column("mode", sa.Text(), nullable=False, default='read_only'),
            sa.Column("status", sa.Text(), nullable=False, default='active_read_only'),
            sa.Column("approved_by", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("blocking_reasons_json", sa.Text(), nullable=False, default='[]'),
        )
    if "read_only_connector_activation_audit_events" not in existing:
        op.create_table(
            "read_only_connector_activation_audit_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("activation_request_id", sa.Text(), nullable=False),
            sa.Column("activation_id", sa.Text(), nullable=False),
            sa.Column("capability_set_id", sa.Text(), nullable=False),
            sa.Column("setup_session_id", sa.Text(), nullable=False),
            sa.Column("credential_ref", sa.Text(), nullable=False),
            sa.Column("event_type", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("actor", sa.Text(), nullable=False),
            sa.Column("details_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "read_only_connector_activation_requests" not in existing:
        op.create_table(
            "read_only_connector_activation_requests",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("activation_request_id", sa.Text(), nullable=False, unique=True),
            sa.Column("capability_set_id", sa.Text(), nullable=False),
            sa.Column("setup_session_id", sa.Text(), nullable=False),
            sa.Column("credential_ref", sa.Text(), nullable=False),
            sa.Column("adapter_id", sa.Text(), nullable=False),
            sa.Column("adapter_type", sa.Text(), nullable=False),
            sa.Column("mode", sa.Text(), nullable=False, default='read_only'),
            sa.Column("requested_by", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False, default='requested'),
            sa.Column("requires_human_approval", sa.Boolean(), nullable=False, default=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("blocking_reasons_json", sa.Text(), nullable=False, default='[]'),
        )
    if "safe_discovery_audit_events" not in existing:
        op.create_table(
            "safe_discovery_audit_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("discovery_plan_id", sa.Text(), nullable=False),
            sa.Column("fingerprint_plan_id", sa.Text(), nullable=False),
            sa.Column("setup_session_id", sa.Text(), nullable=False),
            sa.Column("credential_ref", sa.Text(), nullable=False),
            sa.Column("event_type", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("created_by", sa.Text(), nullable=False),
            sa.Column("details_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "safe_discovery_plans" not in existing:
        op.create_table(
            "safe_discovery_plans",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("discovery_plan_id", sa.Text(), nullable=False, unique=True),
            sa.Column("fingerprint_plan_id", sa.Text(), nullable=False),
            sa.Column("setup_session_id", sa.Text(), nullable=False),
            sa.Column("credential_ref", sa.Text(), nullable=False),
            sa.Column("selected_adapter_type", sa.Text(), nullable=False),
            sa.Column("connector_name", sa.Text(), nullable=False),
            sa.Column("erp_url_host", sa.Text(), nullable=False),
            sa.Column("environment_type", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False, default='planned'),
            sa.Column("read_only_surface_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("blocked_write_surface_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("permission_surface_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("planned_discovery_steps_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("risk_summary_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("next_safe_step", sa.Text(), nullable=True),
            sa.Column("created_by", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("blocking_reasons_json", sa.Text(), nullable=False, default='[]'),
        )
    if "skill_run_queue_entries" not in existing:
        op.create_table(
            "skill_run_queue_entries",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("schedule_id", sa.Text(), nullable=False),
            sa.Column("version_id", sa.Text(), nullable=False),
            sa.Column("skill_id", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False, default='queued'),
            sa.Column("inputs_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("target_base_url", sa.Text(), nullable=False),
            sa.Column("run_id", sa.Text(), nullable=True),
            sa.Column("detail", sa.Text(), nullable=False, default=''),
            sa.Column("enqueued_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "skill_schedules" not in existing:
        op.create_table(
            "skill_schedules",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("version_id", sa.Text(), nullable=False),
            sa.Column("skill_id", sa.Text(), nullable=False),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("interval_seconds", sa.Integer(), nullable=False),
            sa.Column("min_interval_seconds", sa.Integer(), nullable=False, default=60),
            sa.Column("dedup_window_seconds", sa.Integer(), nullable=False, default=30),
            sa.Column("status", sa.Text(), nullable=False, default='draft'),
            sa.Column("target_base_url", sa.Text(), nullable=False),
            sa.Column("inputs_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_run_id", sa.Text(), nullable=True),
            sa.Column("tick_lock_token", sa.Text(), nullable=True),
            sa.Column("tick_lock_until", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_by", sa.Text(), nullable=False, default='manual_operator'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "skill_schedule_events" not in existing:
        op.create_table(
            "skill_schedule_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("schedule_id", sa.Text(), nullable=False),
            sa.Column("event_type", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False, default='info'),
            sa.Column("detail", sa.Text(), nullable=False, default=''),
            sa.Column("payload_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "ui_skill_version_events" not in existing:
        op.create_table(
            "ui_skill_version_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("version_id", sa.Text(), nullable=False),
            sa.Column("skill_id", sa.Text(), nullable=False),
            sa.Column("event_type", sa.Text(), nullable=False),
            sa.Column("from_status", sa.Text(), nullable=False),
            sa.Column("to_status", sa.Text(), nullable=False),
            sa.Column("actor", sa.Text(), nullable=False, default='system'),
            sa.Column("reason", sa.Text(), nullable=False, default=''),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "ui_skill_version_records" not in existing:
        op.create_table(
            "ui_skill_version_records",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("skill_id", sa.Text(), nullable=False),
            sa.Column("compiled_skill_id", sa.Text(), nullable=False),
            sa.Column("version_number", sa.Integer(), nullable=False, default=1),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False, default='draft'),
            sa.Column("steps_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("guard_names_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("replay_run_id", sa.Text(), nullable=True),
            sa.Column("promotion_readiness_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("llm_required", sa.Boolean(), nullable=False, default=False),
            sa.Column("runtime_type", sa.Text(), nullable=False, default='deterministic_ui'),
            sa.Column("is_active", sa.Boolean(), nullable=False, default=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "visual_browser_sessions" not in existing:
        op.create_table(
            "visual_browser_sessions",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("visual_session_id", sa.Text(), nullable=False, unique=True),
            sa.Column("created_by", sa.Text(), nullable=False),
            sa.Column("target_url", sa.Text(), nullable=False, default=''),
            sa.Column("target_host", sa.Text(), nullable=False, default=''),
            sa.Column("intended_erp_hint", sa.Text(), nullable=False, default=''),
            sa.Column("workspace_mode", sa.Text(), nullable=False, default='observe_only'),
            sa.Column("status", sa.Text(), nullable=False, default='created'),
            sa.Column("credential_capture_allowed", sa.Boolean(), nullable=False, default=False),
            sa.Column("llm_can_see_credentials", sa.Boolean(), nullable=False, default=False),
            sa.Column("automatic_clicks_allowed", sa.Boolean(), nullable=False, default=False),
            sa.Column("automatic_form_submit_allowed", sa.Boolean(), nullable=False, default=False),
            sa.Column("dom_observation_allowed", sa.Boolean(), nullable=False, default=False),
            sa.Column("screen_capture_allowed", sa.Boolean(), nullable=False, default=False),
            sa.Column("workflow_recording_allowed", sa.Boolean(), nullable=False, default=False),
            sa.Column("browser_launched", sa.Boolean(), nullable=False, default=False),
            sa.Column("action_execution_allowed", sa.Boolean(), nullable=False, default=False),
            sa.Column("external_http_performed", sa.Boolean(), nullable=False, default=False),
            sa.Column("browser_control_performed", sa.Boolean(), nullable=False, default=False),
            sa.Column("mcp_execution_performed", sa.Boolean(), nullable=False, default=False),
            sa.Column("scheduler_used", sa.Boolean(), nullable=False, default=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("blocking_reasons_json", sa.Text(), nullable=False, default='[]'),
        )
    if "visual_browser_session_audit_events" not in existing:
        op.create_table(
            "visual_browser_session_audit_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("visual_session_id", sa.Text(), nullable=False),
            sa.Column("event_type", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("actor", sa.Text(), nullable=False),
            sa.Column("details_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "visual_observation_audit_events" not in existing:
        op.create_table(
            "visual_observation_audit_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("observation_id", sa.Text(), nullable=False),
            sa.Column("visual_session_id", sa.Text(), nullable=False),
            sa.Column("event_type", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("actor", sa.Text(), nullable=False),
            sa.Column("details_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "visual_observation_snapshots" not in existing:
        op.create_table(
            "visual_observation_snapshots",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("observation_id", sa.Text(), nullable=False, unique=True),
            sa.Column("visual_session_id", sa.Text(), nullable=False),
            sa.Column("created_by", sa.Text(), nullable=False),
            sa.Column("target_url", sa.Text(), nullable=False, default=''),
            sa.Column("target_host", sa.Text(), nullable=False, default=''),
            sa.Column("status", sa.Text(), nullable=False, default='created'),
            sa.Column("observation_source", sa.Text(), nullable=False, default='mocked_payload'),
            sa.Column("screen_summary_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("dom_summary_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("visible_text_redacted_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("detected_tables_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("detected_forms_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("detected_buttons_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("credential_fields_detected_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("dangerous_action_candidates_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("redaction_summary_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("safety_summary_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("blocking_reasons_json", sa.Text(), nullable=False, default='[]'),
        )
    if "visual_table_form_extractions" not in existing:
        op.create_table(
            "visual_table_form_extractions",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("extraction_id", sa.Text(), nullable=False, unique=True),
            sa.Column("visual_session_id", sa.Text(), nullable=False),
            sa.Column("observation_id", sa.Text(), nullable=False),
            sa.Column("workflow_trace_id", sa.Text(), nullable=False, default=''),
            sa.Column("created_by", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False, default='created'),
            sa.Column("extraction_goal", sa.Text(), nullable=False, default=''),
            sa.Column("table_structures_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("form_structures_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("button_structures_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("field_candidates_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("business_surface_hints_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("redaction_summary_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("safety_summary_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("blocking_reasons_json", sa.Text(), nullable=False, default='[]'),
        )
    if "visual_table_form_extraction_audit_events" not in existing:
        op.create_table(
            "visual_table_form_extraction_audit_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("extraction_id", sa.Text(), nullable=False),
            sa.Column("visual_session_id", sa.Text(), nullable=False),
            sa.Column("observation_id", sa.Text(), nullable=False),
            sa.Column("event_type", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("actor", sa.Text(), nullable=False),
            sa.Column("details_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "visual_workflow_traces" not in existing:
        op.create_table(
            "visual_workflow_traces",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("workflow_trace_id", sa.Text(), nullable=False, unique=True),
            sa.Column("visual_session_id", sa.Text(), nullable=False),
            sa.Column("created_by", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False, default='created'),
            sa.Column("workflow_name", sa.Text(), nullable=False, default=''),
            sa.Column("workflow_goal", sa.Text(), nullable=False, default=''),
            sa.Column("observation_ids_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("steps_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("dangerous_action_steps_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("credential_touchpoints_json", sa.Text(), nullable=False, default='[]'),
            sa.Column("redaction_summary_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("safety_summary_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("blocking_reasons_json", sa.Text(), nullable=False, default='[]'),
        )
    if "visual_workflow_trace_audit_events" not in existing:
        op.create_table(
            "visual_workflow_trace_audit_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("workflow_trace_id", sa.Text(), nullable=False),
            sa.Column("visual_session_id", sa.Text(), nullable=False),
            sa.Column("event_type", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("actor", sa.Text(), nullable=False),
            sa.Column("details_json", sa.Text(), nullable=False, default='{}'),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "write_pilot_evidence" not in existing:
        op.create_table(
            "write_pilot_evidence",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("run_id", sa.Text(), nullable=False),
            sa.Column("request_id", sa.Text(), nullable=False),
            sa.Column("skill_id", sa.Text(), nullable=False),
            sa.Column("action_taken", sa.Text(), nullable=False),
            sa.Column("target_model", sa.Text(), nullable=False),
            sa.Column("target_res_model", sa.Text(), nullable=False),
            sa.Column("target_res_id", sa.Text(), nullable=False),
            sa.Column("pre_snapshot_json", sa.Text(), nullable=False),
            sa.Column("post_snapshot_json", sa.Text(), nullable=False),
            sa.Column("rollback_instructions_json", sa.Text(), nullable=False),
            sa.Column("idempotency_key", sa.Text(), nullable=False),
            sa.Column("allow_r1_real_write_pilot", sa.Boolean(), nullable=False, default=False),
            sa.Column("allow_generic_real_odoo_writes", sa.Boolean(), nullable=False, default=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
