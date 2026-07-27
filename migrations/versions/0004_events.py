"""Add canonical event, object and ingestion cursor storage."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0004_events"
down_revision = "0003_unified_connections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing = set(inspect(op.get_bind()).get_table_names())
    if "canonical_objects" not in existing:
        op.create_table(
            "canonical_objects",
            sa.Column("id", sa.String(200), primary_key=True),
            sa.Column("tenant_id", sa.String(128), nullable=False),
            sa.Column("object_type", sa.String(128), nullable=False),
            sa.Column("object_key", sa.String(200), nullable=False),
            sa.Column("attributes_json", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint(
                "tenant_id", "object_key", name="uq_canonical_object_identity"
            ),
        )
        op.create_index("ix_canonical_objects_tenant_id", "canonical_objects", ["tenant_id"])
    if "canonical_events" not in existing:
        op.create_table(
            "canonical_events",
            sa.Column("id", sa.String(200), primary_key=True),
            sa.Column("tenant_id", sa.String(128), nullable=False),
            sa.Column("event_key", sa.String(200), nullable=False),
            sa.Column("event_type", sa.String(200), nullable=False),
            sa.Column("event_timestamp", sa.String(100), nullable=False),
            sa.Column("source", sa.String(200), nullable=False),
            sa.Column("object_keys_json", sa.Text(), nullable=False),
            sa.Column("attributes_json", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("tenant_id", "event_key", name="uq_canonical_event_tenant_key"),
        )
        op.create_index("ix_canonical_events_tenant_id", "canonical_events", ["tenant_id"])
    if "ingestion_cursors" not in existing:
        op.create_table(
            "ingestion_cursors",
            sa.Column("id", sa.String(200), primary_key=True),
            sa.Column("tenant_id", sa.String(128), nullable=False),
            sa.Column("connector_id", sa.String(128), nullable=False),
            sa.Column("stream_key", sa.String(200), nullable=False),
            sa.Column("cursor_value", sa.Text(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint(
                "tenant_id", "connector_id", "stream_key", name="uq_ingestion_cursor_scope"
            ),
        )
        op.create_index("ix_ingestion_cursors_tenant_id", "ingestion_cursors", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_ingestion_cursors_tenant_id", table_name="ingestion_cursors")
    op.drop_table("ingestion_cursors")
    op.drop_index("ix_canonical_events_tenant_id", table_name="canonical_events")
    op.drop_table("canonical_events")
    op.drop_index("ix_canonical_objects_tenant_id", table_name="canonical_objects")
    op.drop_table("canonical_objects")
