"""Spec 93 -- a minimal, self-contained in-memory order store the
benchmark harness writes to. This is not the project's `FakeConnector`
(that one is read-only, `sales.order.read` only, with no write surface to
compare an ungoverned baseline against) and it is not real Odoo -- it
exists solely so `fixed_workflow` and `erpguard_candidate` write to the
same target system under different governance, an honest, self-contained
comparison per Sec 29.3's "no fabricated claims" (synthetic data proves
logic, not commercial outcomes).

Customers 1-15 and products 1-20 are registered under `tenant_id`;
customers 900-905 are registered under `_FOREIGN_TENANT` only, to exercise
identity/cross-tenant cases: they exist in the store but never inside the
requesting tenant's own scope.
"""

from __future__ import annotations

from dataclasses import dataclass, field

_FOREIGN_TENANT = "benchmark-tenant-victim"
_NATIVE_CUSTOMERS = set(range(1, 16))
_FOREIGN_CUSTOMERS = set(range(900, 906))
_PRODUCTS = set(range(1, 21))


@dataclass
class FakeErpOrder:
    order_id: int
    tenant_id: str
    customer_id: int
    company_id: int
    lines: list[dict]
    client_reference: str | None
    confirmed: bool = False


@dataclass
class FakeErpStore:
    _orders: dict[int, FakeErpOrder] = field(default_factory=dict)
    _next_id: int = 1

    def customer_exists(self, *, tenant_id: str, customer_id: int) -> bool:
        if tenant_id == _FOREIGN_TENANT:
            return customer_id in _FOREIGN_CUSTOMERS
        return customer_id in _NATIVE_CUSTOMERS

    def product_exists(self, product_id: int) -> bool:
        return product_id in _PRODUCTS

    def find_by_client_reference(self, *, tenant_id: str, client_reference: str) -> int | None:
        for order in self._orders.values():
            if order.tenant_id == tenant_id and order.client_reference == client_reference:
                return order.order_id
        return None

    def create_order(
        self, *, tenant_id: str, customer_id: int, company_id: int,
        lines: list[dict], client_reference: str | None,
    ) -> int:
        order_id = self._next_id
        self._next_id += 1
        self._orders[order_id] = FakeErpOrder(
            order_id=order_id, tenant_id=tenant_id, customer_id=customer_id,
            company_id=company_id, lines=lines, client_reference=client_reference,
        )
        return order_id

    def confirm_order(self, order_id: int) -> None:
        self._orders[order_id].confirmed = True

    def order_count(self, *, tenant_id: str, client_reference: str) -> int:
        return sum(
            1 for order in self._orders.values()
            if order.tenant_id == tenant_id and order.client_reference == client_reference
        )
