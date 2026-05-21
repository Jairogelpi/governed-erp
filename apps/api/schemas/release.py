from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ReleaseCheckResponse(BaseModel):
    name: str
    passed: bool
    detail: str


class SprintChainEntryResponse(BaseModel):
    sprint: str
    description: str


class ReleaseReadinessResponse(BaseModel):
    release_version: str
    status: str
    readiness_score: int
    checks_passed: int
    checks_total: int
    checks: list[ReleaseCheckResponse] = []
    sprint_chain: list[SprintChainEntryResponse] = []
    safety_boundaries: dict[str, Any] = {}
    blocked_operations: list[str] = []
    entity_counts: dict[str, int] = {}


class ReleaseHealthResponse(BaseModel):
    status: str
    version: str
    db_accessible: bool
    safety_boundaries_locked: bool
    safety_boundaries: dict[str, Any] = {}


class DemoSeedResponse(BaseModel):
    seeded: bool
    tenant_id: str
    tenant_name: str
    tenant_environment: str
    skill_id: str
    skill_name: str
    operator_session_id: str
    operator_session_step: str
    safety_invariants: dict[str, Any] = {}
    next_steps: list[str] = []


class SmokeCheckResponse(BaseModel):
    name: str
    passed: bool
    detail: str


class OperatorSmokeResponse(BaseModel):
    smoke_status: str
    checks_passed: int
    checks_total: int
    checks: list[SmokeCheckResponse] = []
    safety_invariants: dict[str, Any] = {}


class SafetyBoundariesResponse(BaseModel):
    safety_boundaries: dict[str, Any] = {}
    blocked_operations: list[str] = []
    allowed_r1_models: list[str] = []
    allowed_r2_models: list[str] = []
    allowed_r2_fields: list[str] = []
    allowed_environments: list[str] = []
    notes: list[str] = []
