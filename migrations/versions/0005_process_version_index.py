"""Enforce one immutable row per process key and version."""

from alembic import op
from sqlalchemy import inspect


revision = "0005_process_version_index"
down_revision = "0004_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    indexes = {item["name"] for item in inspect(op.get_bind()).get_indexes("process_definitions")}
    if "uq_process_definition_key_version" not in indexes:
        op.create_index(
            "uq_process_definition_key_version",
            "process_definitions",
            ["process_key", "version"],
            unique=True,
        )


def downgrade() -> None:
    op.drop_index("uq_process_definition_key_version", table_name="process_definitions")
