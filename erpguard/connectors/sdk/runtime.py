from __future__ import annotations

from erpguard.connectors.sdk.models import ConnectorContext
from erpguard.connectors.sdk.registry import ConnectorRegistry


class ConnectorRuntime:
    """Instantiates discovered plugins while keeping runtime services out of metadata."""

    def __init__(self, registry: ConnectorRegistry):
        self.registry = registry

    def create_plugin(
        self, connector_id: str, context: ConnectorContext, services: dict
    ) -> tuple[object, ConnectorContext]:
        plugin = self.registry.create(connector_id)
        return plugin, context.model_copy(update={"services": services})
