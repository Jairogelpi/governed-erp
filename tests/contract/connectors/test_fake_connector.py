from __future__ import annotations

import asyncio

from erpguard.connectors.sdk.models import ConnectorContext, ExecutionPermit
from erpguard.connectors.sdk.registry import discover_connectors


def test_fake_connector_contract_is_read_only_and_deterministic():
    plugin = discover_connectors().get("fake")
    context = ConnectorContext(tenant_id="tenant-1", connection_id="conn-1")
    first = asyncio.run(plugin.fingerprint(context))
    second = asyncio.run(plugin.fingerprint(context))
    assert first == second
    assert plugin.metadata.features.controlled_write is False
    assert asyncio.run(plugin.test_connection(context)).status == "ok"


def test_fake_connector_blocks_execution_even_with_permit():
    plugin = discover_connectors().get("fake")
    context = ConnectorContext(tenant_id="tenant-1", connection_id="conn-1")
    plan = asyncio.run(plugin.plan_capability(context, "sales.order.read"))
    result = asyncio.run(
        plugin.execute_capability(context, plan, ExecutionPermit(permit_id="permit-1", capability=plan.capability))
    )
    assert result.status == "blocked"
    assert result.safety_flags.external_http_performed is False
    assert result.safety_flags.erp_write_performed is False
