"""Sprint 8 — unit tests for write pilot service layer."""
from __future__ import annotations

import pytest

from erpguard.db.session import SessionLocal, init_db
from erpguard.product.write_pilot_policy import WritePilotPolicyService


@pytest.fixture(autouse=True)
def fresh_db():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


class TestWritePilotPolicy:
    def test_policy_blocked_by_feature_flag_by_default(self, fresh_db):
        svc = WritePilotPolicyService(fresh_db)
        result = svc.check(skill_id="ghost_skill", target_model="mail.message", request_id="req_test")
        assert result.passed is False
        codes = [v.code for v in result.violations]
        assert "feature_flag_disabled" in codes

    def test_policy_blocked_for_non_whitelisted_model(self, fresh_db):
        svc = WritePilotPolicyService(fresh_db)
        result = svc.check(skill_id="ghost_skill", target_model="sale.order", request_id="req_test")
        assert result.passed is False
        codes = [v.code for v in result.violations]
        assert "model_not_whitelisted" in codes

    def test_policy_mail_message_whitelisted(self, fresh_db):
        svc = WritePilotPolicyService(fresh_db)
        result = svc.check(skill_id="ghost_skill", target_model="mail.message", request_id="req_test")
        assert result.target_whitelisted is True

    def test_policy_sale_order_not_whitelisted(self, fresh_db):
        svc = WritePilotPolicyService(fresh_db)
        result = svc.check(skill_id="ghost_skill", target_model="sale.order", request_id="req_test")
        assert result.target_whitelisted is False

    def test_policy_generic_writes_always_disabled(self, fresh_db):
        svc = WritePilotPolicyService(fresh_db)
        result = svc.check(skill_id="ghost_skill", target_model="mail.message", request_id="req_test")
        assert result.allow_generic_real_odoo_writes is False

    def test_policy_r3_r4_writes_always_disabled(self, fresh_db):
        svc = WritePilotPolicyService(fresh_db)
        result = svc.check(skill_id="ghost_skill", target_model="mail.message", request_id="req_test")
        assert result.allow_r3_r4_real_writes is False

    def test_policy_feature_flag_off_by_default(self, fresh_db):
        svc = WritePilotPolicyService(fresh_db)
        result = svc.check(skill_id="ghost_skill", target_model="mail.message", request_id="req_test")
        assert result.allow_r1_real_write_pilot is False

    def test_policy_requires_certification(self, fresh_db):
        svc = WritePilotPolicyService(fresh_db)
        result = svc.check(skill_id="ghost_skill_no_cert", target_model="mail.message", request_id="req_test")
        codes = [v.code for v in result.violations]
        assert "missing_write_readiness_certification" in codes

    def test_policy_pilot_passes_when_flag_enabled(self, fresh_db, monkeypatch):
        monkeypatch.setattr("erpguard.product.write_pilot_policy._ALLOW_R1_REAL_WRITE_PILOT", True)
        from erpguard.db.repositories import create_write_readiness_certification
        import json
        create_write_readiness_certification(
            session=fresh_db,
            skill_id="skill_for_pilot_policy_test",
            assessment_id="assess_x",
            certification_status="certified_read_only",
            overall_risk_level="R2",
            evidence_json=json.dumps({}),
        )
        svc = WritePilotPolicyService(fresh_db)
        result = svc.check(skill_id="skill_for_pilot_policy_test", target_model="mail.message", request_id="req_x")
        assert result.passed is True
        assert result.allow_r1_real_write_pilot is True
        assert len(result.violations) == 0
