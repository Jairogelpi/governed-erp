from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class OdooReadOnlyDemoFlowRequest(BaseModel):
    requested_by: str = "operator_1"
    object_types: list[str] = Field(
        default_factory=lambda: ["partner", "product", "sale_order"]
    )
    allow_network_test: bool = False
    allow_business_read: bool = False


class OdooReadOnlyDemoFlowResponse(BaseModel):
    demo_flow_id: str
    activation_id: str
    adapter_session_id: str
    connection_test_id: str
    read_mapping_ids: list[str]
    evidence_pack_ids: list[str]
    requested_object_types: list[str]
    object_summaries: list[dict[str, Any]]
    status: str
    safety_summary: dict[str, Any]
    created_by: str
    blocking_reasons: list[str]


class OdooReadOnlyDemoFlowListResponse(BaseModel):
    demo_flows: list[OdooReadOnlyDemoFlowResponse]


class OdooReadOnlyDemoAuditEventResponse(BaseModel):
    event_type: str
    demo_flow_id: str
    activation_id: str
    adapter_session_id: str
    connection_test_id: str
    status: str
    actor: str
    details: dict[str, Any]
    created_at: datetime


class OdooReadOnlyDemoAuditResponse(BaseModel):
    events: list[OdooReadOnlyDemoAuditEventResponse]
