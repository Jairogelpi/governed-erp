from erpguard.canonical.enums import ERPType
from erpguard.adapters.odoo.config import OdooConfig
from erpguard.db.repositories import create_connection
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.approval_decision import ApprovalDecisionService
from erpguard.product.approval_request import ApprovalRequestService
from erpguard.product.draft_review import DraftReviewService
from erpguard.product.models import BusinessAnalysisRequest
from erpguard.product.services import BusinessAnalysisService
from erpguard.product.skill_package_builder import SkillPackageBuilder


class FakeOdooClient:
    def version(self):
        return {"server_version": "19.0-test"}

    def authenticate(self):
        return 1

    def search_read(self, model, domain, fields, limit=None):
        if model == "ir.module.module":
            return [{"name": "sale"}]
        if model == "ir.model":
            return [{"model": "sale.order"}]
        if model == "sale.order":
            return [{"id": 1, "name": "S001", "state": "sale", "order_line": []}]
        if model == "product.product":
            return [{"id": 1, "display_name": "Prod", "default_code": "P1"}]
        return []

    def fields_get(self, model, attributes=None):
        return {"id": {}, "name": {}}

    def search_count(self, model, domain):
        if model == "sale.order":
            return 1
        if model == "product.product":
            return 1
        return 0


_CONFIG = {
    "url": "https://example.odoo.com",
    "database": "demo",
    "username": "user@example.com",
    "api_key": "secret",
    "formula_model": "x_sale_formula_line",
    "capacity_field": "x_studio_capacidad_ml",
    "field_mappings": {},
}
_APPROVER = {"type": "user", "id": "approver1", "display_name": "Approver"}
_OPERATOR = {"type": "user", "id": "op1", "display_name": "Operator"}


def _make_request(monkeypatch):
    init_db()
    session = SessionLocal()
    monkeypatch.setattr(
        "erpguard.product.services.build_readonly_client", lambda cfg: FakeOdooClient()
    )
    connection = create_connection(session, "Odoo", erp_type=ERPType.ODOO, config=_CONFIG)
    config = OdooConfig.model_validate(_CONFIG)
    result = BusinessAnalysisService(session, connection, config).analyze(BusinessAnalysisRequest())
    draft = BusinessAnalysisService(session, connection, config).draft(
        result.opportunities[0].opportunity_id
    )
    review = DraftReviewService(session).create(draft.draft_id)
    compiled = SkillPackageBuilder(session).build(review.review_id)
    ApprovalRequestService(session).create(
        skill_id=compiled.skill_id, requested_by=_OPERATOR, reason="Governance review."
    )
    return session, compiled.skill_id


def test_approval_decision_approve_sets_correct_flags(monkeypatch):
    session, skill_id = _make_request(monkeypatch)

    decision = ApprovalDecisionService(session).decide(
        skill_id=skill_id,
        decided_by=_APPROVER,
        decision="approve",
        reason="Guards verified. Dry-run proof passed.",
    )

    assert decision.decision == "approve"
    assert decision.can_execute_real_writes is False
    assert decision.approved_for_real_execution is False
    assert decision.evidence["can_execute_real_writes"] is False
    assert decision.evidence["approved_for_real_execution"] is False
    session.close()


def test_approval_decision_reject(monkeypatch):
    session, skill_id = _make_request(monkeypatch)

    decision = ApprovalDecisionService(session).decide(
        skill_id=skill_id,
        decided_by=_APPROVER,
        decision="reject",
        reason="Needs more context.",
    )

    assert decision.decision == "reject"
    assert decision.can_execute_real_writes is False
    session.close()


def test_approval_decision_invalid_choice(monkeypatch):
    session, skill_id = _make_request(monkeypatch)
    import pytest

    with pytest.raises(ValueError, match="not valid"):
        ApprovalDecisionService(session).decide(
            skill_id=skill_id,
            decided_by=_APPROVER,
            decision="execute_now",
            reason="trying to execute",
        )
    session.close()


def test_approval_decision_history_lists_all_decisions(monkeypatch):
    session, skill_id = _make_request(monkeypatch)

    ApprovalDecisionService(session).decide(
        skill_id=skill_id, decided_by=_APPROVER, decision="approve", reason="ok"
    )
    history = ApprovalDecisionService(session).list_history(skill_id)

    assert len(history) >= 1
    assert all(d.can_execute_real_writes is False for d in history)
    assert all(d.approved_for_real_execution is False for d in history)
    session.close()
