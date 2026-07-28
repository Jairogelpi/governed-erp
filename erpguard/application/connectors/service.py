"""Tenant-scoped orchestration from unified connections to Connector SDK v2."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from erpguard.connectors.sdk import ConnectorRuntime, ConnectorRegistry, discover_connectors
from erpguard.connectors.sdk.models import ConnectorContext, ConnectorMetadata, ConnectionTestResult
from erpguard.db.model_packages.connections import UnifiedConnection


class ConnectorApplicationError(ValueError):
    """Controlled connector application error with a stable public code."""


class ConnectorNotFound(ConnectorApplicationError):
    pass


class ConnectionNotFound(ConnectorApplicationError):
    pass


class ConnectorConnectionMismatch(ConnectorApplicationError):
    pass


class ConnectorOperationUnavailable(ConnectorApplicationError):
    pass


class ConnectorApplicationService:
    """Use the one connection -> definition -> runtime -> plugin flow."""

    def __init__(
        self,
        session: Session,
        *,
        registry: ConnectorRegistry | None = None,
        runtime: ConnectorRuntime | None = None,
    ) -> None:
        self.session = session
        self.registry = registry or discover_connectors()
        self.runtime = runtime or ConnectorRuntime(self.registry)

    def list_definitions(self) -> list[ConnectorMetadata]:
        return [plugin.metadata for plugin in self.registry.list()]

    def get_definition(self, connector_id: str) -> ConnectorMetadata:
        try:
            return self.registry.get(connector_id).metadata
        except KeyError as exc:
            raise ConnectorNotFound("connector_not_found") from exc

    def ensure_connector(self, connector_id: str) -> None:
        self.get_definition(connector_id)

    def connection_context(
        self,
        *,
        tenant_id: str,
        connection_id: str,
        connector_id: str,
    ) -> tuple[UnifiedConnection, ConnectorContext]:
        self.ensure_connector(connector_id)
        connection = (
            self.session.query(UnifiedConnection)
            .filter(
                UnifiedConnection.id == connection_id,
                UnifiedConnection.tenant_id == tenant_id,
            )
            .one_or_none()
        )
        if connection is None:
            raise ConnectionNotFound("connection_not_found")
        if connection.connector_type != connector_id:
            raise ConnectorConnectionMismatch("connector_connection_mismatch")
        metadata = json.loads(connection.metadata_json or "{}")
        context = ConnectorContext(
            tenant_id=tenant_id,
            connection_id=connection.id,
            credential_ref=connection.secret_ref,
            services={
                "connection_endpoint": connection.endpoint,
                "connection_metadata": metadata,
            },
        )
        return connection, context

    async def test_connection(
        self,
        *,
        tenant_id: str,
        connection_id: str,
        connector_id: str,
    ) -> ConnectionTestResult:
        _, context = self.connection_context(
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector_id=connector_id,
        )
        plugin, runtime_context = self.runtime.create_plugin(
            connector_id,
            context,
            {
                "connection_endpoint": context.services["connection_endpoint"],
                "connection_metadata": context.services["connection_metadata"],
            },
        )
        try:
            return await plugin.test_connection(runtime_context)
        except (RuntimeError, ValueError) as exc:
            raise ConnectorOperationUnavailable("connector_operation_unavailable") from exc
