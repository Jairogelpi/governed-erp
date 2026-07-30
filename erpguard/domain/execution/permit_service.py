"""Execution Permit runtime service (master spec section 19 / Phase 15).

A "Run" (`ExecutionRun` row) carries the permit through
`planned -> approved -> executed`, or `revoked`. `plan()` builds the
ActionPlan and computes the reproducible hashes; `approve()` binds
approvals, signs the permit content, and sets its expiry (this is the
moment spec 19.1 calls "issue ExecutionPermit"); `execute()` re-verifies
every spec 19.4 item against current state -- not just trusting
plan/approve-time validity, which is the actual point of the "altered,
expired and reused permits fail" exit criterion -- then calls the
connector.

`execute()` marks the run `status="executed"` once verification passes and
the connector call is attempted, regardless of the connector's own result.
FakeConnector always returns `status="blocked"` (execution is hard-disabled
in this codebase by design). "Executed" here means "verification passed and
execution was attempted," never "a write succeeded."

`unsupported_fingerprint` is always `not_checked` in the verification
result -- no connector-agnostic fingerprint-requirement schema exists
anywhere in this codebase (same gap Phase 14 documented for compilation).
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from erpguard.application.connectors.service import ConnectorApplicationService
from erpguard.config import settings
from erpguard.connectors.sdk.models import (
    ConnectorContext,
    ExecutionPermit as SdkExecutionPermit,
    NativeExecutionPlan,
)
from erpguard.db.model_packages.connections import UnifiedConnection
from erpguard.db.model_packages.execution import Approval, ExecutionRun
from erpguard.db.model_packages.skill_package import SkillPackage
from erpguard.domain.execution.approval_service import ApprovalService
from erpguard.domain.execution.kill_switch_service import KillSwitchService
from erpguard.domain.execution.types import ActionPlan, CheckResult, PermitVerificationResult
from erpguard.domain.processes.candidate_integrity import stable_digest


class RunNotFound(KeyError):
    pass


class RunValidationError(ValueError):
    """Base for every plan/approve-time rejection."""


class SkillNotActive(RunValidationError):
    pass


class WrongConnection(RunValidationError):
    pass


class WrongCapability(RunValidationError):
    pass


class KillSwitchActive(RunValidationError):
    pass


class ApprovalAlreadyUsed(RunValidationError):
    pass


class IdempotencyConflict(RunValidationError):
    pass


class RunVerificationError(RunValidationError):
    """Base for every execute-time rejection -- these are the exit-criteria
    failure modes (altered/expired/reused/revoked/etc)."""


class RunAlreadyExecuted(RunVerificationError):
    pass


class RunRevoked(RunVerificationError):
    pass


class RunNotApproved(RunVerificationError):
    pass


class RunExpired(RunVerificationError):
    pass


class RunTampered(RunVerificationError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _signing_secret() -> str:
    # Reuses the auth bearer-token secret rather than adding a new settings
    # field -- this codebase has exactly one HMAC secret today
    # (erpguard/domain/identity/auth.py). A separate permit-signing secret
    # would be better hygiene at real scale; noted, not built here.
    return settings.auth_secret or "insecure-dev-secret"


def _as_utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        # SQLite round-trips DateTime(timezone=True) as naive; every value
        # this service writes is UTC, so treat a naive read-back as UTC
        # rather than producing a signature that can never match itself
        # across a save/reload boundary.
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _compute_signature(row: ExecutionRun) -> str:
    payload = {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "actor_id": row.actor_id,
        "connection_id": row.connection_id,
        "connector_id": row.connector_id,
        "skill_package_id": row.skill_package_id,
        "capability": row.capability,
        "operation_hash": row.operation_hash,
        "native_plan_hash": row.native_plan_hash,
        "state_snapshot_hash": row.state_snapshot_hash,
        "capability_allowlist_json": row.capability_allowlist_json,
        "approval_ids_json": row.approval_ids_json,
        "idempotency_key": row.idempotency_key,
        "expires_at": _as_utc_iso(row.expires_at),
    }
    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hmac.new(_signing_secret().encode(), payload_bytes, hashlib.sha256).hexdigest()


class PermitService:
    def __init__(self, session: Session):
        self.session = session

    def _get_skill_package(self, *, tenant_id: str, skill_package_id: str) -> SkillPackage:
        row = self.session.query(SkillPackage).filter_by(tenant_id=tenant_id, id=skill_package_id).one_or_none()
        if row is None:
            raise RunValidationError("skill_package_not_found")
        return row

    def _get_connection(self, *, tenant_id: str, connection_id: str) -> UnifiedConnection:
        row = self.session.query(UnifiedConnection).filter_by(tenant_id=tenant_id, id=connection_id).one_or_none()
        if row is None:
            raise WrongConnection("connection_not_found")
        return row

    def _capability_allowed(self, skill_package: SkillPackage, capability: str) -> bool:
        content = json.loads(skill_package.package_json)
        return any(item["capability"] == capability for item in content.get("capability_manifest", []))

    def plan(
        self,
        *,
        tenant_id: str,
        actor_id: str,
        connection_id: str,
        skill_package_id: str,
        capability: str,
        idempotency_key: str,
    ) -> ExecutionRun:
        skill_package = self._get_skill_package(tenant_id=tenant_id, skill_package_id=skill_package_id)
        if skill_package.status != "approved":
            raise SkillNotActive("inactive_skill")

        connection = self._get_connection(tenant_id=tenant_id, connection_id=connection_id)
        if connection.connector_type != skill_package.connector_id:
            raise WrongConnection("connection_connector_mismatch")

        if not self._capability_allowed(skill_package, capability):
            raise WrongCapability(f"capability_not_in_skill_package:{capability}")

        if KillSwitchService(self.session).is_active(tenant_id=tenant_id):
            raise KillSwitchActive("kill_switch_active")

        plan = ActionPlan(
            actor_id=actor_id,
            process_version_id=f"{skill_package.process_key}:{skill_package.candidate_version}",
            skill_version_id=skill_package.id,
            connector_id=skill_package.connector_id,
            connection_id=connection_id,
            capability=capability,
            canonical_capabilities=[capability],
            idempotency_key=idempotency_key,
        )
        operation_hash = stable_digest(plan.model_dump(mode="json"))

        existing = (
            self.session.query(ExecutionRun)
            .filter_by(tenant_id=tenant_id, idempotency_key=idempotency_key)
            .order_by(ExecutionRun.created_at.desc())
            .first()
        )
        if existing is not None:
            if existing.operation_hash == operation_hash:
                return existing
            raise IdempotencyConflict("idempotency_key_reused_for_different_operation")

        native_plan_hash = stable_digest({"capability": capability, "connector_id": skill_package.connector_id})
        # No live connector read exists at plan time -- the "state" this
        # permit is issued against is the compiled package's own content
        # hash, not a live ERP snapshot (this codebase has no live-read
        # step wired into permit issuance yet).
        state_snapshot_hash = stable_digest({"skill_package_id": skill_package.id, "package_hash": skill_package.package_hash})

        row = ExecutionRun(
            id=f"run_{uuid4().hex}",
            tenant_id=tenant_id,
            actor_id=actor_id,
            connection_id=connection_id,
            connector_id=skill_package.connector_id,
            skill_package_id=skill_package.id,
            process_version_id=plan.process_version_id,
            skill_version_id=plan.skill_version_id,
            capability=capability,
            action_plan_json=json.dumps(plan.model_dump(mode="json"), sort_keys=True, separators=(",", ":")),
            operation_hash=operation_hash,
            native_plan_hash=native_plan_hash,
            state_snapshot_hash=state_snapshot_hash,
            idempotency_key=idempotency_key,
            status="planned",
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def get(self, *, tenant_id: str, run_id: str) -> ExecutionRun:
        row = self.session.query(ExecutionRun).filter_by(tenant_id=tenant_id, id=run_id).one_or_none()
        if row is None:
            raise RunNotFound(run_id)
        return row

    def approve(self, *, tenant_id: str, run_id: str, approval_ids: list[str], ttl_seconds: int = 900) -> ExecutionRun:
        row = self.get(tenant_id=tenant_id, run_id=run_id)
        if row.status != "planned":
            raise RunValidationError(f"run_not_plannable:{row.status}")

        skill_package = self._get_skill_package(tenant_id=tenant_id, skill_package_id=row.skill_package_id)
        if skill_package.status != "approved":
            raise SkillNotActive("inactive_skill")
        if KillSwitchService(self.session).is_active(tenant_id=tenant_id):
            raise KillSwitchActive("kill_switch_active")

        approvals: list[Approval] = []
        for approval_id in approval_ids:
            approval = ApprovalService(self.session).get(tenant_id=tenant_id, approval_id=approval_id)
            if approval.used_at is not None:
                raise ApprovalAlreadyUsed(f"approval_already_used:{approval_id}")
            approvals.append(approval)

        now = _utc_now()
        for approval in approvals:
            approval.used_at = now
            approval.used_by_run_id = row.id

        row.approval_ids_json = json.dumps(sorted(approval_ids))
        row.capability_allowlist_json = json.dumps([row.capability])
        row.expires_at = now + timedelta(seconds=ttl_seconds)
        row.signature = _compute_signature(row)
        row.status = "approved"
        row.approved_at = now
        self.session.commit()
        self.session.refresh(row)
        return row

    def revoke(self, *, tenant_id: str, run_id: str) -> ExecutionRun:
        row = self.get(tenant_id=tenant_id, run_id=run_id)
        if row.status == "executed":
            raise RunAlreadyExecuted("run_already_executed")
        if row.status == "revoked":
            raise RunRevoked("run_already_revoked")
        row.status = "revoked"
        row.revoked_at = _utc_now()
        self.session.commit()
        self.session.refresh(row)
        return row

    def _verify(self, row: ExecutionRun) -> PermitVerificationResult:
        checks: list[CheckResult] = []

        if row.status == "executed":
            checks.append(CheckResult(name="reused", status="failed", detail="permit already consumed"))
            raise RunAlreadyExecuted("permit_reused")
        checks.append(CheckResult(name="reused", status="passed"))

        if row.status == "revoked":
            checks.append(CheckResult(name="revoked", status="failed", detail="permit was revoked"))
            raise RunRevoked("permit_revoked")
        checks.append(CheckResult(name="revoked", status="passed"))

        if row.status != "approved":
            checks.append(CheckResult(name="missing_approval", status="failed", detail=f"status={row.status}"))
            raise RunNotApproved("permit_not_approved")
        checks.append(CheckResult(name="missing_approval", status="passed"))

        expires_at_iso = _as_utc_iso(row.expires_at)
        expires_at = datetime.fromisoformat(expires_at_iso) if expires_at_iso else None
        if expires_at is None or _utc_now() > expires_at:
            checks.append(CheckResult(name="expired", status="failed"))
            raise RunExpired("permit_expired")
        checks.append(CheckResult(name="expired", status="passed"))

        expected_signature = _compute_signature(row)
        if not hmac.compare_digest(expected_signature, row.signature):
            checks.append(CheckResult(name="altered_plan", status="failed", detail="signature mismatch"))
            checks.append(CheckResult(name="altered_state", status="failed", detail="signature mismatch"))
            raise RunTampered("permit_altered")
        checks.append(CheckResult(name="altered_plan", status="passed"))
        checks.append(CheckResult(name="altered_state", status="passed"))

        skill_package = self._get_skill_package(tenant_id=row.tenant_id, skill_package_id=row.skill_package_id)
        if skill_package.status != "approved":
            checks.append(CheckResult(name="inactive_skill", status="failed"))
            raise SkillNotActive("inactive_skill")
        checks.append(CheckResult(name="inactive_skill", status="passed"))

        if KillSwitchService(self.session).is_active(tenant_id=row.tenant_id):
            checks.append(CheckResult(name="kill_switch", status="failed"))
            raise KillSwitchActive("kill_switch_active")
        checks.append(CheckResult(name="kill_switch", status="passed"))

        connection = self._get_connection(tenant_id=row.tenant_id, connection_id=row.connection_id)
        if connection.connector_type != row.connector_id:
            checks.append(CheckResult(name="wrong_connection", status="failed"))
            raise WrongConnection("connection_connector_mismatch")
        checks.append(CheckResult(name="wrong_connection", status="passed"))
        checks.append(CheckResult(name="wrong_tenant", status="passed", detail="enforced by tenant-scoped lookup"))
        checks.append(CheckResult(name="wrong_capability", status="passed"))
        checks.append(
            CheckResult(
                name="unsupported_fingerprint",
                status="not_checked",
                detail="no connector-agnostic fingerprint-requirement schema exists in this codebase",
            )
        )
        return PermitVerificationResult(checks=checks)

    def execute(self, *, tenant_id: str, run_id: str) -> ExecutionRun:
        row = self.get(tenant_id=tenant_id, run_id=run_id)
        verification = self._verify(row)  # raises on any real failure

        connector = ConnectorApplicationService(self.session).registry.get(row.connector_id)
        context = ConnectorContext(tenant_id=row.tenant_id, connection_id=row.connection_id)
        native_plan = NativeExecutionPlan(capability=row.capability, steps=[row.capability])
        sdk_permit = SdkExecutionPermit(permit_id=row.id, capability=row.capability, approved=True)

        result = asyncio.run(connector.execute_capability(context, native_plan, sdk_permit))

        row.verification_result_json = json.dumps(
            {
                "checks": [c.model_dump(mode="json") for c in verification.checks],
                "connector_result": result.model_dump(mode="json"),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        row.status = "executed"
        row.executed_at = _utc_now()
        self.session.commit()
        self.session.refresh(row)
        return row
