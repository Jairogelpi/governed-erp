
from erpguard.canonical.enums import ERPType
from erpguard.adapters.odoo.config import OdooConfig
from erpguard.db.repositories import (
    create_connection,
    get_automation_draft_review,
    list_draft_reviews,
)
from erpguard.db.session import SessionLocal, init_db
from erpguard.release_ops.draft_review import DraftReviewService
from erpguard.release_ops.models import BusinessAnalysisRequest
from erpguard.release_ops.services import BusinessAnalysisService


class FakeReadOnlyOdooClient:
    def version(self):
        return {"server_version": "19.0-20260513"}

    def authenticate(self):
        return 2

    def search_read(self, model, domain, fields, limit=None):
        if model == "ir.module.module":
            return [{"name": "sale"}, {"name": "account"}]
        if model == "ir.model" and domain == [["model", "in", ["res.users", "ir.module.module", "ir.model", "ir.model.fields", "sale.order", "sale.order.line", "product.product", "product.template", "res.partner", "stock.quant", "stock.move", "stock.picking", "mrp.production", "mrp.bom", "account.move"]]]:
            return [{"model": m} for m in ["res.users", "sale.order", "product.product"]]
        if model == "ir.model" and domain == [["model", "like", "x_%"]]:
            return []
        if model == "sale.order":
            return [{"id": 42, "name": "S00042", "state": "sale", "order_line": [90]}]
        if model == "sale.order.line":
            return [{"id": 90, "product_id": [15, "Perfume 100ML"], "product_uom_qty": 10, "price_unit": 12.3}]
        if model == "product.product":
            return [{"id": 15, "display_name": "Perfume 100ML", "default_code": "PERF100"}]
        return []

    def fields_get(self, model, attributes=None):
        if model == "sale.order":
            return {"id": {}, "name": {}, "state": {}, "order_line": {}, "amount_total": {}}
        if model == "sale.order.line":
            return {"id": {}, "order_id": {}, "product_id": {}, "product_uom_qty": {}, "price_unit": {}, "price_subtotal": {}}
        if model == "product.product":
            return {"id": {}, "display_name": {}, "default_code": {}, "tracking": {}, "standard_price": {}}
        if model == "product.template":
            return {"id": {}, "display_name": {}, "default_code": {}}
        return {}

    def search_count(self, model, domain):
        if model == "sale.order":
            return 2
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
    "field_mappings": {
        "product_capacity_ml": "x_studio_capacidad_ml",
        "formula_sale_line_id": "x_studio_sale_line_id",
        "formula_fragrance_id": "x_studio_fragancia_id",
        "formula_ml_per_unit": "x_studio_ml_por_unidad",
        "formula_ml_total": "x_studio_ml_total_pedido",
    },
}


def _make_draft(monkeypatch):
    init_db()
    session = SessionLocal()
    fake_client = FakeReadOnlyOdooClient()
    monkeypatch.setattr("erpguard.release_ops.services.build_readonly_client", lambda cfg: fake_client)
    connection = create_connection(session, "Odoo Demo", erp_type=ERPType.ODOO, config=_ODOO_CONFIG)
    config = OdooConfig.model_validate(_ODOO_CONFIG)
    result = BusinessAnalysisService(session, connection, config).analyze(BusinessAnalysisRequest())
    draft = BusinessAnalysisService(session, connection, config).draft(result.opportunities[0].opportunity_id)
    return session, draft


def test_draft_review_service_creates_review(monkeypatch):
    session, draft = _make_draft(monkeypatch)

    review = DraftReviewService(session).create(draft.draft_id)

    assert review.review_id.startswith("draft_review_")
    assert review.draft_id == draft.draft_id
    assert review.status == "ready_to_compile"
    assert review.guards
    guard_names = [g.name if hasattr(g, "name") else g["name"] for g in review.guards]
    assert "read_only" in guard_names
    assert "no_odoo_writes" in guard_names
    assert "dry_run_only" in guard_names
    assert "requires_approval_before_activation" in guard_names
    assert review.input_schema
    assert review.output_schema
    assert review.test_cases
    assert review.skill_id is None

    row = get_automation_draft_review(session, review.review_id)
    assert row is not None
    assert row.status == "ready_to_compile"
    session.close()


def test_draft_review_service_get_or_create_returns_existing(monkeypatch):
    session, draft = _make_draft(monkeypatch)

    review1 = DraftReviewService(session).get_or_create(draft.draft_id)
    review2 = DraftReviewService(session).get_or_create(draft.draft_id)

    assert review1.review_id == review2.review_id
    assert len(list_draft_reviews(session, draft.draft_id)) == 1
    session.close()


def test_draft_review_service_schema_matches_opportunity(monkeypatch):
    session, draft = _make_draft(monkeypatch)

    review = DraftReviewService(session).create(draft.draft_id)

    input_names = [f.name if hasattr(f, "name") else f["name"] for f in review.input_schema]
    assert "connection_id" in input_names
    assert review.test_cases
    for tc in review.test_cases:
        decision = tc.expected_decision if hasattr(tc, "expected_decision") else tc["expected_decision"]
        assert decision in {"allow", "review_required", "block"}
    session.close()
