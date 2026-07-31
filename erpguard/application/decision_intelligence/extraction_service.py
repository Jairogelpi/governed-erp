from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from erpguard.connectors.odoo.transports import OdooReadTransport
from erpguard.domain.decision_intelligence.types import (
    AnalyticalLine,
    CostEvidence,
    ExtractionDataset,
)


SOURCE_FIELDS: dict[str, list[str]] = {
    "account.move": [
        "id",
        "name",
        "move_type",
        "state",
        "invoice_date",
        "company_id",
        "currency_id",
        "partner_id",
        "amount_untaxed",
        "amount_total",
        "reversed_entry_id",
    ],
    "account.move.line": [
        "id",
        "move_id",
        "product_id",
        "quantity",
        "price_unit",
        "discount",
        "price_subtotal",
        "display_type",
    ],
    "sale.order": [
        "id",
        "name",
        "date_order",
        "state",
        "company_id",
        "currency_id",
        "partner_id",
        "amount_untaxed",
        "amount_total",
    ],
    "sale.order.line": [
        "id",
        "order_id",
        "product_id",
        "product_uom_qty",
        "price_unit",
        "discount",
        "price_subtotal",
    ],
    "product.product": ["id", "display_name", "default_code", "standard_price"],
    "res.partner": ["id", "display_name", "name"],
    "res.company": ["id", "display_name", "name", "currency_id"],
    "res.currency": ["id", "name", "symbol"],
    "stock.valuation.layer": [
        "id",
        "product_id",
        "company_id",
        "quantity",
        "unit_cost",
        "value",
        "create_date",
    ],
}

REQUIRED_FIELDS: dict[str, set[str]] = {
    "account.move": {
        "id",
        "move_type",
        "state",
        "invoice_date",
        "company_id",
        "currency_id",
        "partner_id",
    },
    "account.move.line": {
        "id",
        "move_id",
        "quantity",
        "price_unit",
        "price_subtotal",
    },
}


def _many2one(value: Any) -> tuple[int, str]:
    if isinstance(value, (list, tuple)) and value:
        return int(value[0]), str(value[1]) if len(value) > 1 else str(value[0])
    if isinstance(value, int):
        return value, str(value)
    return 0, ""


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


