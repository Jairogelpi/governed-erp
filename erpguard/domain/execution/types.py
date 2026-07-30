"""Execution Permit runtime shapes (master spec section 19 / Phase 15).

Modeled as a "Run" (spec 23.7's `/v1/runs/*` API family) that carries an
`ActionPlan` and, once approved, an `ExecutionPermit`. State machine:
`planned -> approved -> executed`, or `revoked` at any point before
`executed`. `executed` here means "verification passed and the connector
was called" -- FakeConnector always returns `status="blocked"` by design
(execution is hard-disabled in this codebase), so `executed` never means a
write happened.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

CheckStatus = Literal["passed", "failed", "not_checked"]


class ExecutionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ActionPlan(ExecutionModel):
    """Spec 19.2. `resolved_objects`/`predicted_effects`/`ambiguities` are
    only as rich as the compiled SkillPackage already declares -- this
    codebase has no live entity-resolution engine to enrich them further.
    """

    actor_id: str
    process_version_id: str
    skill_version_id: str
    connector_id: str
    connection_id: str
    capability: str
    canonical_capabilities: list[str] = Field(default_factory=list)
    resolved_objects: list[str] = Field(default_factory=list)
    predicted_effects: list[dict[str, Any]] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    risk: str = "unknown"
    idempotency_key: str
    # Business arguments the capability needs at execution time (e.g. a
    # Phase 16 quote.create_draft's partner_id/lines/client_reference).
    # Only as rich as the caller supplies at plan() time -- this codebase
    # has no live entity-resolution engine to derive it independently.
    capability_payload: dict[str, Any] = Field(default_factory=dict)


class CheckResult(ExecutionModel):
    name: str
    status: CheckStatus
    detail: str = ""


class PermitVerificationResult(ExecutionModel):
    """One entry per spec 19.4 rejection reason. `unsupported_fingerprint`
    is always `not_checked` -- no connector-agnostic fingerprint-requirement
    schema exists anywhere in this codebase (same gap Phase 14 documented).
    """

    checks: list[CheckResult] = Field(default_factory=list)

    @property
    def all_real_checks_passed(self) -> bool:
        return all(item.status != "failed" for item in self.checks)


class ExecutionPermit(ExecutionModel):
    """Spec 19.3, full field list."""

    permit_id: str
    tenant_id: str
    actor_id: str
    connection_id: str
    connector_id: str
    process_version_id: str
    skill_version_id: str
    operation_hash: str
    native_plan_hash: str
    state_snapshot_hash: str
    capability_allowlist: list[str]
    approval_ids: list[str]
    idempotency_key: str
    issued_at: str
    expires_at: str
    single_use: bool = True
    signature: str
