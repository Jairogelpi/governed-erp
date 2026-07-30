"""Add Phase 18.1 operational shadow feed and outcome reconciliation."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0018_operational_shadow_feed"
down_revision = "0017_shadow_mode"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    deployment_columns = _columns("shadow_deployments")
    deployment_additions = (
        ("minimum_case_count", sa.Integer(), "30"),
        ("minimum_decision_coverage", sa.Float(), "1.0"),
        ("minimum_review_coverage", sa.Float(), "0.5"),
        ("minimum_outcome_reconciliation", sa.Float(), "0.5"),
        ("observation_window_hours", sa.Integer(), "168"),
    )
    for name, column_type, default in deployment_additions:
        if name not in deployment_columns:
            op.add_column(
                "shadow_deployments",
                sa.Column(name, column_type, nullable=False, server_default=default),
            )

    case_columns = _columns("shadow_case_results")
    case_additions = (
        ("evaluation_mode", sa.String(32), False, "manual_api"),
        ("canonical_trace_hash", sa.String(128), True, None),
        ("trace_provenance_json", sa.Text(), False, "{}"),
        ("variant_id", sa.String(128), True, None),
        ("event_count", sa.Integer(), False, "0"),
        ("first_event_at", sa.String(100), True, None),
        ("last_event_at", sa.String(100), True, None),
    )
    for name, column_type, nullable, default in case_additions:
        if name not in case_columns:
            op.add_column(
                "shadow_case_results",
                sa.Column(
                    name,
                    column_type,
                    nullable=nullable,
                    server_default=default,
                ),
            )
    indexes = {item["name"] for item in inspect(op.get_bind()).get_indexes("shadow_case_results")}
    if "ix_shadow_case_results_canonical_trace_hash" not in indexes:
        op.create_index(
            "ix_shadow_case_results_canonical_trace_hash",
            "shadow_case_results",
            ["canonical_trace_hash"],
        )

    existing = set(inspect(op.get_bind()).get_table_names())
    if "shadow_outcome_observations" not in existing:
        op.create_table(
            "shadow_outcome_observations",
            sa.Column("id", sa.String(128), primary_key=True),
            sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
            sa.Column("deployment_id", sa.String(128), nullable=False, index=True),
            sa.Column("shadow_case_result_id", sa.String(128), nullable=False, index=True),
            sa.Column("idempotency_key", sa.String(256), nullable=False),
            sa.Column("outcome_json", sa.Text(), nullable=False),
            sa.Column("observed_decision_status", sa.String(32), nullable=True),
            sa.Column("provenance", sa.String(32), nullable=False),
            sa.Column("source_event_ids_json", sa.Text(), nullable=False),
            sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("recorded_by", sa.String(128), nullable=False),
            sa.Column("deterministic_hash", sa.String(128), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint(
                "tenant_id",
                "shadow_case_result_id",
                "idempotency_key",
                name="uq_shadow_outcome_case_idempotency",
            ),
        )
    if "shadow_feed_runs" not in existing:
        op.create_table(
            "shadow_feed_runs",
            sa.Column("id", sa.String(128), primary_key=True),
            sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
            sa.Column("deployment_id", sa.String(128), nullable=False, index=True),
            sa.Column("trigger", sa.String(32), nullable=False),
            sa.Column("requested_case_ids_json", sa.Text(), nullable=False),
            sa.Column("scanned_case_count", sa.Integer(), nullable=False),
            sa.Column("evaluated_case_count", sa.Integer(), nullable=False),
            sa.Column("deduplicated_case_count", sa.Integer(), nullable=False),
            sa.Column("failed_case_count", sa.Integer(), nullable=False),
            sa.Column("failure_codes_json", sa.Text(), nullable=False),
            sa.Column("no_effects", sa.Boolean(), nullable=False),
            sa.Column("created_by", sa.String(128), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade() -> None:
    existing = set(inspect(op.get_bind()).get_table_names())
    if "shadow_feed_runs" in existing:
        op.drop_table("shadow_feed_runs")
    if "shadow_outcome_observations" in existing:
        op.drop_table("shadow_outcome_observations")
    indexes = {
        item["name"] for item in inspect(op.get_bind()).get_indexes("shadow_case_results")
    }
    if "ix_shadow_case_results_canonical_trace_hash" in indexes:
        op.drop_index(
            "ix_shadow_case_results_canonical_trace_hash",
            table_name="shadow_case_results",
        )
    case_columns = _columns("shadow_case_results")
    for name in (
        "last_event_at",
        "first_event_at",
        "event_count",
        "variant_id",
        "trace_provenance_json",
        "canonical_trace_hash",
        "evaluation_mode",
    ):
        if name in case_columns:
            op.drop_column("shadow_case_results", name)
    deployment_columns = _columns("shadow_deployments")
    for name in (
        "observation_window_hours",
        "minimum_outcome_reconciliation",
        "minimum_review_coverage",
        "minimum_decision_coverage",
        "minimum_case_count",
    ):
        if name in deployment_columns:
            op.drop_column("shadow_deployments", name)