class OdooAnalyticalExtractor:
    """Bounded read-only extraction over the connector's read transport."""

    def __init__(self, transport: OdooReadTransport):
        self.transport = transport
        self.manifest: dict[str, Any] = {}

    def _fields(self, model: str) -> list[str]:
        discovered = self.transport.fields_get(model, ["type", "string"])
        requested = SOURCE_FIELDS[model]
        available = [field for field in requested if field in discovered]
        self.manifest[model] = {
            "requested_fields": requested,
            "available_fields": available,
            "missing_fields": sorted(set(requested) - set(available)),
        }
        return available

    def _read(
        self,
        model: str,
        domain: list,
        *,
        max_rows: int,
        required: bool = False,
    ) -> list[dict[str, Any]]:
        try:
            fields = self._fields(model)
            total = self.transport.search_count(model, domain)
            rows = self.transport.search_read(model, domain, fields, max_rows)
        except Exception as exc:
            if required:
                raise RuntimeError(f"required_analytical_source_unavailable:{model}") from exc
            self.manifest[model] = {
                "requested_fields": SOURCE_FIELDS[model],
                "available_fields": [],
                "missing_fields": SOURCE_FIELDS[model],
                "available": False,
                "error_type": type(exc).__name__,
                "source_row_count": 0,
                "retrieved_row_count": 0,
                "truncated": False,
                "read_only_method": "search_read",
            }
            return []
        self.manifest[model].update(
            {
                "available": True,
                "domain": domain,
                "source_row_count": total,
                "retrieved_row_count": len(rows),
                "truncated": total > len(rows),
                "read_only_method": "search_read",
            }
        )
        return rows

    def extract(
        self,
        *,
        company_ids: list[int],
        comparison_start: str,
        comparison_end: str,
        current_start: str,
        current_end: str,
        max_rows: int,
    ) -> ExtractionDataset:
        version = self.transport.version()
        uid = self.transport.authenticate()
        combined_start = min(comparison_start, current_start)
        combined_end = max(comparison_end, current_end)
        move_domain: list = [
            ["state", "=", "posted"],
            ["move_type", "in", ["out_invoice", "out_refund"]],
            ["invoice_date", ">=", combined_start],
            ["invoice_date", "<=", combined_end],
        ]
        if company_ids:
            move_domain.append(["company_id", "in", company_ids])
        moves = self._read(
            "account.move",
            move_domain,
            max_rows=max_rows,
            required=True,
        )
        move_ids = [int(row["id"]) for row in moves]
        lines = self._read(
            "account.move.line",
            [["move_id", "in", move_ids]],
            max_rows=max_rows,
            required=True,
        )

        sale_domain: list = [
            ["date_order", ">=", f"{combined_start} 00:00:00"],
            ["date_order", "<=", f"{combined_end} 23:59:59"],
        ]
        if company_ids:
            sale_domain.append(["company_id", "in", company_ids])
        sale_orders = self._read("sale.order", sale_domain, max_rows=max_rows)
        sale_order_ids = [int(row["id"]) for row in sale_orders]
        sale_lines = self._read(
            "sale.order.line",
            [["order_id", "in", sale_order_ids]],
            max_rows=max_rows,
        )

        product_ids = sorted(
            {
                _many2one(row.get("product_id"))[0]
                for row in [*lines, *sale_lines]
                if _many2one(row.get("product_id"))[0]
            }
        )
        partner_ids = sorted(
            {
                _many2one(row.get("partner_id"))[0]
                for row in [*moves, *sale_orders]
                if _many2one(row.get("partner_id"))[0]
            }
        )
        discovered_company_ids = sorted(
            {
                _many2one(row.get("company_id"))[0]
                for row in [*moves, *sale_orders]
                if _many2one(row.get("company_id"))[0]
            }
        )
        products = self._read(
            "product.product",
            [["id", "in", product_ids]],
            max_rows=max_rows,
        )
        partners = self._read(
            "res.partner",
            [["id", "in", partner_ids]],
            max_rows=max_rows,
        )
        companies = self._read(
            "res.company",
            [["id", "in", company_ids or discovered_company_ids]],
            max_rows=max_rows,
        )
        currency_ids = sorted(
            {
                _many2one(row.get("currency_id"))[0]
                for row in [*moves, *sale_orders, *companies]
                if _many2one(row.get("currency_id"))[0]
            }
        )
        currencies = self._read(
            "res.currency",
            [["id", "in", currency_ids]],
            max_rows=max_rows,
        )
        valuations = self._read(
            "stock.valuation.layer",
            [
                ["product_id", "in", product_ids],
                ["create_date", "<=", f"{combined_end} 23:59:59"],
                *([["company_id", "in", company_ids]] if company_ids else []),
            ],
            max_rows=max_rows,
        )

        product_by_id = {int(row["id"]): row for row in products}
        partner_by_id = {int(row["id"]): row for row in partners}
        currency_by_id = {int(row["id"]): row for row in currencies}
        move_by_id = {int(row["id"]): row for row in moves}
        valuations_by_company_product: dict[
            tuple[int, int],
            list[dict[str, Any]],
        ] = defaultdict(list)
        for row in valuations:
            product_id, _ = _many2one(row.get("product_id"))
            company_id, _ = _many2one(row.get("company_id"))
            valuations_by_company_product[(company_id, product_id)].append(row)
        for rows in valuations_by_company_product.values():
            rows.sort(key=lambda row: (str(row.get("create_date") or ""), int(row["id"])))

        extracted_at = datetime.now(timezone.utc).isoformat()
        analytical_lines: list[AnalyticalLine] = []
        for row in lines:
            if row.get("display_type") not in (None, False, "product"):
                continue
            move_id, _ = _many2one(row.get("move_id"))
            move = move_by_id.get(move_id)
            if move is None:
                continue
            product_id, product_label = _many2one(row.get("product_id"))
            partner_id, partner_label = _many2one(move.get("partner_id"))
            company_id, company_name = _many2one(move.get("company_id"))
            currency_id, currency_label = _many2one(move.get("currency_id"))
            product = product_by_id.get(product_id, {})
            partner = partner_by_id.get(partner_id, {})
            currency = currency_by_id.get(currency_id, {})
            invoice_date = str(move.get("invoice_date") or "")
            valuation = next(
                (
                    item
                    for item in reversed(
                        valuations_by_company_product.get(
                            (company_id, product_id),
                            [],
                        )
                    )
                    if str(item.get("create_date") or "")[:10] <= invoice_date
                ),
                None,
            )
            if valuation is not None:
                unit_cost = _decimal(valuation.get("unit_cost"))
                if not unit_cost and _decimal(valuation.get("quantity")):
                    unit_cost = abs(
                        _decimal(valuation.get("value")) / _decimal(valuation.get("quantity"))
                    )
                cost_evidence = CostEvidence(
                    source="stock_valuation_layer",
                    reliability="high",
                    unit_cost=abs(unit_cost),
                    as_of=str(valuation.get("create_date") or ""),
                )
            elif product and product.get("standard_price") is not None:
                cost_evidence = CostEvidence(
                    source="current_standard_price",
                    reliability="low",
                    unit_cost=abs(_decimal(product.get("standard_price"))),
                    as_of=extracted_at,
                    warning="Current standard price is not historical invoice-date cost.",
                )
            else:
                cost_evidence = CostEvidence(
                    source="missing",
                    reliability="none",
                    warning="No historical valuation or explicit fallback cost is available.",
                )
            move_type_value = str(move.get("move_type"))
            if move_type_value not in {"out_invoice", "out_refund"}:
                continue
            move_type: Literal["out_invoice", "out_refund"] = (
                "out_invoice" if move_type_value == "out_invoice" else "out_refund"
            )
            reversed_id, _ = _many2one(move.get("reversed_entry_id"))
            analytical_lines.append(
                AnalyticalLine(
                    invoice_line_id=int(row["id"]),
                    move_id=move_id,
                    move_type=move_type,
                    move_state=str(move.get("state") or ""),
                    invoice_date=invoice_date,
                    company_id=company_id,
                    company_name=company_name,
                    currency_id=currency_id,
                    currency=str(currency.get("name") or currency_label),
                    partner_id=partner_id,
                    partner_name=str(
                        partner.get("display_name") or partner.get("name") or partner_label
                    ),
                    product_id=product_id or None,
                    product_name=str(product.get("display_name") or product_label) or None,
                    quantity=_decimal(row.get("quantity")),
                    price_unit=_decimal(row.get("price_unit")),
                    discount_percent=_decimal(row.get("discount")),
                    price_subtotal=_decimal(row.get("price_subtotal")),
                    reversed_entry_id=reversed_id or None,
                    cost=cost_evidence,
                )
            )

        source_rows = {
            "account.move": moves,
            "account.move.line": lines,
            "sale.order": sale_orders,
            "sale.order.line": sale_lines,
            "product.product": products,
            "res.partner": partners,
            "res.company": companies,
            "res.currency": currencies,
            "stock.valuation.layer": valuations,
        }
        self.manifest["_extraction"] = {
            "connector": "odoo",
            "server_version": version.get("server_version", "unknown"),
            "authenticated_uid_recorded": bool(uid),
            "extracted_at": extracted_at,
            "combined_period_start": combined_start,
            "combined_period_end": combined_end,
            "maximum_rows_per_model": max_rows,
            "read_only": True,
            "write_methods": [],
        }
        row_counts = {model: int(self.manifest[model]["source_row_count"]) for model in source_rows}
        observed_currencies = sorted({line.currency for line in analytical_lines if line.currency})
        return ExtractionDataset(
            lines=analytical_lines,
            source_rows=source_rows,
            manifest=self.manifest,
            row_counts=row_counts,
            currency=observed_currencies[0] if len(observed_currencies) == 1 else None,
        )
