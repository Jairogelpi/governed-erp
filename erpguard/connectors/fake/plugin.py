from __future__ import annotations

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


class FakeConnector(ConnectorTemplate):
    metadata = ConnectorMetadata(
        connector_id="fake",
        package_name="erpguard",
        version="2.0.0",
        display_name="ERPGuard Fake Connector",
        vendor="ERPGuard",
        system_types=["fake_erp"],
        supported_versions=["1"],
        plugin_api_version="2",
        features=ConnectorFeatures(
            object_read=True,
            schema_discovery=True,
            fingerprint=True,
            verification=True,
        ),
    )

    def auth_schemas(self) -> list[AuthSchema]:
        return [AuthSchema(name="credential_ref", kind="secret_reference")]

    def capability_definitions(self) -> list[CapabilityDefinition]:
        return [
            CapabilityDefinition(
                name="sales.order.read",
                version="1",
                safety_tier="read_only",
                description="Read a deterministic fake sales order.",
            )
        ]

    async def test_connection(self, context: ConnectorContext) -> ConnectionTestResult:
        return ConnectionTestResult(status="ok", summary="fake_connector_ready")

    async def discover_schema(self, context: ConnectorContext) -> DiscoveredSystemSchema:
        return DiscoveredSystemSchema(
            status="ok",
            objects=["sale_order", "product", "partner"],
            fields={"sale_order": ["id", "name", "state"]},
        )

    async def fingerprint(self, context: ConnectorContext) -> SystemFingerprint:
        return SystemFingerprint(
            connector_id=self.metadata.connector_id,
            digest=stable_digest(self.metadata.connector_id, context.connection_id, "fake-v2"),
            evidence={"source": "deterministic_fixture"},
        )

    async def pull_events(
        self,
        context: ConnectorContext,
        cursor: IngestionCursor | None,
        request: PullEventsRequest,
    ) -> EventBatch:
        return EventBatch(status="ok", events=[], next_cursor=cursor)

    async def read_objects(
        self, context: ConnectorContext, request: ReadObjectsRequest
    ) -> ReadObjectsResult:
        return ReadObjectsResult(
            status="ok",
            objects=[{"id": identifier, "object_type": request.object_type} for identifier in request.identifiers],
        )

    async def plan_capability(
        self, context: ConnectorContext, operation: CanonicalOperation | str
    ) -> NativeExecutionPlan:
        capability = operation if isinstance(operation, str) else operation.capability
        supported = any(item.name == capability for item in self.capability_definitions())
        return NativeExecutionPlan(
            capability=capability,
            status="planned" if supported else "blocked",
            steps=["fake_read"] if supported else [],
            supports_execution=False,
        )

    async def execute_capability(
        self, context: ConnectorContext, plan: NativeExecutionPlan, permit: ExecutionPermit
    ) -> NativeExecutionResult:
        return NativeExecutionResult(
            status="blocked",
            summary="fake_connector_execution_disabled_in_phase5",
            errors=["execution_not_enabled"],
            safety_flags=ConnectorSafetyFlags(),
        )

    async def verify_execution(
        self,
        context: ConnectorContext,
        operation: CanonicalOperation | str,
        result: NativeExecutionResult,
    ) -> VerificationResult:
        return VerificationResult(status="not_executed", verified=False, summary="no_execution_to_verify")
