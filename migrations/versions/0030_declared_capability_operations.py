"""Generalize declared write capabilities beyond single-field update:
add `operation` (update_field/create_record/archive_record),
`required_fields_json` (create_record's declared field set),
`idempotency_field` (create_record dedup key); `target_field`/
`field_type` become nullable since archive_record/create_record don't
use them the same way update_field does."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0030_declared_capability_operations"
down_revision = "0029_declared_write_capabilities"
branch_labels = None
depends_on = None

_TABLE = "declared_write_capabilities"


def upgrade() -> None:
    columns = {c["name"] for c in inspect(op.get_bind()).get_columns(_TABLE)}
    with op.batch_alter_table(_TABLE) as batch_op:
        if "operation" not in columns:
            batch_op.add_column(
                sa.Column("operation", sa.String(32), nullable=False, server_default="update_field")
            )
        if "required_fields_json" not in columns:
            batch_op.add_column(
                sa.Column("required_fields_json", sa.Text(), nullable=False, server_default="{}")
            )
        if "idempotency_field" not in columns:
            batch_op.add_column(sa.Column("idempotency_field", sa.String(128), nullable=True))
        if "target_field" in columns:
            batch_op.alter_column("target_field", existing_type=sa.String(128), nullable=True)
        if "field_type" in columns:
            batch_op.alter_column("field_type", existing_type=sa.String(16), nullable=True)


def downgrade() -> None:
    columns = {c["name"] for c in inspect(op.get_bind()).get_columns(_TABLE)}
    with op.batch_alter_table(_TABLE) as batch_op:
        if "idempotency_field" in columns:
            batch_op.drop_column("idempotency_field")
        if "required_fields_json" in columns:
            batch_op.drop_column("required_fields_json")
        if "operation" in columns:
            batch_op.drop_column("operation")
