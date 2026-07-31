"""Add Spec 92 Workstream B operational canary router."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0023_operational_canary_router"
down_revision = "0022_recommendation_action_drafts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = set(inspect(bind).get_table_names())
    if "canary_policies" not in existing:
        op.create_table(
            "canary_policies",
            sa.Column("id", sa.String(128), primary_key=True),
            sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
            sa.Column("process_key", sa.String(128), nullable=False, index=True),
            sa.Column("stable_skill_package_id", sa.String(128), nullable=False),
            sa.Column("canary_skill_package_id", sa.String(128), nullable=False),
            sa.Column("shadow_deployment_id", sa.String(128), nullable=False),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("percentage_basis_points", sa.Integer(), nullable=False),
            sa.Column("maximum_cases", sa.Integer(), nullable=False),
            sa.Column("maximum_total_amount", sa.Float(), nullable=False),
            sa.Column("allowed_capabilities_json", sa.Text(), nullable=False),
            sa.Column("company_ids_json", sa.Text(), nullable=False),
            sa.Column("minimum_amount", sa.Float(), nullable=False),
            sa.Column("maximum_amount", sa.Float(), nullable=False),
            sa.Column("object_types_json", sa.Text(), nullable=False),
            sa.Column("start_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("safety_thresholds_json", sa.Text(), nullable=False),
            sa.Column("content_hash", sa.String(128), nullable=False, index=True),
            sa.Column("created_by", sa.String(128), nullable=False),
            sa.Column("approved_by", sa.String(128), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("aborted_at", sa.DateTime(timezone=True), nullable=True),
        )
        if bind.dialect.name == "postgresql":
            op.create_index(
                "uq_canary_policies_one_active_per_process",
                "canary_policies",
                ["tenant_id", "process_key"],
                unique=True,
                postgresql_where=sa.text("status = 'active'"),
            )
    if "canary_routing_decisions" not in existing:
        op.create_table(
            "canary_routing_decisions",
            sa.Column("id", sa.String(128), primary_key=True),
            sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
            sa.Column("canary_policy_id", sa.String(128), nullable=True, index=True),
            sa.Column("process_key", sa.String(128), nullable=False, index=True),
            sa.Column("business_object_key", sa.String(256), nullable=True),
            sa.Column("routing_context_hash", sa.String(128), nullable=False),
            sa.Column("bucket", sa.Integer(), nullable=True),
            sa.Column("selected_lane", sa.String(16), nullable=False),
            sa.Column("stable_skill_package_id", sa.String(128), nullable=True),
            sa.Column("canary_skill_package_id", sa.String(128), nullable=True),
            sa.Column("selected_skill_package_id", sa.String(128), nullable=True),
            sa.Column("selection_reason", sa.String(64), nullable=False),
            sa.Column("execution_run_id", sa.String(128), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "canary_safety_incidents" not in existing:
        op.create_table(
            "canary_safety_incidents",
            sa.Column("id", sa.String(128), primary_key=True),
            sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
            sa.Column("canary_policy_id", sa.String(128), nullable=False, index=True),
            sa.Column("routing_decision_id", sa.String(128), nullable=True),
            sa.Column("execution_run_id", sa.String(128), nullable=True),
            sa.Column("incident_type", sa.String(64), nullable=False),
            sa.Column("severity", sa.String(16), nullable=False),
            sa.Column("details_json", sa.Text(), nullable=False),
            sa.Column("evidence_pack_id", sa.String(128), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("resolved_by", sa.String(128), nullable=True),
            sa.Column("resolution_notes", sa.Text(), nullable=False),
        )

    run_columns = {col["name"] for col in inspect(bind).get_columns("execution_runs_v2")}
    with op.batch_alter_table("execution_runs_v2") as batch_op:
        if "canary_policy_id" not in run_columns:
            batch_op.add_column(sa.Column("canary_policy_id", sa.String(128), nullable=True))
        if "routing_decision_id" not in run_columns:
            batch_op.add_column(sa.Column("routing_decision_id", sa.String(128), nullable=True))
        if "deployment_lane" not in run_columns:
            batch_op.add_column(sa.Column("deployment_lane", sa.String(16), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    run_columns = {col["name"] for col in inspect(bind).get_columns("execution_runs_v2")}
    with op.batch_alter_table("execution_runs_v2") as batch_op:
        if "deployment_lane" in run_columns:
            batch_op.drop_column("deployment_lane")
        if "routing_decision_id" in run_columns:
            batch_op.drop_column("routing_decision_id")
        if "canary_policy_id" in run_columns:
            batch_op.drop_column("canary_policy_id")

    existing = set(inspect(bind).get_table_names())
    for table in ("canary_safety_incidents", "canary_routing_decisions", "canary_policies"):
        if table in existing:
            op.drop_table(table)
