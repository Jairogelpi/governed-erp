from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ConnectorFeaturesResponse(BaseModel):
    event_source: bool
    object_read: bool
    schema_discovery: bool
    permission_inspection: bool
    fingerprint: bool
    controlled_write: bool
    verification: bool
    compensation: bool
    webhooks: bool


class ConnectorAuthSchemaResponse(BaseModel):
    name: str
    kind: str
    required: bool
    secret: bool


class ConnectorCapabilityResponse(BaseModel):
    name: str
    version: str
    safety_tier: str
    description: str
    supports_execution: bool


class ConnectorDefinitionResponse(BaseModel):
    connector_id: str
    package_name: str
    version: str
    display_name: str
    vendor: str
    system_types: list[str]
    supported_versions: list[str]
    plugin_api_version: str
    features: ConnectorFeaturesResponse
    auth_schemas: list[ConnectorAuthSchemaResponse]
    capabilities: list[ConnectorCapabilityResponse]


class ConnectorTestRequest(BaseModel):
    connection_id: str = Field(min_length=1, max_length=128)


class ConnectorTestResponse(BaseModel):
    connector_id: str
    connection_id: str
    status: str
    summary: str
    safety_flags: dict[str, Any]
