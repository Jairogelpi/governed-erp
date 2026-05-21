from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from erpguard.product.connector_auth_profile import (
    ConnectorAuthProfileModel,
    ConnectorTestResult,
)
from erpguard.product.credential_audit import CredentialAuditEventModel
from erpguard.product.scope_registry import ConnectorScopeDefinition


class CreateConnectorAuthProfileRequest(BaseModel):
    connector_id: str
    display_name: str
    auth_type: str = "oauth_placeholder"
    requested_scopes: list[str] = Field(default_factory=list)
    credential: dict[str, Any] = Field(default_factory=dict)
    created_by: dict[str, Any] = Field(default_factory=dict)


class ConnectorAuthProfileResponse(ConnectorAuthProfileModel):
    pass


class ConnectorAuthProfileListResponse(BaseModel):
    profiles: list[ConnectorAuthProfileModel] = Field(default_factory=list)


class ConnectorTestRequest(BaseModel):
    actor: dict[str, Any] = Field(default_factory=dict)


class ConnectorTestResponse(ConnectorTestResult):
    pass


class RotateConnectorAuthProfileRequest(BaseModel):
    credential: dict[str, Any] = Field(default_factory=dict)
    actor: dict[str, Any] = Field(default_factory=dict)


class RevokeConnectorAuthProfileRequest(BaseModel):
    actor: dict[str, Any] = Field(default_factory=dict)


class ConnectorCredentialAuditResponse(BaseModel):
    profile_id: str
    events: list[CredentialAuditEventModel] = Field(default_factory=list)


class ConnectorScopeListResponse(BaseModel):
    scopes: list[ConnectorScopeDefinition] = Field(default_factory=list)
