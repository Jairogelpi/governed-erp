"""Framework-neutral Connector SDK v2 contracts and discovery."""

from erpguard.connectors.sdk.models import (
    CapabilityDefinition,
    ConnectorContext,
    ConnectorFeatures,
    ConnectorMetadata,
    ConnectorSafetyFlags,
    ExecutionPermit,
)
from erpguard.connectors.sdk.plugin import ConnectorPlugin
from erpguard.connectors.sdk.registry import ConnectorRegistry, discover_connectors
from erpguard.connectors.sdk.runtime import ConnectorRuntime

__all__ = [
    "CapabilityDefinition",
    "ConnectorContext",
    "ConnectorFeatures",
    "ConnectorMetadata",
    "ConnectorSafetyFlags",
    "ConnectorPlugin",
    "ConnectorRegistry",
    "ExecutionPermit",
    "ConnectorRuntime",
    "discover_connectors",
]
