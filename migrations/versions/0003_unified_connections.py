"""Add unified connections and encrypted secret storage.

Revision ID: 0003_unified_connections
Revises: 0002_identity
Create Date: 2026-07-27
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "0003_unified_connections"
down_revision = "0002_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = set(inspect(bind).get_table_names())
    if "encrypted_secrets" not in existing:
        op.create_table(
            "encrypted_secrets",
            sa.Column("id", sa.String(length=128), nullable=False),
            sa.Column("tenant_id", sa.String(length=128), nullable=False),
            sa.Column("ciphertext", sa.Text(), nullable=False),
            sa.Column("fingerprint", sa.String(length=128), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_encrypted_secrets_tenant_id", "encrypted_secrets", ["tenant_id"])
    if "unified_connections" not in existing:
        op.create_table(
            "unified_connections",
            sa.Column("id", sa.String(length=128), nullable=False),
            sa.Column("tenant_id", sa.String(length=128), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("connector_type", sa.String(length=64), nullable=False),
            sa.Column("endpoint", sa.String(length=1000), nullable=False),
            sa.Column("auth_type", sa.String(length=64), nullable=False),
            sa.Column("secret_ref", sa.String(length=128), nullable=False),
            sa.Column("metadata_json", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("created_by", sa.String(length=128), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("tenant_id", "name", name="uq_unified_connection_tenant_name"),
        )
        op.create_index("ix_unified_connections_tenant_id", "unified_connections", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_unified_connections_tenant_id", table_name="unified_connections")
    op.drop_table("unified_connections")
    op.drop_index("ix_encrypted_secrets_tenant_id", table_name="encrypted_secrets")
    op.drop_table("encrypted_secrets")

