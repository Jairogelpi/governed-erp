from __future__ import annotations

import hashlib
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SDKModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConnectorFeatures(SDKModel):
    event_source: bool = False
    object_read: bool = False
    schema_discovery: bool = False
    permission_inspection: bool = False
    fingerprint: bool = False
    controlled_write: bool = False
    verification: bool = False
    compensation: bool = False
    webhooks: bool = False


class ConnectorMetadata(SDKModel):
    connector_id: str = Field(min_length=1, max_length=100)
    package_name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    vendor: str = Field(min_length=1)
    system_types: list[str] = Field(min_length=1)
    supported_versions: list[str] = Field(default_factory=list)
    plugin_api_version: str = Field(min_length=1)
    features: ConnectorFeatures


class AuthSchema(SDKModel):
    name: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    required: bool = True
    secret: bool = True


class CapabilityDefinition(SDKModel):
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    safety_tier: str = Field(min_length=1)
    description: str = ""
    supports_execution: bool = False


class ConnectorContext(SDKModel):
    tenant_id: str = Field(min_length=1)
    connection_id: str = Field(min_length=1)
    credential_ref: str | None = None
    credentials: dict[str, Any] = Field(default_factory=dict)
    services: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def reject_raw_credentials(self) -> "ConnectorContext":
        if self.credentials:
            raise ValueError("raw secret credentials are not accepted; use credential_ref")
        return self


class ConnectorSafetyFlags(SDKModel):
    external_http_performed: bool = False
    erp_touched: bool = False
    erp_write_performed: bool = False
    credentials_exposed: bool = False
    raw_secret_accessed: bool = False


class ConnectionTestResult(SDKModel):
    status: str
    summary: str
    safety_flags: ConnectorSafetyFlags = Field(default_factory=ConnectorSafetyFlags)


class DiscoveredSystemSchema(SDKModel):
    status: str
    objects: list[str] = Field(default_factory=list)
    fields: dict[str, list[str]] = Field(default_factory=dict)


class SystemFingerprint(SDKModel):
    connector_id: str
    digest: str
    stable: bool = True
    evidence: dict[str, Any] = Field(default_factory=dict)


class ReadObjectsRequest(SDKModel):
    object_type: str = Field(min_length=1)
    identifiers: list[str] = Field(default_factory=list)


class ReadObjectsResult(SDKModel):
    status: str
    objects: list[dict[str, Any]] = Field(default_factory=list)
    safety_flags: ConnectorSafetyFlags = Field(default_factory=ConnectorSafetyFlags)


class PullEventsRequest(SDKModel):
    limit: int = Field(default=100, ge=1, le=1000)


class IngestionCursor(SDKModel):
    value: str


class EventBatch(SDKModel):
    status: str
    events: list[dict[str, Any]] = Field(default_factory=list)
    next_cursor: IngestionCursor | None = None


class CanonicalOperation(SDKModel):
    capability: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class NativeExecutionPlan(SDKModel):
    capability: str
    status: str = "planned"
    steps: list[str] = Field(default_factory=list)
    supports_execution: bool = False
    arguments: dict[str, Any] = Field(default_factory=dict)


class ExecutionPermit(SDKModel):
    permit_id: str = Field(min_length=1)
    capability: str = Field(min_length=1)
    approved: bool = True


class NativeExecutionResult(SDKModel):
    status: str
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)
    safety_flags: ConnectorSafetyFlags = Field(default_factory=ConnectorSafetyFlags)
    errors: list[str] = Field(default_factory=list)


class VerificationResult(SDKModel):
    status: str
    verified: bool = False
    summary: str = ""


def stable_digest(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
