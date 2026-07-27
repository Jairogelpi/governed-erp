from __future__ import annotations

from uuid import uuid5, NAMESPACE_URL


def build_fake_ocel(*, tenant_id: str) -> dict:
    seed = uuid5(NAMESPACE_URL, f"erpguard.fake:{tenant_id}").hex[:10]
    return {
        "ocel:global-event": {"ocel:activity": "erpguard.fake", "ocel:version": "2.0"},
        "ocel:objects": {
            f"fake-order-{seed}": {"ocel:type": "sale_order", "ocel:ovmap": {"name": "SO-FAKE"}},
            f"fake-customer-{seed}": {"ocel:type": "customer", "ocel:ovmap": {"name": "Fake Customer"}},
        },
        "ocel:events": {
            f"fake-created-{seed}": {
                "ocel:activity": "sales.order.created", "ocel:timestamp": "2026-01-01T00:00:00Z",
                "ocel:omap": [f"fake-order-{seed}", f"fake-customer-{seed}"], "ocel:vmap": {},
            },
            f"fake-reviewed-{seed}": {
                "ocel:activity": "sales.order.reviewed", "ocel:timestamp": "2026-01-01T00:01:00Z",
                "ocel:omap": [f"fake-order-{seed}"], "ocel:vmap": {},
            },
        },
    }
