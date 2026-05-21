from erpguard.adapters.odoo.config import OdooConfig
from erpguard.adapters.odoo.diagnosis import OdooDiagnosisService
from erpguard.adapters.odoo.readonly_client import READ_ONLY_ALLOWED_METHODS


CORE_MODELS = [
    "res.users",
    "ir.module.module",
    "ir.model",
    "ir.model.fields",
    "sale.order",
    "sale.order.line",
    "product.product",
    "product.template",
    "res.partner",
    "stock.quant",
    "stock.move",
    "stock.picking",
    "mrp.production",
    "mrp.bom",
    "account.move",
]


class FakeDiagnosisClient:
    def __init__(self, *, permission_denied_models: set[str] | None = None):
        self.permission_denied_models = permission_denied_models or set()
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
        if model == "ir.model" and domain == [["model", "in", CORE_MODELS]]:
            return [{"model": model_name} for model_name in CORE_MODELS]
        if model == "ir.model" and domain == [["model", "like", "x_%"]]:
            return [{"model": "x_sale_formula_line"}]
        if model == "sale.order":
            return [
                {"id": 42, "name": "S00042", "state": "sale", "order_line": [90, 91]},
                {"id": 43, "name": "S00043", "state": "draft", "order_line": [92]},
            ][: limit or 2]
        if model == "product.product":
            return [
                {"id": 15, "display_name": "Perfume 100ML", "default_code": "PERF100", "x_studio_capacidad_ml": 100},
                {"id": 16, "display_name": "Perfume 50ML", "default_code": "PERF050", "x_studio_capacidad_ml": 50},
            ][: limit or 2]
        return []

    def fields_get(self, model, attributes=None):
        self.calls.append(("fields_get", model, tuple(attributes or [])))
        if model in self.permission_denied_models:
            raise PermissionError(f"Access denied to {model}")
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
            return {
                "id": {},
                "display_name": {},
                "default_code": {},
            }
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
        return 2


def make_service(*, capacity_field: str = "x_studio_capacidad_ml", formula_model: str = "x_sale_formula_line", field_mappings: dict | None = None, permission_denied_models: set[str] | None = None):
    client = FakeDiagnosisClient(permission_denied_models=permission_denied_models)
    config = OdooConfig(
        url="https://example.odoo.com",
        database="demo",
        username="user@example.com",
        api_key="secret",
        formula_model=formula_model,
        capacity_field=capacity_field,
        field_mappings=field_mappings or {
            "product_capacity_ml": capacity_field,
            "formula_sale_line_id": "x_studio_sale_line_id",
            "formula_fragrance_id": "x_studio_fragancia_id",
            "formula_ml_per_unit": "x_studio_ml_por_unidad",
            "formula_ml_total": "x_studio_ml_total_pedido",
        },
    )
    return OdooDiagnosisService(client=client, config=config), client


def test_diagnosis_returns_version_and_uid():
    service, client = make_service()

    result = service.run()

    assert result["odoo"]["server_version"] == "19.0"
    assert result["odoo"]["uid"] == 8
    assert ("version",) in client.calls
    assert ("authenticate",) in client.calls


def test_diagnosis_detects_sales_stock_mrp_account_modules():
    service, _ = make_service()

    result = service.run()

    assert result["modules"] == {"sale": True, "stock": True, "mrp": True, "account": True}
    assert "sale" in result["detected"]["installed_modules"]
    assert "stock" in result["detected"]["installed_modules"]
    assert "mrp" in result["detected"]["installed_modules"]
    assert "account" in result["detected"]["installed_modules"]


def test_diagnosis_detects_core_models():
    service, _ = make_service()

    result = service.run()

    assert "sale.order" in result["models"]["core_detected"]
    assert "product.product" in result["models"]["core_detected"]
    assert "mrp.production" in result["detected"]["core_models"]


def test_diagnosis_detects_custom_fields():
    service, _ = make_service()

    result = service.run()

    assert "x_studio_capacidad_ml" in result["detected"]["custom_fields"]
    assert "x_studio_formula_ids" in result["detected"]["custom_fields"]


def test_diagnosis_warns_when_capacity_field_missing():
    service, _ = make_service(capacity_field="x_missing_capacity")

    result = service.run()

    assert any(warning["code"] == "capacity_field_missing" for warning in result["warnings"])


def test_diagnosis_warns_when_formula_model_missing():
    service, _ = make_service(formula_model="x_missing_formula_model")

    result = service.run()

    assert any(warning["code"] == "formula_model_missing" for warning in result["warnings"])


def test_diagnosis_handles_permission_denied_model():
    service, _ = make_service(permission_denied_models={"mrp.production"})

    result = service.run()

    assert result["fields"]["mrp.production"]["status"] == "permission_denied"
    assert any(warning["code"] == "read_permission_limited" for warning in result["warnings"])


def test_diagnosis_never_calls_write_methods():
    service, client = make_service()

    service.run()

    forbidden_methods = {
        method
        for call in client.calls
        if call and call[0] == "execute_kw"
        for method in [call[2]]
        if method not in READ_ONLY_ALLOWED_METHODS
    }
    assert forbidden_methods == set()
