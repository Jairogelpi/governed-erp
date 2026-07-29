"""Sprint 7 — unit tests for write readiness service layer."""
from __future__ import annotations

import pytest

from erpguard.db.session import SessionLocal, init_db
from erpguard.release_ops.write_risk_matrix import WriteRiskMatrix
from erpguard.product.models import WriteDetectedCandidateModel


@pytest.fixture(autouse=True)
def fresh_db():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


class TestWriteRiskMatrix:
    def test_unknown_method_is_r4(self, fresh_db):
        svc = WriteRiskMatrix()
        candidates = [
            WriteDetectedCandidateModel(
                candidate_id="wc_test01",
                opportunity_code="test",
                odoo_model="sale.order",
                write_method="some_unknown_action",
                description="Unknown action",
            )
        ]
        entries = svc.classify(candidates)
        assert entries[0].risk_level == "R4"
        assert entries[0].risk_code == "unknown_write_method"

    def test_create_is_r2(self, fresh_db):
        svc = WriteRiskMatrix()
        candidates = [
            WriteDetectedCandidateModel(
                candidate_id="wc_test02",
                opportunity_code="test",
                odoo_model="sale.order",
                write_method="create",
                description="Create order",
            )
        ]
        entries = svc.classify(candidates)
        assert entries[0].risk_level == "R2"

    def test_action_confirm_is_r3(self, fresh_db):
        svc = WriteRiskMatrix()
        candidates = [
            WriteDetectedCandidateModel(
                candidate_id="wc_test03",
                opportunity_code="test",
                odoo_model="sale.order",
                write_method="action_confirm",
                description="Confirm order",
            )
        ]
        entries = svc.classify(candidates)
        assert entries[0].risk_level == "R3"

    def test_can_certify_r1_r2_only(self, fresh_db):
        svc = WriteRiskMatrix()
        r2_candidates = [
            WriteDetectedCandidateModel(
                candidate_id="wc_test04",
                opportunity_code="test",
                odoo_model="sale.order.line",
                write_method="write",
                description="Update field",
            )
        ]
        entries = svc.classify(r2_candidates)
        assert svc.can_certify(entries) is True

    def test_cannot_certify_r3(self, fresh_db):
        svc = WriteRiskMatrix()
        r3_candidates = [
            WriteDetectedCandidateModel(
                candidate_id="wc_test05",
                opportunity_code="test",
                odoo_model="sale.order",
                write_method="action_confirm",
                description="Confirm",
            )
        ]
        entries = svc.classify(r3_candidates)
        assert svc.can_certify(entries) is False

    def test_overall_risk_is_max(self, fresh_db):
        svc = WriteRiskMatrix()
        candidates = [
            WriteDetectedCandidateModel(candidate_id="wc1", opportunity_code="t", odoo_model="m1", write_method="write", description="d"),
            WriteDetectedCandidateModel(candidate_id="wc2", opportunity_code="t", odoo_model="m2", write_method="action_confirm", description="d"),
        ]
        entries = svc.classify(candidates)
        assert svc.overall_risk_level(entries) == "R3"

    def test_all_candidates_blocked_for_real_writes(self, fresh_db):
        svc = WriteRiskMatrix()
        candidates = [
            WriteDetectedCandidateModel(candidate_id="wc1", opportunity_code="t", odoo_model="m1", write_method="write", description="d"),
        ]
        entries = svc.classify(candidates)
        assert all(e.can_execute_real_writes is False for e in entries)

    def test_empty_candidates_r1_certifiable(self, fresh_db):
        svc = WriteRiskMatrix()
        assert svc.overall_risk_level([]) == "R1"
        assert svc.can_certify([]) is True

    def test_blocking_issues_only_r3_r4(self, fresh_db):
        svc = WriteRiskMatrix()
        candidates = [
            WriteDetectedCandidateModel(candidate_id="wc1", opportunity_code="t", odoo_model="m1", write_method="write", description="d"),
            WriteDetectedCandidateModel(candidate_id="wc2", opportunity_code="t", odoo_model="m2", write_method="action_confirm", description="d"),
        ]
        entries = svc.classify(candidates)
        issues = svc.blocking_issues(entries)
        assert len(issues) == 1
        assert "action_confirm" in issues[0]
