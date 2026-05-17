import pytest

from erpguard.adapters.base import ERPAdapter
from erpguard.adapters.factory import get_adapter
from erpguard.adapters.odoo.adapter import OdooAdapter
from erpguard.adapters.odoo.config import OdooConfig
from erpguard.canonical.enums import CanonicalAction, ERPType
from erpguard.canonical.objects import SalesOrder
from erpguard.core.errors import AdapterConfigurationError, ObjectNotFoundError


class MockOdooClient:
    def __init__(self):
        self.calls: list[tuple] = []

    def version(self):
        self.calls.append(("version",))
        return {"server_version": "17.0"}

    def authenticate(self):
        self.calls.append(("authenticate",))
        return 2

    def search_read(self, model, domain, fields, limit=None):
        self.calls.append(("search_read", model, domain, tuple(fields), limit))
        if model == "sale.order" and domain == [["name", "=", "S00040"]]:
            return [sale_order_payload()]
        if model == "sale.order" and domain == [["id", "=", 40]]:
            return [sale_order_payload()]
        if model == "sale.order.line":
            return line_payloads()
        if model == "product.product":
            return product_payloads()
        if model == "x.sale.formula.line":
            return formula_payloads()
        return []

    def read(self, model, ids, fields):
        self.calls.append(("read", model, tuple(ids), tuple(fields)))
        if model == "sale.order" and ids == [40]:
            return [sale_order_payload()]
        return []


def sale_order_payload() -> dict:
    return {
        "id": 40,
        "name": "S00040",
        "state": "draft",
        "currency_id": [1, "EUR"],
        "amount_total": 250.0,
        "partner_id": [10, "ACME Customer"],
        "company_id": [1, "Esenssi"],
        "order_line": [101],
    }


def line_payloads() -> list[dict]:
    return [
        {
            "id": 101,
            "product_id": [1001, "Mikado 100 ML"],
            "product_uom_qty": 2.0,
            "price_unit": 125.0,
            "price_subtotal": 250.0,
        }
    ]


def product_payloads() -> list[dict]:
    return [
        {
            "id": 1001,
            "display_name": "Mikado 100 ML",
            "active": True,
            "detailed_type": "product",
            "tracking": "lot",
            "x_capacity_ml": 100.0,
        }
    ]


def formula_payloads() -> list[dict]:
    return [
        {
            "id": 5001,
            "sale_order_line_id": [101, "S00040 - Mikado"],
            "component_name": "Amber",
            "ml_per_unit": 100.0,
            "ml_total": 200.0,
        }
    ]


def make_adapter(client=None) -> OdooAdapter:
    return OdooAdapter(
        config=OdooConfig(
            url="https://example.odoo.com",
            database="demo",
            username="user@example.com",
            api_key="secret",
        ),
        client=client or MockOdooClient(),
    )


def test_odoo_adapter_implements_erp_adapter_contract():
    adapter = make_adapter()

    assert isinstance(adapter, ERPAdapter)
    assert adapter.get_erp_type() is ERPType.ODOO


def test_health_check_returns_ok_when_version_and_auth_work():
    adapter = make_adapter()

    assert adapter.health_check() == {
        "status": "ok",
        "erp_type": "odoo",
        "server_version": "17.0",
        "uid": 2,
    }


def test_get_sales_order_by_reference_maps_mocked_odoo_payload_to_canonical():
    client = MockOdooClient()
    adapter = make_adapter(client)

    order = adapter.get_sales_order_by_reference("S00040")

    assert isinstance(order, SalesOrder)
    assert order.reference == "S00040"
    assert order.lines[0].product.capacity_ml == 100
    assert order.lines[0].formula_lines[0].ml_total == 200
    assert not any(call[0] == "network" for call in client.calls)


def test_get_sales_order_maps_by_id():
    adapter = make_adapter()

    order = adapter.get_sales_order("40")

    assert order.reference == "S00040"


def test_missing_order_raises_object_not_found():
    adapter = make_adapter()

    with pytest.raises(ObjectNotFoundError):
        adapter.get_sales_order_by_reference("MISSING")


def test_list_supported_actions_is_read_only_surface():
    adapter = make_adapter()

    assert adapter.list_supported_actions() == [
        CanonicalAction.INSPECT_SALES_ORDER,
        CanonicalAction.VALIDATE_FORMULA,
        CanonicalAction.INSPECT_ACCESS_RULES,
    ]


def test_factory_returns_odoo_adapter_when_config_is_provided():
    adapter = get_adapter(
        ERPType.ODOO,
        config={
            "url": "https://example.odoo.com",
            "database": "demo",
            "username": "user@example.com",
            "api_key": "secret",
        },
    )

    assert isinstance(adapter, OdooAdapter)


def test_factory_requires_odoo_config():
    with pytest.raises(AdapterConfigurationError):
        get_adapter(ERPType.ODOO)
