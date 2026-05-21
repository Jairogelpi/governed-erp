from fastapi.testclient import TestClient

from apps.api.main import app


class FakeApiOdooClient:
    def __init__(self):
        self.calls: list[tuple] = []

    def version(self):
        self.calls.append(("version",))
        return {"server_version": "19.0"}

    def authenticate(self):
        self.calls.append(("authenticate",))
        return 8

    def search_read(self, model, domain, fields, limit=None):
        self.calls.append(("search_read", model, domain, tuple(fields), limit))
        if model == "ir.module.module":
            return [
                {"name": "sale"},
                {"name": "stock"},
                {"name": "mrp"},
                {"name": "account"},
            ]
        if model == "ir.model" and domain == [["model", "in", ["res.users", "ir.module.module", "ir.model", "ir.model.fields", "sale.order", "sale.order.line", "product.product", "product.template", "res.partner", "stock.quant", "stock.move", "stock.picking", "mrp.production", "mrp.bom", "account.move"]]]:
            return [{"model": value} for value in ["res.users", "ir.module.module", "ir.model", "ir.model.fields", "sale.order", "sale.order.line", "product.product", "product.template", "res.partner", "stock.quant", "stock.move", "stock.picking", "mrp.production", "mrp.bom", "account.move"]]
        if model == "ir.model" and domain == [["model", "like", "x_%"]]:
            return [{"model": "x_sale_formula_line"}]
        if model == "sale.order":
            return [
                {"id": 42, "name": "S00042", "state": "sale", "order_line": [90, 91]},
                {"id": 43, "name": "S00043", "state": "draft", "order_line": [92]},
            ][: limit or 2]
        if model == "sale.order.line":
            return [
                {"id": 90, "product_id": [15, "Perfume 100ML"], "product_uom_qty": 10, "price_unit": 12.3},
                {"id": 91, "product_id": [16, "Perfume 50ML"], "product_uom_qty": 5, "price_unit": 8.9},
            ]
        if model == "product.product":
            if ["id", "display_name", "default_code", "x_studio_capacidad_ml"] == list(fields):
                return [
                    {"id": 15, "display_name": "Perfume 100ML", "default_code": "PERF100", "x_studio_capacidad_ml": 100},
                    {"id": 16, "display_name": "Perfume 50ML", "default_code": "PERF050", "x_studio_capacidad_ml": 50},
                ][: limit or 2]
            return [
                {"id": 15, "display_name": "Perfume 100ML", "default_code": "PERF100", "x_studio_capacidad_ml": 100},
                {"id": 16, "display_name": "Perfume 50ML", "default_code": "PERF050", "x_studio_capacidad_ml": 50},
            ]
        return []

    def fields_get(self, model, attributes=None):
        self.calls.append(("fields_get", model, tuple(attributes or [])))
        if model == "sale.order":
            return {
                "id": {},
                "name": {},
                "state": {},
                "partner_id": {},
                "order_line": {},
                "amount_total": {},
                "x_studio_formula_ids": {},
            }
        if model == "sale.order.line":
            return {
                "id": {},
                "order_id": {},
                "product_id": {},
                "product_uom_qty": {},
                "price_unit": {},
                "price_subtotal": {},
            }
        if model == "product.product":
            return {
                "id": {},
                "display_name": {},
                "default_code": {},
                "tracking": {},
                "standard_price": {},
                "x_studio_capacidad_ml": {},
            }
        if model == "product.template":
            return {"id": {}, "display_name": {}, "default_code": {}}
        if model == "x_sale_formula_line":
            return {
                "id": {},
                "x_studio_fragancia_id": {},
                "x_studio_ml_por_unidad": {},
                "x_studio_ml_total_pedido": {},
                "x_studio_sale_line_id": {},
            }
        return {}

    def search_count(self, model, domain):
        self.calls.append(("search_count", model, domain))
        if model == "sale.order":
            return 2
        if model == "product.product":
            return 2
        return 0


class FakeAuthFailClient(FakeApiOdooClient):
    def authenticate(self):
        self.calls.append(("authenticate",))
        raise RuntimeError("Odoo authentication failed.")


