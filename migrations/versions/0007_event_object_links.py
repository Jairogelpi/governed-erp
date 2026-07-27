"""Add relational canonical event/object links and backfill existing rows."""

import json

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


revision = "0007_event_object_links"
down_revision = "0006_process_candidates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if "canonical_event_objects" not in set(inspect(bind).get_table_names()):
        op.create_table(
            "canonical_event_objects",
            sa.Column("id", sa.String(220), primary_key=True),
            sa.Column("tenant_id", sa.String(128), nullable=False),
            sa.Column("event_id", sa.String(200), nullable=False),
            sa.Column("object_id", sa.String(200), nullable=False),
            sa.Column("qualifier", sa.Text(), nullable=False),
            sa.UniqueConstraint("tenant_id", "event_id", "object_id", "qualifier", name="uq_event_object_link"),
        )
        op.create_index("ix_canonical_event_objects_tenant_id", "canonical_event_objects", ["tenant_id"])
        op.create_index("ix_canonical_event_objects_event_id", "canonical_event_objects", ["event_id"])
        op.create_index("ix_canonical_event_objects_object_id", "canonical_event_objects", ["object_id"])

    object_ids = {
        (row.tenant_id, row.object_key): row.id
        for row in bind.execute(text("SELECT id, tenant_id, object_key FROM canonical_objects"))
    }
    existing_links = {
        (row.tenant_id, row.event_id, row.object_id)
        for row in bind.execute(text("SELECT tenant_id, event_id, object_id FROM canonical_event_objects"))
    }
    for event in bind.execute(text("SELECT id, tenant_id, object_keys_json FROM canonical_events")):
        for object_key in json.loads(event.object_keys_json):
            object_id = object_ids.get((event.tenant_id, str(object_key)))
            if object_id is None or (event.tenant_id, event.id, object_id) in existing_links:
                continue
            bind.execute(
                text(
                    "INSERT INTO canonical_event_objects "
                    "(id, tenant_id, event_id, object_id, qualifier) "
                    "VALUES (:id, :tenant_id, :event_id, :object_id, :qualifier)"
                ),
                {"id": f"link_{event.id}_{object_id}", "tenant_id": event.tenant_id, "event_id": event.id, "object_id": object_id, "qualifier": ""},
            )


def downgrade() -> None:
    op.drop_index("ix_canonical_event_objects_object_id", table_name="canonical_event_objects")
    op.drop_index("ix_canonical_event_objects_event_id", table_name="canonical_event_objects")
    op.drop_index("ix_canonical_event_objects_tenant_id", table_name="canonical_event_objects")
    op.drop_table("canonical_event_objects")
