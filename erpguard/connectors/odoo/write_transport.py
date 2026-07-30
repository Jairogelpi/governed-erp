"""SDK-facing bounded write wrapper for Odoo Phases 16 and 17.

It exposes draft creation and governed order confirmation helpers, never a
generic model/method RPC.
"""

from __future__ import annotations

from typing import Any, Protocol

from erpguard.adapters.odoo.write_client import OdooQuoteDraftClient


class OdooWriteTransport(Protocol):
    def find_by_client_reference(self, client_reference: str) -> int | None: ...

    def create_draft(self, *, partner_id: int, lines: list[dict[str, Any]], client_reference: str) -> int: ...

    def read_order(self, order_id: int) -> dict[str, Any]: ...

    def read_confirmation_snapshot(self, order_id: int) -> dict[str, Any]: ...

    def read_confirmation_automation_fingerprint(self, order_id: int) -> dict[str, Any]: ...

    def confirm_order(self, order_id: int) -> None: ...


class LegacyXmlRpcWriteTransport:
    """SDK transport adapter around `OdooQuoteDraftClient`."""

    def __init__(self, client: OdooQuoteDraftClient):
        self._client = client

    def find_by_client_reference(self, client_reference: str) -> int | None:
        return self._client.find_by_client_reference(client_reference)

    def create_draft(self, *, partner_id: int, lines: list[dict[str, Any]], client_reference: str) -> int:
        return self._client.create_draft(partner_id=partner_id, lines=lines, client_reference=client_reference)

    def read_order(self, order_id: int) -> dict[str, Any]:
        return self._client.read_order(order_id)

    def read_confirmation_snapshot(self, order_id: int) -> dict[str, Any]:
        return self._client.read_confirmation_snapshot(order_id)

    def read_confirmation_automation_fingerprint(self, order_id: int) -> dict[str, Any]:
        return self._client.read_confirmation_automation_fingerprint(order_id)

    def confirm_order(self, order_id: int) -> None:
        self._client.confirm_order(order_id)
