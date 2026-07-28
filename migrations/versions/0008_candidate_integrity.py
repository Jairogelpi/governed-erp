"""Add tenant scope and deterministic candidate artifacts."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0008_candidate_integrity"
down_revision = "0007_event_object_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if "process_candidates" not in set(inspect(bind).get_table_names()):
        return

    columns = {item["name"] for item in inspect(bind).get_columns("process_candidates")}
    if "tenant_id" in columns:
        return

    with op.batch_alter_table("process_candidates", recreate="always") as batch_op:
        batch_op.add_column(
            sa.Column(
                "tenant_id",
                sa.String(128),
                nullable=False,
                server_default=sa.text("'legacy'"),
            )
        )
        batch_op.alter_column("changes_json", new_column_name="patch_json")
        batch_op.add_column(sa.Column("proposal_json", sa.Text(), nullable=False, server_default=sa.text("'{}'")))
        batch_op.add_column(
            sa.Column("base_definition_digest", sa.String(128), nullable=False, server_default=sa.text("''"))
        )
        batch_op.add_column(sa.Column("patch_digest", sa.String(128), nullable=False, server_default=sa.text("''")))
        batch_op.add_column(
            sa.Column("candidate_definition_json", sa.Text(), nullable=False, server_default=sa.text("'{}'"))
        )
        batch_op.add_column(
            sa.Column("candidate_definition_digest", sa.String(128), nullable=False, server_default=sa.text("''"))
        )
        batch_op.add_column(
            sa.Column("validation_status", sa.String(32), nullable=False, server_default=sa.text("'legacy_unvalidated'"))
        )
        batch_op.drop_constraint("uq_process_candidate_version", type_="unique")
        batch_op.create_unique_constraint(
            "uq_process_candidate_tenant_version",
            ["tenant_id", "process_key", "candidate_version"],
        )

    indexes = {item["name"] for item in inspect(bind).get_indexes("process_candidates")}
    if "ix_process_candidates_tenant_id" not in indexes:
        op.create_index("ix_process_candidates_tenant_id", "process_candidates", ["tenant_id"])


def downgrade() -> None:
    bind = op.get_bind()
    if "process_candidates" not in set(inspect(bind).get_table_names()):
        return
    with op.batch_alter_table("process_candidates", recreate="always") as batch_op:
        batch_op.drop_constraint("uq_process_candidate_tenant_version", type_="unique")
        batch_op.create_unique_constraint(
            "uq_process_candidate_version", ["process_key", "candidate_version"]
        )
        batch_op.alter_column("patch_json", new_column_name="changes_json")
        for name in (
            "tenant_id",
            "proposal_json",
            "base_definition_digest",
            "patch_digest",
            "candidate_definition_json",
            "candidate_definition_digest",
            "validation_status",
        ):
            batch_op.drop_column(name)
    if "ix_process_candidates_tenant_id" in {
        item["name"] for item in inspect(bind).get_indexes("process_candidates")
    }:
        op.drop_index("ix_process_candidates_tenant_id", table_name="process_candidates")
