"""Add Spec 92 Sec 10.6 net-ROI implementation-cost columns."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0026_outcome_implementation_cost"
down_revision = "0025_decision_outcome_evidence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    plan_columns = {c["name"] for c in inspect(op.get_bind()).get_columns("outcome_measurement_plans")}
    if "implementation_cost" not in plan_columns:
        op.add_column("outcome_measurement_plans", sa.Column("implementation_cost", sa.String(64), nullable=True))

    report_columns = {c["name"] for c in inspect(op.get_bind()).get_columns("realized_outcome_reports")}
    if "implementation_cost" not in report_columns:
        op.add_column("realized_outcome_reports", sa.Column("implementation_cost", sa.String(64), nullable=True))
    if "net_realized_value" not in report_columns:
        op.add_column("realized_outcome_reports", sa.Column("net_realized_value", sa.String(64), nullable=True))


def downgrade() -> None:
    report_columns = {c["name"] for c in inspect(op.get_bind()).get_columns("realized_outcome_reports")}
    if "net_realized_value" in report_columns:
        op.drop_column("realized_outcome_reports", "net_realized_value")
    if "implementation_cost" in report_columns:
        op.drop_column("realized_outcome_reports", "implementation_cost")

    plan_columns = {c["name"] for c in inspect(op.get_bind()).get_columns("outcome_measurement_plans")}
    if "implementation_cost" in plan_columns:
        op.drop_column("outcome_measurement_plans", "implementation_cost")
