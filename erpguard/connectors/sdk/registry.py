from __future__ import annotations

from importlib.metadata import entry_points
from typing import Iterable

from erpguard.connectors.sdk.plugin import ConnectorPlugin


class ConnectorRegistry:
    def __init__(self, plugins: Iterable[ConnectorPlugin]):
        self._plugins: dict[str, ConnectorPlugin] = {}
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


def discover_connectors() -> ConnectorRegistry:
    discovered = []
    for entry_point in entry_points(group="erpguard.connectors"):
        plugin = entry_point.load()
        plugin = plugin() if isinstance(plugin, type) else plugin
        discovered.append(plugin)
    return ConnectorRegistry(discovered)
