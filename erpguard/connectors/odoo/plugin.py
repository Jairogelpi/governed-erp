from __future__ import annotations

from collections.abc import Callable

from erpguard.connectors.odoo.transports import OdooReadTransport
from erpguard.connectors.odoo.write_transport import OdooWriteTransport
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
            fingerprint=True, verification=True, controlled_write=True,
        ),
    )

    MODELS = {
        "customer": ("res.partner", ["id", "name", "email"]),
        "product": ("product.product", ["id", "name", "default_code"]),
        "quote": ("sale.order", ["id", "name", "partner_id", "amount_total", "state"]),
    }

    def __init__(
        self,
        transport_factory: Callable[[ConnectorContext], OdooReadTransport] | None = None,
        write_transport_factory: Callable[[ConnectorContext], OdooWriteTransport] | None = None,
    ):
        self._transport_factory = transport_factory
        self._write_transport_factory = write_transport_factory

    def auth_schemas(self) -> list[AuthSchema]:
        return [AuthSchema(name="credential_ref", kind="secret_reference")]

    def capability_definitions(self) -> list[CapabilityDefinition]:
        read_only = [
            CapabilityDefinition(name=name, version="1", safety_tier="read_only")
            for name in ("customer.read", "product.read", "quote.read", "odoo.schema.discover", "odoo.permissions.inspect")
        ]
        # Phase 16: the one write-capable capability this connector declares.
        # Scoped to exactly one atomic bridge method (create a draft
        # sale.order) -- never confirm/invoice/picking.
        write_capable = [
            CapabilityDefinition(
                name="quote.create_draft", version="1", safety_tier="write_scoped_draft_only", supports_execution=True
            )
        ]
        return read_only + write_capable

    def _transport(self, context: ConnectorContext) -> OdooReadTransport:
        factory = self._transport_factory or context.services.get("transport_factory")
        if factory is None:
            raise RuntimeError("odoo_transport_factory_required")
        return factory(context)

    def _write_transport(self, context: ConnectorContext) -> OdooWriteTransport:
        factory = self._write_transport_factory or context.services.get("write_transport_factory")
        if factory is None:
            raise RuntimeError("odoo_write_transport_factory_required")
        return factory(context)

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
        arguments = {} if isinstance(operation, str) else operation.arguments
        definitions = {item.name: item for item in self.capability_definitions()}
        definition = definitions.get(capability)
        if definition is None:
            return NativeExecutionPlan(capability=capability, status="blocked", steps=[], supports_execution=False)
        steps = ["odoo_read_only"] if not definition.supports_execution else ["odoo_create_draft_quote"]
        return NativeExecutionPlan(
            capability=capability, status="planned", steps=steps,
            supports_execution=definition.supports_execution, arguments=arguments,
        )

    async def execute_capability(
        self, context: ConnectorContext, plan: NativeExecutionPlan, permit: ExecutionPermit
    ) -> NativeExecutionResult:
        if plan.capability != "quote.create_draft":
            return NativeExecutionResult(
                status="blocked", summary="odoo_connector_v2_is_read_only",
                errors=["write_capability_not_declared"], safety_flags=ConnectorSafetyFlags(),
            )
        return self._execute_quote_create_draft(context, plan)

    def _execute_quote_create_draft(self, context: ConnectorContext, plan: NativeExecutionPlan) -> NativeExecutionResult:
        try:
            partner_id = int(plan.arguments["partner_id"])
            lines = plan.arguments["lines"]
            client_reference = str(plan.arguments["client_reference"])
        except (KeyError, TypeError, ValueError) as exc:
            return NativeExecutionResult(
                status="blocked", summary="invalid_quote_create_draft_arguments",
                errors=[str(exc)], safety_flags=ConnectorSafetyFlags(),
            )

        transport = self._write_transport(context)
        existing_id = transport.find_by_client_reference(client_reference)
        if existing_id is not None:
            # Idempotency: same client_reference -> the existing draft, no
            # second order created.
            return NativeExecutionResult(
                status="ok", summary="draft_already_exists_for_client_reference",
                payload={"order_id": existing_id, "created": False},
                safety_flags=ConnectorSafetyFlags(erp_touched=True, erp_write_performed=False),
            )

        order_id = transport.create_draft(partner_id=partner_id, lines=lines, client_reference=client_reference)
        return NativeExecutionResult(
            status="ok", summary="draft_quote_created",
            payload={"order_id": order_id, "created": True},
            safety_flags=ConnectorSafetyFlags(erp_touched=True, erp_write_performed=True),
        )

    async def verify_execution(
        self, context: ConnectorContext, operation: CanonicalOperation | str, result: NativeExecutionResult
    ) -> VerificationResult:
        capability = operation if isinstance(operation, str) else operation.capability
        if capability != "quote.create_draft" or result.status != "ok":
            return VerificationResult(status="not_executed", verified=False, summary="no_write_to_verify")

        order_id = result.payload.get("order_id")
        if order_id is None:
            return VerificationResult(status="verification_failed", verified=False, summary="missing_order_id")

        transport = self._write_transport(context)
        order = transport.read_order(int(order_id))
        if order.get("state") != "draft":
            return VerificationResult(
                status="verification_failed", verified=False,
                summary=f"postcondition_failed:expected_state_draft_got_{order.get('state')}",
            )
        return VerificationResult(status="verified", verified=True, summary="draft_state_confirmed")

    def execution_permit(self, permit_id: str, capability: str) -> ExecutionPermit:
        return ExecutionPermit(permit_id=permit_id, capability=capability)

    def pull_request(self) -> PullEventsRequest:
        return PullEventsRequest()
