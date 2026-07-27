"""Add bounded identity, role and membership tables.

Revision ID: 0002_identity
Revises: 0001_baseline
Create Date: 2026-07-27
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "0002_identity"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = set(inspect(bind).get_table_names())
    if "identity_users" not in existing:
        op.create_table(
            "identity_users",
            sa.Column("id", sa.String(length=128), nullable=False),
            sa.Column("email", sa.String(length=320), nullable=False),
            sa.Column("display_name", sa.String(length=200), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("email"),
        )
    if "identity_roles" not in existing:
        op.create_table(
            "identity_roles",
            sa.Column("name", sa.String(length=64), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.PrimaryKeyConstraint("name"),
        )
    if "identity_memberships" not in existing:
        op.create_table(
            "identity_memberships",
            sa.Column("id", sa.String(length=128), nullable=False),
            sa.Column("tenant_id", sa.String(length=128), nullable=False),
            sa.Column("user_id", sa.String(length=128), nullable=False),
            sa.Column("role_name", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("tenant_id", "user_id", name="uq_identity_membership_tenant_user"),
        )
        op.create_index("ix_identity_memberships_tenant_id", "identity_memberships", ["tenant_id"])
        op.create_index("ix_identity_memberships_user_id", "identity_memberships", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_identity_memberships_user_id", table_name="identity_memberships")
    op.drop_index("ix_identity_memberships_tenant_id", table_name="identity_memberships")
    op.drop_table("identity_memberships")
    op.drop_table("identity_roles")
    op.drop_table("identity_users")

