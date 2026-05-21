import json

from erpguard.canonical.enums import ERPType
from erpguard.adapters.odoo.config import OdooConfig
from erpguard.db.repositories import create_connection
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.activation_gate import ActivationGateService
from erpguard.product.approval_decision import ApprovalDecisionService
from erpguard.product.approval_request import ApprovalRequestService
from erpguard.product.draft_review import DraftReviewService
from erpguard.product.dry_run_proof import DryRunProofService
from erpguard.product.models import BusinessAnalysisRequest
from erpguard.product.services import BusinessAnalysisService
from erpguard.product.skill_package_builder import SkillPackageBuilder


class FakeOdooClient:
    def version(self): return {"server_version": "19.0-test"}
    def authenticate(self): return 1
    def search_read(self, model, domain, fields, limit=None):
        if model == "ir.module.module": return [{"name": "sale"}]
        if model == "ir.model": return [{"model": "sale.order"}]
        if model == "sale.order": return [{"id": 1, "name": "S001", "state": "sale", "order_line": []}]
        if model == "product.product": return [{"id": 1, "display_name": "Prod", "default_code": "P1"}]
        return []
    def fields_get(self, model, attributes=None): return {"id": {}, "name": {}}
    def search_count(self, model, domain):
        if model == "sale.order": return 1
        if model == "product.product": return 1
        return 0


_CONFIG = {
    "url": "https://example.odoo.com", "database": "demo",
    "username": "user@example.com", "api_key": "secret",
    "formula_model": "x_sale_formula_line", "capacity_field": "x_studio_capacidad_ml",
    "field_mappings": {},
}
_APPROVER = {"type": "user", "id": "approver1", "display_name": "Approver"}
_OPERATOR = {"type": "user", "id": "op1", "display_name": "Operator"}


def _make_full_flow(monkeypatch):
    init_db()
    session = SessionLocal()
    monkeypatch.setattr("erpguard.product.services.build_readonly_client", lambda cfg: FakeOdooClient())
    connection = create_connection(session, "Odoo", erp_type=ERPType.ODOO, config=_CONFIG)
    config = OdooConfig.model_validate(_CONFIG)
    result = BusinessAnalysisService(session, connection, config).analyze(BusinessAnalysisRequest())
    draft = BusinessAnalysisService(session, connection, config).draft(result.opportunities[0].opportunity_id)
    review = DraftReviewService(session).create(draft.draft_id)
    compiled = SkillPackageBuilder(session).build(review.review_id)
    return session, compiled.skill_id


def test_activation_gate_blocked_without_proof_and_approval(monkeypatch):
    session, skill_id = _make_full_flow(monkeypatch)

    gate = ActivationGateService(session).evaluate(skill_id)

    assert gate.can_execute_real_writes is False
    assert gate.approved_for_real_execution is False
    check_ids = {c.check_id if hasattr(c, "check_id") else c["check_id"] for c in gate.checks}
    assert "real_execution_blocked" in check_ids
    session.close()


def test_activation_gate_open_after_full_flow(monkeypatch):
    session, skill_id = _make_full_flow(monkeypatch)

    DryRunProofService(session).run(skill_id)
    ApprovalRequestService(session).create(skill_id=skill_id, requested_by=_OPERATOR, reason="Governance review.")
    ApprovalDecisionService(session).decide(skill_id=skill_id, decided_by=_APPROVER, decision="approve", reason="All good.")

    gate = ActivationGateService(session).evaluate(skill_id)

    assert gate.gate_status == "open"
    assert gate.can_activate is True
    assert gate.can_execute_real_writes is False
    assert gate.approved_for_real_execution is False
    real_exec_check = next(
        (c for c in gate.checks if (c.check_id if hasattr(c, "check_id") else c["check_id"]) == "real_execution_blocked"),
        None,
    )
    assert real_exec_check is not None
    passed = real_exec_check.passed if hasattr(real_exec_check, "passed") else real_exec_check["passed"]
    assert passed is True
    session.close()


def test_activation_gate_always_blocks_real_execution(monkeypatch):
    session, skill_id = _make_full_flow(monkeypatch)

    gate = ActivationGateService(session).evaluate(skill_id)

    assert gate.can_execute_real_writes is False
    assert gate.approved_for_real_execution is False
    session.close()
