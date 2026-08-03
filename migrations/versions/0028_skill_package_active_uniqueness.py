"""Close a TOCTOU gap: enforce at most one active SkillPackage per
(tenant_id, process_key) at the database level on PostgreSQL, same
partial-unique-index pattern 0023 used for canary_policies.

SkillDeploymentService.promote_to_active (erpguard/domain/deployment/service.py)
enforces this via check-then-insert application code only -- concurrent
promotions for the same process could both pass the check and both end up
`active`, silently breaking the invariant the canary router and execution
routing depend on. SQLite has no partial-index support usable here, so the
application-level check remains the only guard in tests; this is the real
guard for the database this project actually targets in production.
"""

from alembic import op
import sqlalchemy as sa


revision = "0028_skill_package_active_uniqueness"
down_revision = "0027_benchmark_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.create_index(
            "uq_skill_packages_one_active_per_process",
            "skill_packages",
            ["tenant_id", "process_key"],
            unique=True,
            postgresql_where=sa.text("status = 'active'"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_index("uq_skill_packages_one_active_per_process", table_name="skill_packages")
