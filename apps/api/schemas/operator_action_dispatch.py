from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ActionRegistryEntrySchema(BaseModel):
    action_key: str
    display_name: str
    description: str
    endpoint_template: str
    method: str
    requires_confirmed_token: bool
    safety_tier: str
    allowed: bool


class ActionRegistryResponse(BaseModel):
    actions: list[ActionRegistryEntrySchema]
    total: int
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


class DispatchEligibilityRequest(BaseModel):
    action_key: str | None = None
    endpoint_hint: str
    method_hint: str = "GET"
    token_id: str | None = None
    version_id: str | None = None


class DispatchEligibilityResponse(BaseModel):
    action_key: str
    endpoint_hint: str
    eligible: bool
    blocked_reason: str | None
    policy_name: str | None
    requires_confirmed_token: bool
    safety_tier: str
    token_id: str | None
    token_status: str | None
    version_id: str | None
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


class DispatchAuditEntrySchema(BaseModel):
    event_id: str
    action_key: str
    endpoint_hint: str
    token_id: str | None
    version_id: str | None
    eligible: bool
    blocked_reason: str | None
    policy_name: str | None
    created_at: Any


class DispatchAuditResponse(BaseModel):
    entries: list[DispatchAuditEntrySchema]
    event_count: int
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True
