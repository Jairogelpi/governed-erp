from __future__ import annotations

import asyncio

import pytest

from erpguard.connectors.odoo.plugin import OdooConnectorPlugin
from erpguard.connectors.odoo.transports import Json2ReadTransport
from erpguard.connectors.sdk.models import ConnectorContext, ReadObjectsRequest
from erpguard.connectors.sdk.registry import discover_connectors
from erpguard.connectors.sdk.runtime import ConnectorRuntime
from erpguard.core.errors import ReadOnlyViolationError


class FakeReadTransport:
    def version(self):
        return {"server_version": "19.0"}

    def authenticate(self):
        return 2

    def fields_get(self, model, attributes=None):
        return {"id": {"type": "integer"}, "name": {"type": "char"}}

    def search_read(self, model, domain, fields, limit=None):
        return [{"id": 7, "name": "SO-007", "model": model}]

    def search_count(self, model, domain):
        return 1


def _plugin() -> OdooConnectorPlugin:
    return OdooConnectorPlugin(lambda context: FakeReadTransport())


def test_odoo_v2_plugin_declares_read_capabilities_and_bounded_writes():
    """Phases 16/17 add two bounded writes; all others remain read-only."""

    plugin = _plugin()
    assert plugin.metadata.connector_id == "odoo"
    assert plugin.metadata.features.controlled_write is True
    definitions = {item.name: item for item in plugin.capability_definitions()}
    assert set(definitions) == {
        "customer.read", "product.read", "quote.read", "odoo.schema.discover",
        "odoo.permissions.inspect", "quote.create_draft", "sales.order.confirm",
    }
    assert definitions["quote.create_draft"].supports_execution is True
    assert definitions["sales.order.confirm"].supports_execution is True
    assert definitions["sales.order.confirm"].safety_tier == "R3_governed_staging_only"
    assert all(
        not d.supports_execution
        for name, d in definitions.items()
        if name not in {"quote.create_draft", "sales.order.confirm"}
    )


def test_odoo_v2_plugin_reads_schema_objects_and_stable_fingerprint():
    plugin = _plugin()
    context = ConnectorContext(tenant_id="tenant-1", connection_id="odoo-1", credential_ref="secret-ref")
    assert asyncio.run(plugin.test_connection(context)).status == "ok"
    schema = asyncio.run(plugin.discover_schema(context))
    assert "sale.order" in schema.objects
    first = asyncio.run(plugin.fingerprint(context))
    second = asyncio.run(plugin.fingerprint(context))
    assert first.digest == second.digest
    result = asyncio.run(plugin.read_objects(context, ReadObjectsRequest(object_type="quote", identifiers=["7"])))
    assert result.status == "ok"
    assert result.objects[0]["name"] == "SO-007"


def test_odoo_v2_plugin_blocks_execution_and_event_pull():
    plugin = _plugin()
    context = ConnectorContext(tenant_id="tenant-1", connection_id="odoo-1", credential_ref="secret-ref")
    plan = asyncio.run(plugin.plan_capability(context, "quote.read"))
    assert plan.supports_execution is False
    result = asyncio.run(plugin.execute_capability(context, plan, plugin.execution_permit("p1", "quote.read")))
    assert result.status == "blocked"
    assert asyncio.run(plugin.pull_events(context, None, plugin.pull_request())).status == "blocked"


def test_json2_transport_rejects_write_method():
    transport = Json2ReadTransport(lambda method, payload: {})
    with pytest.raises(ReadOnlyViolationError):
        transport.call("create", "sale.order", {})


def test_discovered_odoo_plugin_gets_transport_from_runtime_services():
    plugin, context = ConnectorRuntime(discover_connectors()).create_plugin(
        "odoo",
        ConnectorContext(tenant_id="tenant-1", connection_id="odoo-1", credential_ref="ref"),
        {"transport_factory": lambda _: FakeReadTransport()},
    )
    assert asyncio.run(plugin.test_connection(context)).status == "ok"
