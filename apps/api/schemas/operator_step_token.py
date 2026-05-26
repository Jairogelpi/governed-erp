from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class StepPreviewRequest(BaseModel):
    plan_id: str
    step_number: int
    step_title: str
    endpoint_hint: str
    method_hint: str
    severity: str


class StepPreviewResponse(BaseModel):
    token_id: str
    plan_id: str
    step_number: int
    step_title: str
    endpoint_hint: str
    method_hint: str
    severity: str
    risk_level: str
    risk_summary: str
    status: str
    expires_at: Any
    ttl_seconds: int
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


class TokenStatusResponse(BaseModel):
    token_id: str
    plan_id: str
    step_number: int
    step_title: str
    risk_level: str
    status: str
    expires_at: Any
    confirmed_at: Any
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


class StepConfirmRequest(BaseModel):
    token_id: str


class StepConfirmResponse(BaseModel):
    token_id: str
    plan_id: str
    step_number: int
    step_title: str
    status: str
    confirmed_at: Any
    message: str
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True
