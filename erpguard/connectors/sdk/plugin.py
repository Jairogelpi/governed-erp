from __future__ import annotations

from typing import Protocol

from erpguard.connectors.sdk.models import (
    AuthSchema,
    CanonicalOperation,
    ConnectionTestResult,
    ConnectorContext,
    ConnectorMetadata,
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
)


class ConnectorPlugin(Protocol):
    metadata: ConnectorMetadata

    def auth_schemas(self) -> list[AuthSchema]: ...

    def capability_definitions(self) -> list: ...

    async def test_connection(self, context: ConnectorContext) -> ConnectionTestResult: ...

    async def discover_schema(self, context: ConnectorContext) -> DiscoveredSystemSchema: ...

    async def fingerprint(self, context: ConnectorContext) -> SystemFingerprint: ...

    async def pull_events(
        self,
        context: ConnectorContext,
        cursor: IngestionCursor | None,
        request: PullEventsRequest,
    ) -> EventBatch: ...

    async def read_objects(
        self, context: ConnectorContext, request: ReadObjectsRequest
    ) -> ReadObjectsResult: ...

    async def plan_capability(
        self, context: ConnectorContext, operation: CanonicalOperation | str
    ) -> NativeExecutionPlan: ...

    async def execute_capability(
        self, context: ConnectorContext, plan: NativeExecutionPlan, permit: ExecutionPermit
    ) -> NativeExecutionResult: ...

    async def verify_execution(
        self,
        context: ConnectorContext,
        operation: CanonicalOperation | str,
        result: NativeExecutionResult,
    ) -> VerificationResult: ...
