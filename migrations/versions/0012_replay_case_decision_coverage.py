"""Add decision-coverage columns to process_replay_cases.

Historical replay used to silently skip declared decisions that had no
evaluator, which could make a partially-evaluated case look like a clean
"passed" result. These columns record what actually ran so a Proof of
Improvement can require full coverage before recommending anything.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0012_replay_case_decision_coverage"
down_revision = "0011_process_proofs"
branch_labels = None
depends_on = None

_COLUMNS = (
    ("declared_decision_count", sa.Integer(), "0"),
    ("evaluated_decision_count", sa.Integer(), "0"),
    ("unsupported_decisions_json", sa.Text(), "'[]'"),
    ("decision_coverage_rate", sa.Float(), "1.0"),
)


def upgrade() -> None:
    bind = op.get_bind()
    if "process_replay_cases" not in set(inspect(bind).get_table_names()):
        return
    existing_columns = {item["name"] for item in inspect(bind).get_columns("process_replay_cases")}
    with op.batch_alter_table("process_replay_cases", recreate="always") as batch_op:
        for name, col_type, default in _COLUMNS:
            if name not in existing_columns:
                batch_op.add_column(
                    sa.Column(name, col_type, nullable=False, server_default=sa.text(default))
                )


def downgrade() -> None:
    bind = op.get_bind()
    if "process_replay_cases" not in set(inspect(bind).get_table_names()):
        return
    existing_columns = {item["name"] for item in inspect(bind).get_columns("process_replay_cases")}
    with op.batch_alter_table("process_replay_cases", recreate="always") as batch_op:
        for name, _col_type, _default in _COLUMNS:
            if name in existing_columns:
                batch_op.drop_column(name)
