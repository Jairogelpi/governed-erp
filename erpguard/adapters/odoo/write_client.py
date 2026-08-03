"""Narrowly-scoped Odoo write client for the governed sales capabilities.

Phase 16 introduced draft quotation creation. Phase 17 adds exactly one R3
method, ``sale.order.action_confirm``, plus read-only snapshot helpers.
User-declared write capabilities (`erpguard/domain/declared_capabilities/`)
add exactly one more primitive, `write_field`/`read_field` -- a single
`(model, record_id, field, value)` write, re-checked against the same
denylist the declaration itself was checked against at declare-time, so
a bug anywhere upstream still can't turn this into a generic write. This
is still not a generic RPC transport: no `create`, no `unlink`, no method
other than `write`/`read` on a single record, no arbitrary method name.
"""

from __future__ import annotations

from typing import Any, cast

from erpguard.adapters.odoo.client import OdooClient
from erpguard.adapters.odoo.config import OdooConfig
from erpguard.domain.declared_capabilities.denylist import is_denylisted

_SALE_ORDER_MODEL = "sale.order"
_EFFECT_MODELS = ("stock.picking", "account.move", "account.payment", "purchase.order", "mrp.production")


class OdooQuoteDraftClient:
    """Wraps ``OdooClient`` with the bounded Phase 16/17 calls."""

    def __init__(self, config: OdooConfig) -> None:
        self._client = OdooClient(config)

    def find_by_client_reference(self, client_reference: str) -> int | None:
        rows = self._client.search_read(
            _SALE_ORDER_MODEL, [["client_order_ref", "=", client_reference]], ["id"], limit=1
        )
        return int(rows[0]["id"]) if rows else None

    def create_draft(
        self,
        *,
        partner_id: int,
        lines: list[dict[str, Any]],
        client_reference: str,
        company_id: int | None = None,
        pricelist_id: int | None = None,
    ) -> int:
        """Creates exactly one `sale.order` in its default (draft) state.
        Never calls `action_confirm` or any invoicing/picking method."""

        order_lines = []
        for line in lines:
            values: dict[str, Any] = {
                "product_id": int(line["product_id"]),
                "product_uom_qty": line.get("quantity", 1),
            }
            if "price_unit" in line:
                # Only set when a governed recommendation supplies a proposed
                # price (Spec 92 Workstream A); otherwise Odoo's own
                # pricelist pricing applies, same as before.
                values["price_unit"] = line["price_unit"]
            order_lines.append((0, 0, values))
        values_order: dict[str, Any] = {
            "partner_id": partner_id,
            "client_order_ref": client_reference,
            "order_line": order_lines,
        }
        if company_id is not None:
            values_order["company_id"] = company_id
        if pricelist_id is not None:
            values_order["pricelist_id"] = pricelist_id
        order_id = self._client._execute_kw(  # noqa: SLF001 -- intentional, single narrow call site
            _SALE_ORDER_MODEL,
            "create",
            [values_order],
            {},
        )
        return int(cast(int, order_id))

    def read_partner(self, partner_id: int) -> dict[str, Any]:
        """Bounded read used by the pricing-scenario preflight (Spec 92 Sec
        8.3) to confirm the customer exists and is active."""

        rows = self._client.read("res.partner", [partner_id], ["id", "active"])
        if not rows:
            raise LookupError(f"partner_not_found:{partner_id}")
        return {"id": int(rows[0]["id"]), "active": bool(rows[0].get("active", True))}

    def read_products(self, product_ids: list[int]) -> list[dict[str, Any]]:
        """Bounded read used by the pricing-scenario preflight to confirm
        every product exists, is active/saleable, and carries no forbidden
        marker in its name."""

        if not product_ids:
            return []
        rows = self._client.read("product.product", product_ids, ["id", "active", "sale_ok", "name"])
        return [
            {
                "id": int(row["id"]),
                "active": bool(row.get("active", True)),
                "sale_ok": bool(row.get("sale_ok", True)),
                "name": str(row.get("name") or ""),
            }
            for row in rows
        ]

    def read_pricing_scenario_snapshot(self, order_id: int) -> dict[str, Any]:
        """Postcondition read for `sales.quote.create_pricing_scenario_draft`
        (Spec 92 Sec 8.5) -- narrower than `read_confirmation_snapshot`
        (no automation-fingerprint fields needed for a draft-only write)."""

        fields = [
            "id", "name", "state", "partner_id", "company_id", "currency_id",
            "pricelist_id", "amount_total", "client_order_ref", "order_line",
            "picking_ids", "invoice_ids",
        ]
        rows = self._client.read(_SALE_ORDER_MODEL, [order_id], fields)
        if not rows:
            raise LookupError(f"sale_order_not_found:{order_id}")
        order = rows[0]

        line_ids = [int(value) for value in order.get("order_line", [])]
        line_rows = (
            self._client.read("sale.order.line", line_ids, ["id", "product_id", "product_uom_qty", "price_unit"])
            if line_ids
            else []
        )
        lines = [
            {
                "product_id": self._relation_id(line.get("product_id")),
                "quantity": float(line.get("product_uom_qty") or 0),
                "price_unit": float(line.get("price_unit") or 0),
            }
            for line in sorted(line_rows, key=lambda item: int(item["id"]))
        ]

        purchase_orders = self._client.search_read(
            "purchase.order", [["origin", "=", str(order.get("name") or "")]], ["id"], limit=1
        )
        manufacturing_orders = self._client.search_read(
            "mrp.production", [["origin", "=", str(order.get("name") or "")]], ["id"], limit=1
        )

        return {
            "order_id": int(order["id"]),
            "state": str(order.get("state") or ""),
            "partner_id": self._relation_id(order.get("partner_id")),
            "company_id": self._relation_id(order.get("company_id")),
            "currency_id": self._relation_id(order.get("currency_id")),
            "pricelist_id": self._relation_id(order.get("pricelist_id")),
            "amount_total": float(order.get("amount_total") or 0),
            "client_reference": str(order.get("client_order_ref") or ""),
            "lines": lines,
            "invoice_count": len(order.get("invoice_ids") or []),
            "picking_count": len(order.get("picking_ids") or []),
            "purchase_order_count": len(purchase_orders),
            "manufacturing_order_count": len(manufacturing_orders),
        }

    def read_order(self, order_id: int) -> dict[str, Any]:
        rows = self._client.read(_SALE_ORDER_MODEL, [order_id], ["id", "name", "state", "partner_id", "client_order_ref"])
        if not rows:
            raise LookupError(f"sale_order_not_found:{order_id}")
        return rows[0]

    @staticmethod
    def _relation_id(value: Any) -> int | None:
        if isinstance(value, (list, tuple)) and value:
            return int(value[0])
        if isinstance(value, int):
            return value
        return None

    def read_confirmation_snapshot(self, order_id: int) -> dict[str, Any]:
        """Read the critical state used to bind an R3 approval."""

        fields = [
            "id",
            "name",
            "state",
            "partner_id",
            "company_id",
            "currency_id",
            "amount_total",
            "client_order_ref",
            "write_date",
            "order_line",
            "picking_ids",
            "invoice_ids",
        ]
        rows = self._client.read(_SALE_ORDER_MODEL, [order_id], fields)
        if not rows:
            raise LookupError(f"sale_order_not_found:{order_id}")
        order = rows[0]

        line_ids = [int(value) for value in order.get("order_line", [])]
        line_rows = (
            self._client.read(
                "sale.order.line",
                line_ids,
                ["id", "product_id", "product_uom_qty", "price_unit", "price_subtotal", "write_date"],
            )
            if line_ids
            else []
        )
        lines = [
            {
                "id": int(line["id"]),
                "product_id": self._relation_id(line.get("product_id")),
                "product_name": (
                    str(line["product_id"][1])
                    if isinstance(line.get("product_id"), (list, tuple)) and len(line["product_id"]) > 1
                    else ""
                ),
                "quantity": float(line.get("product_uom_qty") or 0),
                "price_unit": float(line.get("price_unit") or 0),
                "price_subtotal": float(line.get("price_subtotal") or 0),
                "write_date": line.get("write_date"),
            }
            for line in sorted(line_rows, key=lambda item: int(item["id"]))
        ]

        for line in lines:
            product_id = line.get("product_id")
            line["invoice_policy"] = None
            if product_id is not None:
                try:
                    products = self._client.read("product.product", [int(product_id)], ["invoice_policy"])
                    if products:
                        line["invoice_policy"] = products[0].get("invoice_policy")
                except Exception:  # model/field availability is recorded by the fingerprint gate
                    pass

        picking_ids = [int(value) for value in order.get("picking_ids", [])]
        picking_rows = (
            self._client.read("stock.picking", picking_ids, ["id", "name", "state", "write_date"])
            if picking_ids
            else []
        )
        pickings = [
            {
                "id": int(row["id"]),
                "name": str(row.get("name") or ""),
                "state": str(row.get("state") or ""),
                "write_date": row.get("write_date"),
            }
            for row in sorted(picking_rows, key=lambda item: int(item["id"]))
        ]

        invoice_ids = [int(value) for value in order.get("invoice_ids", [])]
        invoice_rows = (
            self._client.read("account.move", invoice_ids, ["id", "name", "state", "move_type", "write_date"])
            if invoice_ids
            else []
        )
        invoices = [
            {
                "id": int(row["id"]),
                "name": str(row.get("name") or ""),
                "state": str(row.get("state") or ""),
                "move_type": str(row.get("move_type") or ""),
                "write_date": row.get("write_date"),
            }
            for row in sorted(invoice_rows, key=lambda item: int(item["id"]))
        ]

        related: dict[str, list[dict[str, Any]]] = {
            "payments": [],
            "purchase_orders": [],
            "manufacturing_orders": [],
        }
        observation_issues: list[str] = []
        for model, key, domain in (
            ("account.payment", "payments", [["ref", "ilike", str(order.get("name") or "")]]),
            ("purchase.order", "purchase_orders", [["origin", "=", str(order.get("name") or "")]]),
            ("mrp.production", "manufacturing_orders", [["origin", "=", str(order.get("name") or "")]]),
        ):
            try:
                records = self._client.search_read(model, domain, ["id", "state", "write_date"], limit=20)
                related[key] = [
                    {
                        "id": int(record["id"]),
                        "state": str(record.get("state") or ""),
                        "write_date": record.get("write_date"),
                    }
                    for record in sorted(records, key=lambda item: int(item["id"]))
                ]
            except Exception:
                observation_issues.append(f"effect_model_unobservable:{model}")

        return {
            "order_id": int(order["id"]),
            "name": str(order.get("name") or ""),
            "state": str(order.get("state") or ""),
            "partner_id": self._relation_id(order.get("partner_id")),
            "company_id": self._relation_id(order.get("company_id")),
            "currency_id": self._relation_id(order.get("currency_id")),
            "amount_total": float(order.get("amount_total") or 0),
            "client_reference": str(order.get("client_order_ref") or ""),
            "write_date": order.get("write_date"),
            "lines": lines,
            "pickings": pickings,
            "invoices": invoices,
            **related,
            "effect_observation_issues": observation_issues,
        }

    def read_confirmation_automation_fingerprint(self, order_id: int) -> dict[str, Any]:
        """Inspect only bounded, confirmation-relevant automation signals."""

        snapshot = self.read_confirmation_snapshot(order_id)
        blocking_issues = list(snapshot.get("effect_observation_issues", []))
        model_access: dict[str, dict[str, bool]] = {}
        for model in (_SALE_ORDER_MODEL, *_EFFECT_MODELS):
            permissions: dict[str, bool] = {}
            for operation in ("read", "write"):
                try:
                    permissions[operation] = bool(
                        self._client._execute_kw(  # noqa: SLF001 -- bounded permission inspection
                            model,
                            "check_access_rights",
                            [operation],
                            {"raise_exception": False},
                        )
                    )
                except Exception:
                    permissions[operation] = False
                    blocking_issues.append(f"permission_unobservable:{model}:{operation}")
            model_access[model] = permissions

        installed_modules: list[str] = []
        try:
            modules = self._client.search_read(
                "ir.module.module",
                [
                    ["name", "in", ["sale", "sale_management", "sale_stock", "stock", "account", "purchase", "mrp"]],
                    ["state", "=", "installed"],
                ],
                ["name"],
                limit=20,
            )
            installed_modules = sorted(str(item["name"]) for item in modules)
        except Exception:
            blocking_issues.append("installed_modules_unobservable")

        custom_fields: list[str] = []
        try:
            field_definitions = self._client._execute_kw(  # noqa: SLF001 -- bounded schema inspection
                _SALE_ORDER_MODEL,
                "fields_get",
                [],
                {"attributes": ["manual", "modules"]},
            )
            core_modules = {"base", "sale", "sale_management", "sale_stock", "stock", "account"}
            for name, definition in field_definitions.items():
                modules_value = str(definition.get("modules") or "")
                field_modules = {part.strip() for part in modules_value.split(",") if part.strip()}
                if definition.get("manual") or name.startswith(("x_", "studio_")) or (
                    field_modules and field_modules.isdisjoint(core_modules)
                ):
                    custom_fields.append(str(name))
        except Exception:
            blocking_issues.append("sale_order_custom_fields_unobservable")

        automated_action_count = 0
        try:
            model_rows = self._client.search_read(
                "ir.model",
                [["model", "=", _SALE_ORDER_MODEL]],
                ["id"],
                limit=1,
            )
            if not model_rows:
                raise LookupError("sale_order_model_metadata_missing")
            automated_action_count = int(
                self._client._execute_kw(  # noqa: SLF001 -- bounded automation count
                    "base.automation",
                    "search_count",
                    [[["model_id", "=", int(model_rows[0]["id"])], ["active", "=", True]]],
                    {},
                )
            )
        except Exception:
            blocking_issues.append("automated_actions_unobservable")

        route_ids: list[int] = []
        try:
            line_fields = self._client._execute_kw(  # noqa: SLF001 -- bounded route schema inspection
                "sale.order.line",
                "fields_get",
                [],
                {"attributes": ["type"]},
            )
            if "route_id" in line_fields:
                line_ids = [int(line["id"]) for line in snapshot.get("lines", [])]
                route_rows = (
                    self._client.read("sale.order.line", line_ids, ["route_id"])
                    if line_ids
                    else []
                )
                route_ids = sorted(
                    {
                        int(route[0])
                        for row in route_rows
                        if isinstance((route := row.get("route_id")), (list, tuple)) and route
                    }
                )
        except Exception:
            blocking_issues.append("logistics_routes_unobservable")

        invoice_policies = sorted(
            {
                str(line["invoice_policy"])
                for line in snapshot.get("lines", [])
                if line.get("invoice_policy")
            }
        )
        return {
            "server_version": str(self._client.version().get("server_version") or "unknown"),
            "installed_modules": installed_modules,
            "automated_action_count": automated_action_count,
            "custom_sale_order_fields": sorted(set(custom_fields)),
            "model_access": model_access,
            "configuration_signals": {
                "line_invoice_policies": invoice_policies,
                "explicit_route_ids": route_ids,
                "effect_models_observable": not snapshot.get("effect_observation_issues"),
            },
            "blocking_issues": sorted(set(blocking_issues)),
        }

    def confirm_order(self, order_id: int) -> None:
        """Invoke only ``sale.order.action_confirm`` for one known record."""

        self._client._execute_kw(  # noqa: SLF001 -- intentional bounded bridge
            _SALE_ORDER_MODEL,
            "action_confirm",
            [[int(order_id)]],
            {},
        )

    def write_field(self, *, model: str, record_id: int, field: str, value: Any) -> None:
        """Write exactly one field on exactly one existing record.

        Re-checks the denylist here, independently of whatever check ran
        before this was called -- the last line of defense before the
        actual RPC, not the only one."""

        if is_denylisted(model=model, field=field):
            raise ValueError(f"denylisted_write_target:{model}.{field}")
        self._client._execute_kw(  # noqa: SLF001 -- intentional bounded bridge
            model,
            "write",
            [[int(record_id)], {field: value}],
            {},
        )

    def read_field(self, *, model: str, record_id: int, field: str) -> Any:
        rows = self._client.read(model, [int(record_id)], [field])
        if not rows:
            raise LookupError(f"record_not_found:{model}:{record_id}")
        return rows[0].get(field)
