from __future__ import annotations

from pydantic import BaseModel


class ConnectorListResponse(BaseModel):
    connectors: list[dict]
    policy_version: str


class ConnectorPolicyResponse(BaseModel):
    connector_id: str
    allowed_operations: list[str]
    forbidden_operations: list[str]
    allowed_scopes: list[str]
    write_operations_enabled: bool
    mcp_execution_enabled: bool
    arbitrary_http_enabled: bool
    erp_write_enabled: bool
    policy_version: str


class TestReadinessRequest(BaseModel):
    auth_profile_id: str
    actor: dict = {}


class TestReadinessResponse(BaseModel):
    connector_id: str
    auth_profile_id: str
    policy_allowed: bool
    fixture_mode: bool
    violations: list[str]
    allowed_scopes: list[str]
    policy_version: str


class ReadCalendarsRequest(BaseModel):
    auth_profile_id: str
    actor: dict = {}


class ReadCalendarsResponse(BaseModel):
    connector_id: str
    auth_profile_id: str
    fixture_mode: bool
    calendars: list[dict]
    total_count: int
    redacted_fields_count: int
    read_only: bool
    evidence_id: str
    signals: list[dict]


class ReadUpcomingEventsRequest(BaseModel):
    auth_profile_id: str
    max_results: int = 10
    actor: dict = {}


class ReadUpcomingEventsResponse(BaseModel):
    connector_id: str
    auth_profile_id: str
    fixture_mode: bool
    events: list[dict]
    total_count: int
    redacted_fields_count: int
    read_only: bool
    evidence_id: str
    signals: list[dict]


class ConnectorReadEvidenceResponse(BaseModel):
    id: str
    auth_profile_id: str
    connector_id: str
    operation: str
    fixture_mode: bool
    record_count: int
    redacted_fields_count: int
    result_summary: dict
    policy_passed: bool
    read_only: bool
    created_at: str


class ConnectorReadEvidenceListResponse(BaseModel):
    auth_profile_id: str
    evidence: list[dict]


class ConnectorSignalListResponse(BaseModel):
    auth_profile_id: str
    connector_id: str
    signals: list[dict]


class ExternalConnectorAuditResponse(BaseModel):
    auth_profile_id: str
    events: list[dict]
