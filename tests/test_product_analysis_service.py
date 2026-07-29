import json

from erpguard.canonical.enums import ERPType
from erpguard.adapters.odoo.config import OdooConfig
from erpguard.db.repositories import create_connection, get_automation_draft, get_business_snapshot, get_opportunity_scan, list_automation_drafts, list_business_signals, list_opportunities
from erpguard.db.session import SessionLocal, init_db
from erpguard.release_ops.models import BusinessAnalysisRequest
from erpguard.release_ops.services import BusinessAnalysisService


class FakeReadOnlyOdooClient:
    def __init__(self):
        self.calls: list[tuple] = []

    def version(self):
        self.calls.append(("version",))
        return {"server_version": "19.0-20260513"}

    def authenticate(self):
        self.calls.append(("authenticate",))
        return 2

    def search_read(self, model, domain, fields, limit=None):
        self.calls.append(("search_read", model, domain, tuple(fields), limit))
        if model == "ir.module.module":
            return [{"name": "sale"}, {"name": "account"}]
        if model == "ir.model" and domain == [["model", "in", ["res.users", "ir.module.module", "ir.model", "ir.model.fields", "sale.order", "sale.order.line", "product.product", "product.template", "res.partner", "stock.quant", "stock.move", "stock.picking", "mrp.production", "mrp.bom", "account.move"]]]:
            return [{"model": value} for value in ["res.users", "ir.module.module", "ir.model", "ir.model.fields", "sale.order", "sale.order.line", "product.product", "product.template", "res.partner", "account.move"]]
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
        self.calls.append(("fields_get", model, tuple(attributes or [])))
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
        self.calls.append(("search_count", model, domain))
        if model == "sale.order":
            return 2
        if model == "product.product":
            return 1
        return 0


class FakeConnection:
    def __init__(self, config: dict):
        self.id = "conn_test"
        self.erp_type = "odoo"
        self.config_json = json.dumps(config)


def make_service():
    init_db()
    session = SessionLocal()
    connection = FakeConnection(
        {
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
    )
    connection_row = create_connection(session, "Odoo Demo", erp_type=ERPType.ODOO, config=json.loads(connection.config_json))
    config = OdooConfig.model_validate(json.loads(connection_row.config_json))
    return session, connection_row, config


def test_business_analysis_service_persists_snapshot_signals_and_scan(monkeypatch):
    session, connection, config = make_service()
    fake_client = FakeReadOnlyOdooClient()
    monkeypatch.setattr("erpguard.release_ops.services.build_readonly_client", lambda cfg: fake_client)

    result = BusinessAnalysisService(session, connection, config).analyze(BusinessAnalysisRequest())

    assert result.status == "ok"
    assert result.read_only_mode is True
    assert result.snapshot.connection_id == connection.id
    assert result.snapshot.odoo["server_version"] == "19.0-20260513"
    assert result.signals
    assert result.opportunities
    assert result.recommendation_cards
    assert result.roi_summary["average_score"] > 0
    assert "Review" in result.next_recommended_action

    snapshot_row = get_business_snapshot(session, result.snapshot.snapshot_id)
    scan_row = get_opportunity_scan(session, result.scan_id)
    signals = list_business_signals(session, result.snapshot.snapshot_id)
    opportunities = list_opportunities(session, result.scan_id)

    assert snapshot_row is not None
    assert scan_row is not None
    assert signals
    assert opportunities
    assert all(opportunity.status == "recommended" for opportunity in opportunities)

    session.close()


def test_roi_and_scanner_produce_business_opportunities(monkeypatch):
    session, connection, config = make_service()
    fake_client = FakeReadOnlyOdooClient()
    monkeypatch.setattr("erpguard.release_ops.services.build_readonly_client", lambda cfg: fake_client)

    result = BusinessAnalysisService(session, connection, config).analyze(BusinessAnalysisRequest())

    codes = {opportunity.code for opportunity in result.opportunities}
    assert "formula_mapping_alignment" in codes or "read_only_sales_preflight" in codes
    assert any(opportunity.roi.score > 0 for opportunity in result.opportunities)
    assert any(signal.code == "sales_module_present" for signal in result.signals)
    session.close()


def test_skill_draft_builder_creates_non_executable_draft(monkeypatch):
    session, connection, config = make_service()
    fake_client = FakeReadOnlyOdooClient()
    monkeypatch.setattr("erpguard.release_ops.services.build_readonly_client", lambda cfg: fake_client)

    result = BusinessAnalysisService(session, connection, config).analyze(BusinessAnalysisRequest())
    draft = BusinessAnalysisService(session, connection, config).draft(result.opportunities[0].opportunity_id)

    assert draft.write_actions is False
    assert draft.runtime_mode == "dry_run_only"
    assert draft.draft_package["runtime_mode"] == "dry_run_only"
    assert draft.draft_package["write_actions"] is False
    assert draft.draft_package["opportunity_id"] == result.opportunities[0].opportunity_id
    assert get_automation_draft(session, draft.draft_id) is not None
    assert list_automation_drafts(session, result.opportunities[0].opportunity_id)
    session.close()
