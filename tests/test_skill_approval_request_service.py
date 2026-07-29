from erpguard.canonical.enums import ERPType
from erpguard.adapters.odoo.config import OdooConfig
from erpguard.db.repositories import (
    create_connection,
    get_approval_request,
)
from erpguard.db.session import SessionLocal, init_db
from erpguard.release_ops.approval_request import ApprovalRequestService
from erpguard.release_ops.draft_review import DraftReviewService
from erpguard.product.models import BusinessAnalysisRequest
from erpguard.release_ops.services import BusinessAnalysisService
from erpguard.release_ops.skill_package_builder import SkillPackageBuilder


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


def _make_compiled_skill(monkeypatch):
    init_db()
    session = SessionLocal()
    monkeypatch.setattr(
        "erpguard.release_ops.services.build_readonly_client", lambda cfg: FakeOdooClient()
    )
    connection = create_connection(session, "Odoo", erp_type=ERPType.ODOO, config=_CONFIG)
    config = OdooConfig.model_validate(_CONFIG)
    result = BusinessAnalysisService(session, connection, config).analyze(BusinessAnalysisRequest())
    draft = BusinessAnalysisService(session, connection, config).draft(
        result.opportunities[0].opportunity_id
    )
    review = DraftReviewService(session).create(draft.draft_id)
    compiled = SkillPackageBuilder(session).build(review.review_id)
    return session, compiled.skill_id


def test_approval_request_service_creates_request(monkeypatch):
    session, skill_id = _make_compiled_skill(monkeypatch)

    req = ApprovalRequestService(session).create(
        skill_id=skill_id,
        requested_by={"type": "user", "id": "op1", "display_name": "Operator"},
        reason="Ready for governance review.",
    )

    assert req.request_id.startswith("approval_request_")
    assert req.skill_id == skill_id
    assert req.status == "pending"
    assert req.can_execute_real_writes is False
    assert "runtime_mode" in req.context
    assert req.context["runtime_mode"] == "dry_run_only"
    assert req.context["write_actions"] is False

    row = get_approval_request(session, req.request_id)
    assert row is not None
    assert row.can_execute_real_writes is False
    session.close()


def test_approval_request_service_get_latest(monkeypatch):
    session, skill_id = _make_compiled_skill(monkeypatch)

    ApprovalRequestService(session).create(
        skill_id=skill_id,
        requested_by={"type": "user", "id": "op1", "display_name": "Operator"},
        reason="First request.",
    )
    latest = ApprovalRequestService(session).get_latest(skill_id)

    assert latest is not None
    assert latest.skill_id == skill_id
    assert latest.can_execute_real_writes is False
    session.close()


def test_approval_request_not_found_for_missing_skill():
    init_db()
    session = SessionLocal()

    latest = ApprovalRequestService(session).get_latest("skill_does_not_exist")
    assert latest is None
    session.close()