def make_connection_payload(api_key: str = "super-secret") -> dict:
    return {
        "name": "Odoo Esenssi Producción",
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


def test_create_odoo_connection_redacts_api_key(monkeypatch):
    client = TestClient(app)
    connection_id = _create_connection(client)

    response = client.get(f"/v1/connections/{connection_id}")

    assert response.status_code == 200
    assert response.json()["config"]["api_key"] == "***REDACTED***"
    assert "super-secret" not in response.text


def test_test_odoo_connection_success(monkeypatch):
    fake_client = FakeApiOdooClient()
    monkeypatch.setattr("apps.api.routes.odoo.build_readonly_client", lambda config: fake_client)
    client = TestClient(app)
    connection_id = _create_connection(client)

    response = client.post(f"/v1/odoo/connections/{connection_id}/test")

    assert response.status_code == 200
    body = response.json()
    assert body["connection_id"] == connection_id
    assert body["status"] == "ok"
    assert body["erp_type"] == "odoo"
    assert body["server_version"] == "19.0"
    assert body["uid"] == 8
    assert body["read_only_mode"] is True


def test_test_odoo_connection_auth_failure(monkeypatch):
    monkeypatch.setattr("apps.api.routes.odoo.build_readonly_client", lambda config: FakeAuthFailClient())
    client = TestClient(app)
    connection_id = _create_connection(client)

    response = client.post(f"/v1/odoo/connections/{connection_id}/test")

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "odoo_authentication_failed"
    assert body["error"]["details"]["connection_id"] == connection_id


def test_diagnose_odoo_connection_success(monkeypatch):
    fake_client = FakeApiOdooClient()
    monkeypatch.setattr("apps.api.routes.odoo.build_readonly_client", lambda config: fake_client)
    client = TestClient(app)
    connection_id = _create_connection(client)

    response = client.post(
        f"/v1/odoo/connections/{connection_id}/diagnose",
        json={"include_samples": True, "sample_limits": {"sales_orders": 5, "products": 5, "custom_fields": 50}},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["connection_id"] == connection_id
    assert body["status"] == "ok"
    assert body["read_only_mode"] is True
    assert body["odoo"]["server_version"] == "19.0"
    assert body["odoo"]["uid"] == 8
    assert body["modules"]["sale"] is True
    assert "sale.order" in body["detected"]["core_models"]
    assert "x_studio_capacidad_ml" in body["detected"]["custom_fields"]
    assert body["samples"]["sales_orders"][0]["name"] == "S00042"
    assert body["samples"]["products"][0]["capacity_ml"] == 100
    assert body["warnings"] == []
    assert body["next_recommended_action"] == "Run read-only sales order canonical mapping."


def test_diagnose_odoo_connection_returns_read_only_true(monkeypatch):
    fake_client = FakeApiOdooClient()
    monkeypatch.setattr("apps.api.routes.odoo.build_readonly_client", lambda config: fake_client)
    client = TestClient(app)
    connection_id = _create_connection(client)

    response = client.post(f"/v1/odoo/connections/{connection_id}/diagnose", json={"include_samples": False})

    assert response.status_code == 200
    assert response.json()["read_only_mode"] is True


def test_raw_sales_order_summary_success(monkeypatch):
    fake_client = FakeApiOdooClient()
    monkeypatch.setattr("apps.api.routes.odoo.build_readonly_client", lambda config: fake_client)
    client = TestClient(app)
    connection_id = _create_connection(client)

    response = client.get(f"/v1/odoo/connections/{connection_id}/sales-orders/S00042/raw-summary")

    assert response.status_code == 200
    body = response.json()
    assert body["connection_id"] == connection_id
    assert body["order_reference"] == "S00042"
    assert body["status"] == "found"
    assert body["read_only_mode"] is True
    assert body["order"]["name"] == "S00042"
    assert body["order"]["line_count"] == 2
    assert body["lines"][0]["product_name"] == "Perfume 100ML"


def test_raw_sales_order_summary_not_found(monkeypatch):
    class EmptyClient(FakeApiOdooClient):
        def search_read(self, model, domain, fields, limit=None):
            if model == "sale.order":
                return []
            return super().search_read(model, domain, fields, limit=limit)

    monkeypatch.setattr("apps.api.routes.odoo.build_readonly_client", lambda config: EmptyClient())
    client = TestClient(app)
    connection_id = _create_connection(client)

    response = client.get(f"/v1/odoo/connections/{connection_id}/sales-orders/UNKNOWN/raw-summary")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "odoo_sales_order_not_found"
    assert body["error"]["details"]["connection_id"] == connection_id
