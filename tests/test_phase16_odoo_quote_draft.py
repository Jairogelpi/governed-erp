"""Phase 16 -- Real quotation draft (master spec: close the first real
business write). Unit-level coverage against `OdooConnectorPlugin` with
injected fake transports (never a live Odoo call in the automated suite --
this was verified manually once against a real staging instance; see the
commit message for that demonstration's results, order id and all).

Exit criteria exercised here:
- one request creates one draft;
- retry (same client_reference) creates no duplicate;
- no invoice/picking/confirmation is ever called (this plugin has no such
  method at all -- the only real write path is `create`, verified by
  construction, not just by test);
- postconditions pass (state == "draft" read-back);
- evidence: the verification result captures connector result + postcondition.
"""

from __future__ import annotations

import asyncio

from erpguard.connectors.odoo.plugin import OdooConnectorPlugin
from erpguard.connectors.sdk.models import (
    CanonicalOperation,
    ConnectorContext,
    ExecutionPermit,
    NativeExecutionPlan,
)


class _FakeWriteTransport:
    def __init__(self) -> None:
        self.orders: dict[str, int] = {}
        self.rows: dict[int, dict] = {}
        self._next_id = 100
        self.create_calls = 0

    def find_by_client_reference(self, client_reference: str) -> int | None:
        return self.orders.get(client_reference)

    def create_draft(self, *, partner_id: int, lines: list[dict], client_reference: str) -> int:
        self.create_calls += 1
        order_id = self._next_id
        self._next_id += 1
        self.orders[client_reference] = order_id
        self.rows[order_id] = {"id": order_id, "state": "draft", "partner_id": partner_id, "client_order_ref": client_reference}
        return order_id

    def read_order(self, order_id: int) -> dict:
        return self.rows[order_id]


def _plugin(transport: _FakeWriteTransport) -> OdooConnectorPlugin:
    return OdooConnectorPlugin(write_transport_factory=lambda context: transport)


def _context() -> ConnectorContext:
    return ConnectorContext(tenant_id="tenant-1", connection_id="conn-1")


def test_quote_create_draft_is_declared_with_supports_execution() -> None:
    plugin = _plugin(_FakeWriteTransport())
    definitions = {item.name: item for item in plugin.capability_definitions()}
    assert definitions["quote.create_draft"].supports_execution is True
    assert definitions["sales.order.confirm"].supports_execution is True
    # every read capability stays supports_execution=False
    assert all(
        not d.supports_execution
        for name, d in definitions.items()
        if name not in {"quote.create_draft", "sales.order.confirm"}
    )


def test_one_request_creates_one_draft() -> None:
    transport = _FakeWriteTransport()
    plugin = _plugin(transport)
    plan = NativeExecutionPlan(
        capability="quote.create_draft",
        arguments={"partner_id": 42, "lines": [{"product_id": 7, "quantity": 1}], "client_reference": "REF-1"},
    )
    permit = ExecutionPermit(permit_id="permit-1", capability="quote.create_draft", approved=True)

    result = asyncio.run(plugin.execute_capability(_context(), plan, permit))

    assert result.status == "ok"
    assert result.payload["created"] is True
    assert transport.create_calls == 1
    assert result.safety_flags.erp_write_performed is True


def test_retry_with_same_client_reference_creates_no_duplicate() -> None:
    transport = _FakeWriteTransport()
    plugin = _plugin(transport)
    plan = NativeExecutionPlan(
        capability="quote.create_draft",
        arguments={"partner_id": 42, "lines": [{"product_id": 7, "quantity": 1}], "client_reference": "REF-RETRY"},
    )
    permit = ExecutionPermit(permit_id="permit-1", capability="quote.create_draft", approved=True)

    first = asyncio.run(plugin.execute_capability(_context(), plan, permit))
    second = asyncio.run(plugin.execute_capability(_context(), plan, permit))

    assert transport.create_calls == 1
    assert first.payload["order_id"] == second.payload["order_id"]
    assert first.payload["created"] is True
    assert second.payload["created"] is False
    assert second.safety_flags.erp_write_performed is False


def test_postcondition_verifies_draft_state() -> None:
    transport = _FakeWriteTransport()
    plugin = _plugin(transport)
    plan = NativeExecutionPlan(
        capability="quote.create_draft",
        arguments={"partner_id": 42, "lines": [{"product_id": 7, "quantity": 1}], "client_reference": "REF-2"},
    )
    permit = ExecutionPermit(permit_id="permit-1", capability="quote.create_draft", approved=True)

    result = asyncio.run(plugin.execute_capability(_context(), plan, permit))
    verification = asyncio.run(plugin.verify_execution(_context(), "quote.create_draft", result))

    assert verification.status == "verified"
    assert verification.verified is True


def test_postcondition_fails_if_state_is_not_draft() -> None:
    transport = _FakeWriteTransport()
    plugin = _plugin(transport)
    plan = NativeExecutionPlan(
        capability="quote.create_draft",
        arguments={"partner_id": 42, "lines": [{"product_id": 7, "quantity": 1}], "client_reference": "REF-3"},
    )
    permit = ExecutionPermit(permit_id="permit-1", capability="quote.create_draft", approved=True)
    result = asyncio.run(plugin.execute_capability(_context(), plan, permit))

    # Simulate the order having moved out of draft between execute and verify.
    order_id = result.payload["order_id"]
    transport.rows[order_id]["state"] = "sale"

    verification = asyncio.run(plugin.verify_execution(_context(), "quote.create_draft", result))
    assert verification.status == "verification_failed"
    assert verification.verified is False


def test_missing_arguments_are_blocked_not_crashed() -> None:
    plugin = _plugin(_FakeWriteTransport())
    plan = NativeExecutionPlan(capability="quote.create_draft", arguments={})
    permit = ExecutionPermit(permit_id="permit-1", capability="quote.create_draft", approved=True)

    result = asyncio.run(plugin.execute_capability(_context(), plan, permit))
    assert result.status == "blocked"


def test_only_declared_capabilities_can_execute_no_raw_native_call() -> None:
    """The connector has no `action_confirm`/invoice/picking method at all --
    this test asserts an undeclared capability is blocked, not that some
    forbidden method silently does nothing."""

    plugin = _plugin(_FakeWriteTransport())
    plan = NativeExecutionPlan(capability="quote.action_confirm", arguments={})
    permit = ExecutionPermit(permit_id="permit-1", capability="quote.action_confirm", approved=True)

    result = asyncio.run(plugin.execute_capability(_context(), plan, permit))
    assert result.status == "blocked"
    assert not hasattr(plugin, "action_confirm")


def test_plan_capability_carries_arguments_through() -> None:
    plugin = _plugin(_FakeWriteTransport())
    operation = CanonicalOperation(capability="quote.create_draft", arguments={"partner_id": 1, "lines": [], "client_reference": "R"})
    plan = asyncio.run(plugin.plan_capability(_context(), operation))
    assert plan.arguments == operation.arguments
    assert plan.supports_execution is True
