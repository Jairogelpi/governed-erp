"""Narrowly-scoped Odoo write client: exactly one atomic bridge method,
`sales.quote.create_draft` (master spec Phase 16). This is not a generic
write RPC -- unlike `OdooClient`'s `_execute_kw` (used only for reads by
every existing caller), this client exposes only the three operations the
draft-quotation bridge needs: idempotent lookup, draft creation, and a
postcondition read-back. It never calls `action_confirm`, invoicing, or
picking methods.
"""

from __future__ import annotations

from typing import Any, cast

from erpguard.adapters.odoo.client import OdooClient
from erpguard.adapters.odoo.config import OdooConfig

_SALE_ORDER_MODEL = "sale.order"


class OdooQuoteDraftClient:
    """Wraps `OdooClient` with exactly the calls Phase 16 needs."""

    def __init__(self, config: OdooConfig) -> None:
        self._client = OdooClient(config)

    def find_by_client_reference(self, client_reference: str) -> int | None:
        rows = self._client.search_read(
            _SALE_ORDER_MODEL, [["client_order_ref", "=", client_reference]], ["id"], limit=1
        )
        return int(rows[0]["id"]) if rows else None

    def create_draft(self, *, partner_id: int, lines: list[dict[str, Any]], client_reference: str) -> int:
        """Creates exactly one `sale.order` in its default (draft) state.
        Never calls `action_confirm` or any invoicing/picking method."""

        order_lines = [
            (
                0,
                0,
                {
                    "product_id": int(line["product_id"]),
                    "product_uom_qty": line.get("quantity", 1),
                },
            )
            for line in lines
        ]
        order_id = self._client._execute_kw(  # noqa: SLF001 -- intentional, single narrow call site
            _SALE_ORDER_MODEL,
            "create",
            [
                {
                    "partner_id": partner_id,
                    "client_order_ref": client_reference,
                    "order_line": order_lines,
                }
            ],
            {},
        )
        return int(cast(int, order_id))

    def read_order(self, order_id: int) -> dict[str, Any]:
        rows = self._client.read(_SALE_ORDER_MODEL, [order_id], ["id", "name", "state", "partner_id", "client_order_ref"])
        if not rows:
            raise LookupError(f"sale_order_not_found:{order_id}")
        return rows[0]
