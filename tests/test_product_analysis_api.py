import json

from fastapi.testclient import TestClient

from apps.api.main import app


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


def make_connection_payload(api_key: str = "super-secret") -> dict:
    return {
        "name": "Odoo Demo",
        "url": "https://empresa.odoo.com",
        "database": "empresa-prod",
        "username": "usuario@empresa.com",
        "api_key": api_key,
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


def _create_connection(client: TestClient):
    response = client.post("/v1/odoo/connections", json=make_connection_payload())
    assert response.status_code == 200
    return response.json()["connection_id"]


def test_product_analysis_ui_and_api(monkeypatch):
    fake_client = FakeReadOnlyOdooClient()
    monkeypatch.setattr("apps.api.routes.odoo.build_readonly_client", lambda config: fake_client)
    monkeypatch.setattr("erpguard.product.services.build_readonly_client", lambda config: fake_client)
    client = TestClient(app)
    connection_id = _create_connection(client)

    response = client.post(
        f"/v1/product/connections/{connection_id}/analyze",
        json={"include_samples": True, "sample_limits": {"sales_orders": 5, "products": 5, "custom_fields": 50}, "max_opportunities": 5},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["connection_id"] == connection_id
    assert body["status"] == "ok"
    assert body["read_only_mode"] is True
    assert body["snapshot"]["snapshot_id"].startswith("business_snapshot_")
    assert body["signals"]
    assert body["opportunities"]
    assert body["recommendation_cards"]
    assert body["roi_summary"]["average_score"] > 0
    assert body["next_recommended_action"]

    first_opportunity_id = body["opportunities"][0]["opportunity_id"]
    draft_response = client.post(f"/v1/product/opportunities/{first_opportunity_id}/draft")
    assert draft_response.status_code == 200
    draft_body = draft_response.json()
    assert draft_body["write_actions"] is False
    assert draft_body["runtime_mode"] == "dry_run_only"
    assert draft_body["draft_package"]["write_actions"] is False
    assert draft_body["draft_package"]["runtime_mode"] == "dry_run_only"

    snapshot_response = client.get(f"/v1/product/snapshots/{body['snapshot']['snapshot_id']}")
    assert snapshot_response.status_code == 200
    scan_response = client.get(f"/v1/product/scans/{body['scan_id']}")
    assert scan_response.status_code == 200
    draft_lookup = client.get(f"/v1/product/drafts/{draft_body['draft_id']}")
    assert draft_lookup.status_code == 200

    html = client.get("/demo").text
    assert "Business Analysis & Opportunity Scanner" in html
    assert "/v1/product/connections/" in html
