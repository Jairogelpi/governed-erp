"""Small template for independent Connector SDK v2 packages."""

from __future__ import annotations

from abc import ABC, abstractmethod

from erpguard.connectors.sdk.models import AuthSchema, CapabilityDefinition, ConnectorMetadata


class ConnectorTemplate(ABC):
    """Base helper that keeps future plugins independent of ERPGuard internals."""

    metadata: ConnectorMetadata

    @abstractmethod
    def auth_schemas(self) -> list[AuthSchema]:
        raise NotImplementedError

    @abstractmethod
    def capability_definitions(self) -> list[CapabilityDefinition]:
        raise NotImplementedError
