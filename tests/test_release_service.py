from __future__ import annotations

import pytest

from erpguard.db.session import SessionLocal, init_db
from erpguard.release_ops.release_readiness import ReleaseReadinessService, _SAFETY_BOUNDARIES, _SPRINT_CHAIN
from erpguard.release_ops.demo_seed import DemoSeedService
from erpguard.release_ops.operator_smoke import OperatorSmokeService
from erpguard.version import __version__


@pytest.fixture(autouse=True)
def db_session():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


# ── ReleaseReadinessService ────────────────────────────────────────────────

class TestReleaseReadinessService:
    def test_report_returns_version(self, db_session):
        result = ReleaseReadinessService(db_session).report()
        assert result["release_version"] == __version__

    def test_report_has_checks(self, db_session):
        result = ReleaseReadinessService(db_session).report()
        assert len(result["checks"]) >= 8
        assert result["checks_total"] >= 8

    def test_all_safety_flags_false(self, db_session):
        assert all(not v for v in _SAFETY_BOUNDARIES.values()), "All safety flags must be false"

    def test_safety_boundaries_in_report(self, db_session):
        result = ReleaseReadinessService(db_session).report()
        sb = result["safety_boundaries"]
        assert sb["ALLOW_GENERIC_REAL_ODOO_WRITES"] is False
        assert sb["ALLOW_R3_R4_REAL_WRITES"] is False
        assert sb["can_execute_real_writes"] is False

    def test_sprint_chain_has_13_entries(self, db_session):
        assert len(_SPRINT_CHAIN) == 13
        result = ReleaseReadinessService(db_session).report()
        assert len(result["sprint_chain"]) == 13

    def test_report_status_is_ready(self, db_session):
        result = ReleaseReadinessService(db_session).report()
        assert result["status"] in ("ready", "partial")
        assert result["readiness_score"] >= 0

    def test_blocked_operations_listed(self, db_session):
        result = ReleaseReadinessService(db_session).report()
        blocked = result["blocked_operations"]
        assert any("action_confirm" in op for op in blocked)
        assert any("button_validate" in op for op in blocked)
        assert any("generic" in op.lower() for op in blocked)

    def test_entity_counts_present(self, db_session):
        result = ReleaseReadinessService(db_session).report()
        counts = result["entity_counts"]
        assert "tenants" in counts
        assert "skills" in counts
        assert isinstance(counts["tenants"], int)

    def test_generic_writes_check_passes(self, db_session):
        result = ReleaseReadinessService(db_session).report()
        check = next(c for c in result["checks"] if c["name"] == "generic_writes_locked")
        assert check["passed"] is True

    def test_r3_r4_check_passes(self, db_session):
        result = ReleaseReadinessService(db_session).report()
        check = next(c for c in result["checks"] if c["name"] == "r3_r4_writes_locked")
        assert check["passed"] is True


# ── DemoSeedService ────────────────────────────────────────────────────────

class TestDemoSeedService:
    def test_seed_creates_tenant(self, db_session):
        result = DemoSeedService(db_session).seed()
        assert result["seeded"] is True
        assert result["tenant_id"].startswith("tenant_")
        assert result["tenant_name"] == "ERPGuard Demo Tenant"
        assert result["tenant_environment"] == "staging"

    def test_seed_creates_skill(self, db_session):
        result = DemoSeedService(db_session).seed()
        assert result["skill_id"].startswith("skill_")
        assert "Demo" in result["skill_name"]

    def test_seed_creates_operator_session(self, db_session):
        result = DemoSeedService(db_session).seed()
        assert result["operator_session_id"].startswith("opsession_")
        assert result["operator_session_step"] == "awaiting_connection"

    def test_seed_safety_invariants(self, db_session):
        result = DemoSeedService(db_session).seed()
        inv = result["safety_invariants"]
        assert inv["can_execute_real_writes"] is False
        assert inv["allow_generic_real_odoo_writes"] is False
        assert inv["allow_r3_r4_real_writes"] is False

    def test_seed_provides_next_steps(self, db_session):
        result = DemoSeedService(db_session).seed()
        assert len(result["next_steps"]) >= 3
        assert any("/demo" in step for step in result["next_steps"])


# ── OperatorSmokeService ───────────────────────────────────────────────────

class TestOperatorSmokeService:
    def test_smoke_passes(self, db_session):
        result = OperatorSmokeService(db_session).run()
        assert result["smoke_status"] in ("passed", "partial")
        assert result["checks_passed"] >= 5
        assert result["checks_total"] == 7

    def test_smoke_safety_boundaries_check_passes(self, db_session):
        result = OperatorSmokeService(db_session).run()
        check = next(c for c in result["checks"] if c["name"] == "safety_boundaries")
        assert check["passed"] is True

    def test_smoke_r2_flag_check_passes(self, db_session):
        result = OperatorSmokeService(db_session).run()
        check = next(c for c in result["checks"] if c["name"] == "r2_pilot_flag_default_off")
        assert check["passed"] is True

    def test_smoke_invariants_always_false(self, db_session):
        result = OperatorSmokeService(db_session).run()
        inv = result["safety_invariants"]
        assert inv["can_execute_real_writes"] is False
        assert inv["allow_generic_real_odoo_writes"] is False
        assert inv["allow_r3_r4_real_writes"] is False

    def test_smoke_tenant_creation_passes(self, db_session):
        result = OperatorSmokeService(db_session).run()
        check = next(c for c in result["checks"] if c["name"] == "tenant_creation")
        assert check["passed"] is True

    def test_smoke_operator_flow_advance_passes(self, db_session):
        result = OperatorSmokeService(db_session).run()
        check = next(c for c in result["checks"] if c["name"] == "operator_flow_advance")
        assert check["passed"] is True
