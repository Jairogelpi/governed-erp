"""Deprecated read-only bridge for the pre-SDK adapter surface.

This module deliberately does not import an ERP adapter or delegate generic
writes. Connector SDK v2 plugins must implement semantic capabilities instead.
"""

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


class LegacyAdapterShim(ConnectorTemplate):
    """Temporary read-only SDK facade over the legacy contract boundary."""

    metadata = ConnectorMetadata(
        connector_id="legacy-adapter-shim",
        package_name="erpguard",
        version="2.0.0",
        display_name="Legacy Adapter Shim",
        vendor="ERPGuard",
        system_types=["legacy"],
        supported_versions=["1"],
        plugin_api_version="2",
        features=ConnectorFeatures(object_read=True, fingerprint=True),
    )

    def auth_schemas(self) -> list[AuthSchema]:
        return [AuthSchema(name="credential_ref", kind="secret_reference")]

    def capability_definitions(self) -> list[CapabilityDefinition]:
        return [CapabilityDefinition(name="legacy.read_objects", version="1", safety_tier="read_only")]

    async def test_connection(self, context: ConnectorContext) -> ConnectionTestResult:
        return ConnectionTestResult(status="ok", summary="legacy_read_only_shim_ready")

    async def discover_schema(self, context: ConnectorContext) -> DiscoveredSystemSchema:
        return DiscoveredSystemSchema(status="advisory", objects=[])

    async def fingerprint(self, context: ConnectorContext) -> SystemFingerprint:
        return SystemFingerprint(
            connector_id=self.metadata.connector_id,
            digest=stable_digest(self.metadata.connector_id, context.connection_id),
        )

    async def pull_events(
        self,
        context: ConnectorContext,
        cursor: IngestionCursor | None,
        request: PullEventsRequest,
    ) -> EventBatch:
        return EventBatch(status="blocked", events=[], next_cursor=cursor)

    async def read_objects(
        self, context: ConnectorContext, object_type: str | ReadObjectsRequest
    ) -> ReadObjectsResult:
        return ReadObjectsResult(status="ok", objects=[])

    async def plan_capability(
        self, context: ConnectorContext, operation: CanonicalOperation | str
    ) -> NativeExecutionPlan:
        capability = operation if isinstance(operation, str) else operation.capability
        read_only = capability in {"legacy.read_objects", "read_object", "search_objects"}
        return NativeExecutionPlan(
            capability=capability,
            status="planned" if read_only else "blocked",
            steps=["legacy_read_only"] if read_only else [],
            supports_execution=False,
        )

    async def execute_capability(
        self, context: ConnectorContext, plan: NativeExecutionPlan, permit: ExecutionPermit
    ) -> NativeExecutionResult:
        return NativeExecutionResult(
            status="blocked",
            summary="legacy_shim_never_executes",
            errors=["legacy_write_and_execution_blocked"],
            safety_flags=ConnectorSafetyFlags(),
        )

    async def verify_execution(
        self,
        context: ConnectorContext,
        operation: CanonicalOperation | str,
        result: NativeExecutionResult,
    ) -> VerificationResult:
        return VerificationResult(status="not_executed", verified=False)
