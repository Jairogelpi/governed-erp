from __future__ import annotations

from importlib.metadata import entry_points
from typing import Iterable

from erpguard.connectors.sdk.plugin import ConnectorPlugin


class ConnectorRegistry:
    def __init__(self, plugins: Iterable[ConnectorPlugin], factories: dict[str, object] | None = None):
        self._plugins: dict[str, ConnectorPlugin] = {}
        self._factories = factories or {}
        for plugin in plugins:
            connector_id = plugin.metadata.connector_id
            if connector_id in self._plugins:
                raise ValueError(f"duplicate_connector_id:{connector_id}")
            self._plugins[connector_id] = plugin

    def get(self, connector_id: str) -> ConnectorPlugin:
        try:
            return self._plugins[connector_id]
        except KeyError as exc:
            raise KeyError(connector_id) from exc

    def list(self) -> list[ConnectorPlugin]:
        return [self._plugins[key] for key in sorted(self._plugins)]

    def create(self, connector_id: str, **kwargs) -> ConnectorPlugin:
        factory = self._factories.get(connector_id)
        if factory is None:
            return self.get(connector_id)
        return factory(**kwargs) if callable(factory) else self.get(connector_id)


def discover_connectors() -> ConnectorRegistry:
    discovered = []
    factories: dict[str, object] = {}
    for entry_point in entry_points(group="erpguard.connectors"):
        factory = entry_point.load()
        plugin = factory() if isinstance(factory, type) else factory
        discovered.append(plugin)
        factories[plugin.metadata.connector_id] = factory
    return ConnectorRegistry(discovered, factories)
