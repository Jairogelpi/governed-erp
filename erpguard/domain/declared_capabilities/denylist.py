"""Hard denylist for user-declared field-write capabilities.

Deliberately hardcoded, not user-configurable -- this is the actual
safety boundary, not a preference. No `DeclaredWriteCapability` may ever
target these models/fields, regardless of who approves it.
"""

from __future__ import annotations

# Whole-model denylist: security/identity/config models, and any model
# already covered by an existing named capability (so a declared
# capability can never re-implement a write path that already has
# bespoke side-effect verification -- sale.order writes stay exclusive
# to quote.create_draft/sales.order.confirm).
DENYLISTED_MODEL_PREFIXES: tuple[str, ...] = (
    "res.users",
    "res.groups",
    "res.company",
    "ir.",
    "auth.",
    "sale.order",
)

# Field-level denylist: (model, field) pairs that would otherwise pass
# the prefix check but are still too dangerous to expose (posted-entry
# immutability, accounting state).
DENYLISTED_FIELDS: frozenset[tuple[str, str]] = frozenset(
    {
        ("account.move", "state"),
        ("account.move", "amount_total"),
        ("account.payment", "state"),
        ("stock.picking", "state"),
    }
)


def is_denylisted(*, model: str, field: str) -> bool:
    if any(model == prefix or model.startswith(prefix) for prefix in DENYLISTED_MODEL_PREFIXES):
        return True
    return (model, field) in DENYLISTED_FIELDS
