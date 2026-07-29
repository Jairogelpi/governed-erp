import json

from erpguard.canonical.enums import ERPType
from erpguard.adapters.odoo.config import OdooConfig
from erpguard.db.repositories import (
    create_connection,
    get_automation_draft_review,
    get_skill,
    get_latest_skill_version,
)
from erpguard.db.session import SessionLocal, init_db
from erpguard.release_ops.draft_review import DraftReviewService
from erpguard.release_ops.skill_package_builder import SkillPackageBuilder
from erpguard.product.models import BusinessAnalysisRequest
from erpguard.release_ops.services import BusinessAnalysisService


class FakeReadOnlyOdooClient:
    def version(self):
        return {"server_version": "19.0-20260513"}

    def authenticate(self):
        return 2

    def search_read(self, model, domain, fields, limit=None):
        if model == "ir.module.module":
            return [{"name": "sale"}, {"name": "account"}]
        if model == "ir.model":
            return [{"model": "sale.order"}, {"model": "product.product"}]
        if model == "sale.order":
            return [{"id": 42, "name": "S00042", "state": "sale", "order_line": []}]
        if model == "product.product":
            return [{"id": 15, "display_name": "Perfume", "default_code": "PERF"}]
        return []

    def fields_get(self, model, attributes=None):
        if model in ("sale.order", "sale.order.line", "product.product", "product.template"):
            return {"id": {}, "name": {}}
        return {}

    def search_count(self, model, domain):
        if model == "sale.order":
            return 1
        if model == "product.product":
            return 1
        return 0


_ODOO_CONFIG = {
    "url": "https://example.odoo.com",
    "database": "demo",
    "username": "user@example.com",
    "api_key": "secret",
    "formula_model": "x_sale_formula_line",
    "capacity_field": "x_studio_capacidad_ml",
    "field_mappings": {},
}


def _make_review(monkeypatch):
    init_db()
    session = SessionLocal()
    fake_client = FakeReadOnlyOdooClient()
    monkeypatch.setattr("erpguard.release_ops.services.build_readonly_client", lambda cfg: fake_client)
    connection = create_connection(session, "Odoo Demo", erp_type=ERPType.ODOO, config=_ODOO_CONFIG)
    config = OdooConfig.model_validate(_ODOO_CONFIG)
    result = BusinessAnalysisService(session, connection, config).analyze(BusinessAnalysisRequest())
    draft = BusinessAnalysisService(session, connection, config).draft(result.opportunities[0].opportunity_id)
    review = DraftReviewService(session).create(draft.draft_id)
    return session, draft, review


def test_skill_package_builder_creates_skill_in_registry(monkeypatch):
    session, draft, review = _make_review(monkeypatch)

    compiled = SkillPackageBuilder(session).build(review.review_id)

    assert compiled.skill_id.startswith("skill_")
    assert compiled.version_id.startswith("skill_version_")
    assert compiled.write_actions is False
    assert compiled.runtime_mode == "dry_run_only"
    assert compiled.requires_approval_before_activation is True
    assert "read_only" in compiled.guards
    assert "no_odoo_writes" in compiled.guards
    assert "dry_run_only" in compiled.guards

    skill_row = get_skill(session, compiled.skill_id)
    assert skill_row is not None
    assert skill_row.status == "draft"

    version_row = get_latest_skill_version(session, compiled.skill_id)
    assert version_row is not None
    assert version_row.runtime_type == "dry_run_only"
    assert version_row.llm_required_for_repeated_runs is False

    package = json.loads(version_row.skill_package_json)
    assert package["write_actions"] is False
    assert package["runtime_mode"] == "dry_run_only"
    assert package["requires_approval_before_activation"] is True
    assert "no_odoo_writes" in package["guards"]

    review_row = get_automation_draft_review(session, review.review_id)
    assert review_row.status == "compiled"
    assert review_row.skill_id == compiled.skill_id
    session.close()


def test_skill_package_builder_returns_existing_compiled_skill(monkeypatch):
    session, draft, review = _make_review(monkeypatch)

    compiled1 = SkillPackageBuilder(session).build(review.review_id)
    compiled2 = SkillPackageBuilder(session).build(review.review_id)

    assert compiled1.skill_id == compiled2.skill_id
    assert compiled1.version_id == compiled2.version_id
    session.close()


def test_skill_package_builder_package_has_workflow_steps(monkeypatch):
    session, draft, review = _make_review(monkeypatch)

    compiled = SkillPackageBuilder(session).build(review.review_id)

    version_row = get_latest_skill_version(session, compiled.skill_id)
    package = json.loads(version_row.skill_package_json)
    step_ids = [s["id"] for s in package.get("workflow", [])]
    assert "load_review" in step_ids
    assert "guard_check" in step_ids
    assert "dry_run_output" in step_ids
    session.close()
