"""Sprint 6 — unit tests for live read service layer."""
from __future__ import annotations


import pytest

from erpguard.db.session import SessionLocal, init_db
from erpguard.release_ops.live_read_policy import LiveReadPolicyService


@pytest.fixture(autouse=True)
def fresh_db():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


class TestLiveReadPolicyService:
    def test_policy_fails_for_unknown_skill(self, fresh_db):
        svc = LiveReadPolicyService(fresh_db)
        result = svc.check("nonexistent_skill")
        assert result.passed is False
        codes = [v.code for v in result.violations]
        assert "skill_not_found" in codes

    def test_policy_always_has_reads_enabled_flag(self, fresh_db):
        svc = LiveReadPolicyService(fresh_db)
        result = svc.check("nonexistent_skill")
        assert result.allow_real_odoo_reads is True

    def test_policy_always_has_writes_disabled(self, fresh_db):
        svc = LiveReadPolicyService(fresh_db)
        result = svc.check("nonexistent_skill")
        assert result.can_execute_real_writes is False
        assert result.real_erp_writes_enabled is False

    def test_policy_to_dict_security_flags(self, fresh_db):
        svc = LiveReadPolicyService(fresh_db)
        result = svc.check("nonexistent_skill")
        d = result.to_dict()
        assert d["can_execute_real_writes"] is False
        assert d["real_erp_writes_enabled"] is False
        assert d["allow_real_odoo_reads"] is True
