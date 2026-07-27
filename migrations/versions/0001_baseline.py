"""Create the baseline ERPGuard schema.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-07-27
"""

from alembic import op

from erpguard.db.base import Base
import erpguard.db.model_packages  # noqa: F401
import erpguard.db.models  # noqa: F401


revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create missing baseline tables without altering existing data."""
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    """Baseline downgrade is intentionally non-destructive."""
    pass

