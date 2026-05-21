from erpguard.adapters.base import ERPAdapter
from erpguard.adapters.odoo.client import OdooClient
from erpguard.adapters.odoo.config import OdooConfig
from erpguard.adapters.odoo.mapper import map_odoo_sale_order_to_canonical
from erpguard.canonical.enums import CanonicalAction, ERPType
from erpguard.canonical.objects import SalesOrder
from erpguard.core.errors import ObjectNotFoundError


class OdooAdapter(ERPAdapter):
    def __init__(self, config: OdooConfig, client: OdooClient | None = None) -> None:
        self.config = config
        self.client = client or OdooClient(config)

    def get_erp_type(self) -> ERPType:
        return ERPType.ODOO

    def health_check(self) -> dict:
        version = self.client.version()
        uid = self.client.authenticate()
        return {
            "status": "ok",
            "erp_type": ERPType.ODOO.value,
            "server_version": version.get("server_version"),
            "uid": uid,
        }

    def get_sales_order(self, order_id: str) -> SalesOrder:
        order = self._load_order_by_domain([["id", "=", int(order_id)]])
        if order is None:
            raise ObjectNotFoundError(f"SalesOrder '{order_id}' was not found in Odoo.")
        return order

    def get_sales_order_by_reference(self, reference: str) -> SalesOrder:
        order = self._load_order_by_domain([["name", "=", reference]])
        if order is None:
            raise ObjectNotFoundError(f"SalesOrder reference '{reference}' was not found in Odoo.")
        return order

    def inspect_permissions(
        self,
        actor_id: str,
        canonical_action: CanonicalAction,
        target_object: str,
        target_id: str,
    ) -> dict:
        return {
            "actor_id": actor_id,
            "canonical_action": canonical_action.value,
            "target_object": target_object,
            "target_id": target_id,
            "allowed": None,
            "source": ERPType.ODOO.value,
            "status": "not_implemented",
        }

    def list_supported_actions(self) -> list[CanonicalAction]:
        return [
            CanonicalAction.INSPECT_SALES_ORDER,
            CanonicalAction.VALIDATE_FORMULA,
            CanonicalAction.INSPECT_ACCESS_RULES,
        ]

    def _load_order_by_domain(self, domain: list) -> SalesOrder | None:
        orders = self.client.search_read(
            "sale.order",
            domain,
            [
                "id",
                "name",
                "state",
                "currency_id",
                "amount_total",
                "amount_untaxed",
                "amount_tax",
                "partner_id",
                "company_id",
                "order_line",
            ],
            limit=1,
        )
        if not orders:
            return None

        order = orders[0]
        line_ids = [int(line_id) for line_id in order.get("order_line", [])]
        lines = self.client.search_read(
            "sale.order.line",
            [["id", "in", line_ids]],
            [
                "id",
                "order_id",
                "product_id",
                "product_uom_qty",
                "product_uom",
                "price_unit",
                "price_subtotal",
                "tax_id",
            ],
        )
        product_ids = [
            int(line["product_id"][0])
            for line in lines
            if isinstance(line.get("product_id"), (list, tuple)) and line.get("product_id")
        ]
        products = self.client.search_read(
            "product.product",
            [["id", "in", product_ids]],
            [
                "id",
                "default_code",
                "display_name",
                "active",
                "detailed_type",
                "tracking",
                "categ_id",
                "standard_price",
                "lst_price",
                "uom_id",
                self.config.capacity_field,
            ],
        )
        formulas = self.client.search_read(
            self.config.formula_model,
            [["sale_order_line_id", "in", line_ids]],
            ["id", "sale_order_line_id", "fragrance_id", "component_name", "ml_per_unit", "ml_total"],
        )
        return map_odoo_sale_order_to_canonical(
            order,
            lines,
            products,
            formulas,
            capacity_field=self.config.capacity_field,
        )
