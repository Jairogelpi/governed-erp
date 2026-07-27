from __future__ import annotations

import asyncio

from erpguard.connectors.sdk.legacy_adapter_shim import LegacyAdapterShim
from erpguard.connectors.sdk.models import ConnectorContext


def test_legacy_shim_allows_read_like_operation_only():
    shim = LegacyAdapterShim()
    result = asyncio.run(shim.read_objects(ConnectorContext(tenant_id="t", connection_id="c"), "sale_order"))
    assert result.status == "ok"
    assert result.safety_flags.erp_write_performed is False


def test_legacy_shim_blocks_write_like_operation():
    shim = LegacyAdapterShim()
    result = asyncio.run(shim.plan_capability(ConnectorContext(tenant_id="t", connection_id="c"), "confirm_document"))
    assert result.status == "blocked"
