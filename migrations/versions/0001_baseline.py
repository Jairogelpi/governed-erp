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
    # Identity tables are introduced by revision 0002. Keep the Phase 2
    # baseline stable even though the current metadata also contains them.
    baseline_tables = [
        table for table in Base.metadata.sorted_tables if not table.name.startswith("identity_")
    ]
    Base.metadata.create_all(bind=bind, tables=baseline_tables)


def downgrade() -> None:
    """Baseline downgrade is intentionally non-destructive."""
    pass
