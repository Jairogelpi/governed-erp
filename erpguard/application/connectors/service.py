"""Tenant-scoped orchestration from unified connections to Connector SDK v2."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from erpguard.adapters.odoo.client import OdooClient
from erpguard.adapters.odoo.config import OdooConfig
from erpguard.adapters.odoo.write_client import OdooQuoteDraftClient
from erpguard.config import settings
from erpguard.connectors.odoo.transports import LegacyXmlRpcReadTransport
from erpguard.connectors.odoo.write_transport import LegacyXmlRpcWriteTransport
from erpguard.connectors.sdk import ConnectorRuntime, ConnectorRegistry, discover_connectors
from erpguard.connectors.sdk.models import ConnectorContext, ConnectorMetadata, ConnectionTestResult
from erpguard.db.model_packages.connections import EncryptedSecret, UnifiedConnection
from erpguard.infrastructure.secrets import EncryptedLocalSecretProvider


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
        services: dict[str, object] = {
            "connection_endpoint": connection.endpoint,
            "connection_metadata": metadata,
        }
        if connector_id == "odoo":
            services["transport_factory"] = self._odoo_transport_factory(connection)
            services["write_transport_factory"] = self._odoo_write_transport_factory(connection)
            services["declared_capability_lookup"] = self._declared_capability_lookup(tenant_id)
        context = ConnectorContext(
            tenant_id=tenant_id,
            connection_id=connection.id,
            credential_ref=connection.secret_ref,
            services=services,
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

    def _odoo_config(self, connection: UnifiedConnection) -> OdooConfig:
        metadata = json.loads(connection.metadata_json or "{}")
        secret_row = (
            self.session.query(EncryptedSecret)
            .filter(EncryptedSecret.id == connection.secret_ref, EncryptedSecret.tenant_id == connection.tenant_id)
            .one_or_none()
        )
        if secret_row is None or secret_row.status != "active":
            raise ConnectorOperationUnavailable("connection_secret_unavailable")
        api_key = EncryptedLocalSecretProvider(settings.local_secret_key).reveal(secret_row.ciphertext)
        return OdooConfig(
            url=connection.endpoint,
            database=metadata.get("database", ""),
            username=metadata.get("username", ""),
            api_key=api_key,
        )

    def _odoo_transport_factory(self, connection: UnifiedConnection):
        def factory(context: ConnectorContext) -> LegacyXmlRpcReadTransport:
            return LegacyXmlRpcReadTransport(OdooClient(self._odoo_config(connection)))

        return factory

    def _odoo_write_transport_factory(self, connection: UnifiedConnection):
        def factory(context: ConnectorContext) -> LegacyXmlRpcWriteTransport:
            return LegacyXmlRpcWriteTransport(OdooQuoteDraftClient(self._odoo_config(connection)))

        return factory

    def _declared_capability_lookup(self, tenant_id: str):
        from erpguard.db.model_packages.declared_capabilities import DeclaredWriteCapability

        def lookup(capability_id: str) -> DeclaredWriteCapability | None:
            return (
                self.session.query(DeclaredWriteCapability)
                .filter_by(tenant_id=tenant_id, id=capability_id, status="active")
                .one_or_none()
            )

        return lookup
