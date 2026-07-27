from __future__ import annotations

from collections.abc import Callable

from erpguard.connectors.odoo.transports import OdooReadTransport
from erpguard.connectors.sdk.models import (
    AuthSchema,
    CanonicalOperation,
    CapabilityDefinition,
    ConnectionTestResult,
    ConnectorContext,
    ConnectorFeatures,
    ConnectorMetadata,
    ConnectorSafetyFlags,
    DiscoveredSystemSchema,
    EventBatch,
    ExecutionPermit,
    IngestionCursor,
    NativeExecutionPlan,
    NativeExecutionResult,
    PullEventsRequest,
    ReadObjectsRequest,
    ReadObjectsResult,
    SystemFingerprint,
    VerificationResult,
    stable_digest,
)
from erpguard.connectors.sdk.template import ConnectorTemplate


class OdooConnectorPlugin(ConnectorTemplate):
    metadata = ConnectorMetadata(
        connector_id="odoo",
        package_name="erpguard",
        version="2.0.0",
        display_name="Odoo Connector v2",
        vendor="Odoo",
        system_types=["odoo"],
        supported_versions=["19"],
        plugin_api_version="2",
        features=ConnectorFeatures(
            object_read=True, schema_discovery=True, permission_inspection=True,
            fingerprint=True, verification=True,
        ),
    )

    MODELS = {
        "customer": ("res.partner", ["id", "name", "email"]),
        "product": ("product.product", ["id", "name", "default_code"]),
        "quote": ("sale.order", ["id", "name", "partner_id", "amount_total", "state"]),
    }

    def __init__(self, transport_factory: Callable[[ConnectorContext], OdooReadTransport] | None = None):
        self._transport_factory = transport_factory

    def auth_schemas(self) -> list[AuthSchema]:
        return [AuthSchema(name="credential_ref", kind="secret_reference")]

    def capability_definitions(self) -> list[CapabilityDefinition]:
        return [
            CapabilityDefinition(name=name, version="1", safety_tier="read_only")
            for name in ("customer.read", "product.read", "quote.read", "odoo.schema.discover", "odoo.permissions.inspect")
        ]

    def _transport(self, context: ConnectorContext) -> OdooReadTransport:
        if self._transport_factory is None:
            raise RuntimeError("odoo_transport_factory_required")
        return self._transport_factory(context)

    async def test_connection(self, context: ConnectorContext) -> ConnectionTestResult:
        transport = self._transport(context)
        version = transport.version()
        transport.authenticate()
        return ConnectionTestResult(status="ok", summary=f"odoo_read_only:{version.get('server_version', 'unknown')}")

    async def discover_schema(self, context: ConnectorContext) -> DiscoveredSystemSchema:
        transport = self._transport(context)
        fields: dict[str, list[str]] = {}
        for object_type, (model, defaults) in self.MODELS.items():
            discovered = transport.fields_get(model, ["string", "type", "readonly"])
            fields[object_type] = sorted(set(defaults).union(discovered.keys()))
        return DiscoveredSystemSchema(
            status="ok", objects=sorted(model for model, _ in self.MODELS.values()), fields=fields
        )

    async def fingerprint(self, context: ConnectorContext) -> SystemFingerprint:
        schema = await self.discover_schema(context)
        version = self._transport(context).version().get("server_version", "unknown")
        digest = stable_digest(version, *(f"{key}:{','.join(value)}" for key, value in sorted(schema.fields.items())))
        return SystemFingerprint(connector_id=self.metadata.connector_id, digest=digest, evidence={"version": version})

    async def pull_events(
        self, context: ConnectorContext, cursor: IngestionCursor | None, request: PullEventsRequest
    ) -> EventBatch:
        return EventBatch(status="blocked", events=[], next_cursor=cursor)

    async def read_objects(self, context: ConnectorContext, request: ReadObjectsRequest) -> ReadObjectsResult:
        if request.object_type not in self.MODELS:
            return ReadObjectsResult(status="blocked")
        model, fields = self.MODELS[request.object_type]
        identifiers = [int(value) for value in request.identifiers if value.isdigit()]
        records = self._transport(context).search_read(model, [["id", "in", identifiers]], fields)
        return ReadObjectsResult(status="ok", objects=records)

    async def plan_capability(
        self, context: ConnectorContext, operation: CanonicalOperation | str
    ) -> NativeExecutionPlan:
        capability = operation if isinstance(operation, str) else operation.capability
        supported = any(item.name == capability for item in self.capability_definitions())
        return NativeExecutionPlan(
            capability=capability, status="planned" if supported else "blocked",
            steps=["odoo_read_only"] if supported else [], supports_execution=False,
        )

    async def execute_capability(
        self, context: ConnectorContext, plan: NativeExecutionPlan, permit: ExecutionPermit
    ) -> NativeExecutionResult:
        return NativeExecutionResult(
            status="blocked", summary="odoo_connector_v2_is_read_only",
            errors=["write_capability_not_declared"], safety_flags=ConnectorSafetyFlags(),
        )

    async def verify_execution(
        self, context: ConnectorContext, operation: CanonicalOperation | str, result: NativeExecutionResult
    ) -> VerificationResult:
        return VerificationResult(status="not_executed", verified=False, summary="no_write_to_verify")

    def execution_permit(self, permit_id: str, capability: str) -> ExecutionPermit:
        return ExecutionPermit(permit_id=permit_id, capability=capability)

    def pull_request(self) -> PullEventsRequest:
        return PullEventsRequest()
