"""Execution Permit runtime service (master spec section 19 / Phase 15).

A "Run" (`ExecutionRun` row) carries the permit through
`planned -> approved -> succeeded|blocked|failed|unknown`, or `revoked`. `plan()` builds the
ActionPlan and computes the reproducible hashes; `approve()` binds
approvals, signs the permit content, and sets its expiry (this is the
moment spec 19.1 calls "issue ExecutionPermit"); `execute()` re-verifies
every spec 19.4 item against current state -- not just trusting
plan/approve-time validity, which is the actual point of the "altered,
expired and reused permits fail" exit criterion -- then calls the
connector.

Phase 17 makes terminal status describe the actual outcome. A connector
block is ``blocked``; verified postconditions are ``succeeded``; a known
postcondition failure is ``failed``; and an indeterminate transport outcome
is ``unknown``.

Generic capabilities retain ``unsupported_fingerprint=not_checked``.
Phase 17.1 governed confirmation instead verifies a bounded Odoo automation
fingerprint that is part of the signed control contract.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import xmlrpc.client
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from erpguard.application.connectors.service import ConnectorApplicationService
from erpguard.config import settings
from erpguard.connectors.sdk.models import (
    CanonicalOperation,
    ExecutionPermit as SdkExecutionPermit,
    NativeExecutionResult,
    NativeExecutionPlan,
)
from erpguard.db.model_packages.connections import UnifiedConnection
from erpguard.db.model_packages.execution import Approval, ExecutionRun
from erpguard.db.model_packages.skill_package import SkillPackage
from erpguard.domain.deployment.service import SkillDeploymentService
from erpguard.domain.execution.approval_service import ApprovalService
from erpguard.domain.execution.kill_switch_service import KillSwitchService
from erpguard.domain.execution.types import ActionPlan, CheckResult, PermitVerificationResult
from erpguard.domain.execution.side_effects import (
    ConfirmationControlContract,
    SideEffectEvaluation,
    materialize_compensation_plan,
)
from erpguard.domain.processes.candidate_integrity import stable_digest


class RunNotFound(KeyError):
    pass


class RunValidationError(ValueError):
    """Base for every plan/approve-time rejection."""


class SkillNotActive(RunValidationError):
    pass


class NoActiveSkillForProcess(RunValidationError):
    pass


class WrongConnection(RunValidationError):
    pass


class WrongCapability(RunValidationError):
    pass


class WrongActor(RunValidationError):
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


class RunStateChanged(RunVerificationError):
    pass


class EvidenceNotAvailable(RunValidationError):
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
        "control_contract_hash": row.control_contract_hash,
        "capability_allowlist_json": row.capability_allowlist_json,
        "approval_ids_json": row.approval_ids_json,
        "idempotency_key": row.idempotency_key,
        "expires_at": _as_utc_iso(row.expires_at),
    }
    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hmac.new(_signing_secret().encode(), payload_bytes, hashlib.sha256).hexdigest()


def _safe_execution_error(exc: Exception) -> str:
    """Retain a bounded business error without persisting RPC tracebacks."""

    if isinstance(exc, xmlrpc.client.Fault):
        lines = [line.strip() for line in exc.faultString.splitlines() if line.strip()]
        final_line = lines[-1] if lines else "odoo_xmlrpc_fault"
        return f"Fault:{final_line[:500]}"
    return type(exc).__name__


_EXECUTABLE_STATUSES = {"approved", "canary", "active"}


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

    @staticmethod
    def _is_governed_confirmation(capability: str) -> bool:
        return capability == "sales.order.confirm"

    @staticmethod
    def required_approval_scope(row: ExecutionRun) -> str | None:
        if row.capability != "sales.order.confirm":
            return None
        return (
            f"run:{row.id}:sales.order.confirm:"
            f"{row.state_snapshot_hash}:{row.control_contract_hash}"
        )

    def _connector_for_row(self, row: ExecutionRun):
        app_service = ConnectorApplicationService(self.session)
        connector = app_service.registry.get(row.connector_id)
        _, context = app_service.connection_context(
            tenant_id=row.tenant_id,
            connection_id=row.connection_id,
            connector_id=row.connector_id,
        )
        return connector, context

    def _confirmation_snapshot(self, row: ExecutionRun) -> dict:
        connector, context = self._connector_for_row(row)
        snapshot_method = getattr(connector, "governed_confirmation_snapshot", None)
        if snapshot_method is None:
            raise RunValidationError("connector_missing_governed_confirmation_snapshot")
        plan = ActionPlan.model_validate(json.loads(row.action_plan_json))
        operation = CanonicalOperation(capability=row.capability, arguments=plan.capability_payload)
        try:
            return snapshot_method(context, operation)
        except (LookupError, ValueError) as exc:
            raise RunValidationError(str(exc)) from exc

    def _confirmation_control_contract(
        self,
        row: ExecutionRun,
        snapshot: dict,
    ) -> ConfirmationControlContract:
        connector, context = self._connector_for_row(row)
        contract_method = getattr(connector, "governed_confirmation_control_contract", None)
        if contract_method is None:
            raise RunValidationError("connector_missing_confirmation_control_contract")
        plan = ActionPlan.model_validate(json.loads(row.action_plan_json))
        operation = CanonicalOperation(capability=row.capability, arguments=plan.capability_payload)
        return ConfirmationControlContract.model_validate(
            contract_method(context, operation, snapshot)
        )

    def plan(
        self,
        *,
        tenant_id: str,
        actor_id: str,
        connection_id: str,
        skill_package_id: str | None = None,
        process_key: str | None = None,
        capability: str,
        idempotency_key: str,
        capability_payload: dict | None = None,
    ) -> ExecutionRun:
        if skill_package_id is None:
            if process_key is None:
                raise RunValidationError("skill_package_id_or_process_key_required")
            active = SkillDeploymentService(self.session).get_active(
                tenant_id=tenant_id, process_key=process_key
            )
            if active is None:
                raise NoActiveSkillForProcess(f"no_active_skill_for_process:{process_key}")
            skill_package_id = active.id

        assert skill_package_id is not None
        skill_package = self._get_skill_package(tenant_id=tenant_id, skill_package_id=skill_package_id)
        if skill_package.status not in _EXECUTABLE_STATUSES:
            raise SkillNotActive("inactive_skill")

        connection = self._get_connection(tenant_id=tenant_id, connection_id=connection_id)
        if connection.connector_type != skill_package.connector_id:
            raise WrongConnection("connection_connector_mismatch")

        if not self._capability_allowed(skill_package, capability):
            raise WrongCapability(f"capability_not_in_skill_package:{capability}")

        if KillSwitchService(self.session).is_active(tenant_id=tenant_id):
            raise KillSwitchActive("kill_switch_active")

        app_service = ConnectorApplicationService(self.session)
        connector = app_service.registry.get(skill_package.connector_id)
        _, context = app_service.connection_context(
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector_id=skill_package.connector_id,
        )
        operation = CanonicalOperation(capability=capability, arguments=capability_payload or {})
        native_plan = asyncio.run(connector.plan_capability(context, operation))
        if native_plan.status != "planned" or (
            self._is_governed_confirmation(capability) and not native_plan.supports_execution
        ):
            raise WrongCapability(f"capability_execution_not_supported:{capability}")

        live_snapshot: dict = {}
        control_contract: ConfirmationControlContract | None = None
        predicted_effects: list[dict] = []
        resolved_objects: list[str] = []
        risk = "unknown"
        if self._is_governed_confirmation(capability):
            snapshot_method = getattr(connector, "governed_confirmation_snapshot", None)
            preflight_method = getattr(connector, "governed_confirmation_preflight", None)
            contract_method = getattr(connector, "governed_confirmation_control_contract", None)
            if snapshot_method is None or preflight_method is None or contract_method is None:
                raise RunValidationError("connector_missing_governed_confirmation_contract")
            try:
                live_snapshot = snapshot_method(context, operation)
            except (LookupError, ValueError) as exc:
                raise RunValidationError(str(exc)) from exc
            control_contract = ConfirmationControlContract.model_validate(
                contract_method(context, operation, live_snapshot)
            )
            preflight = preflight_method(
                context,
                operation,
                live_snapshot,
                control_contract.model_dump(mode="json"),
            )
            if preflight.get("status") != "passed":
                issues = ",".join(preflight.get("issues", [])) or "confirmation_preflight_failed"
                raise RunValidationError(issues)
            predicted_effects = list(preflight.get("predicted_effects", []))
            resolved_objects = [f"sale.order:{live_snapshot.get('order_id')}"]
            risk = "R3"

        plan = ActionPlan(
            actor_id=actor_id,
            process_version_id=f"{skill_package.process_key}:{skill_package.candidate_version}",
            skill_version_id=skill_package.id,
            connector_id=skill_package.connector_id,
            connection_id=connection_id,
            capability=capability,
            canonical_capabilities=[capability],
            resolved_objects=resolved_objects,
            predicted_effects=predicted_effects,
            risk=risk,
            idempotency_key=idempotency_key,
            capability_payload=capability_payload or {},
        )
        operation_hash = stable_digest(plan.model_dump(mode="json"))
        state_snapshot = (
            live_snapshot
            if live_snapshot
            else {"skill_package_id": skill_package.id, "package_hash": skill_package.package_hash}
        )
        state_snapshot_hash = stable_digest(state_snapshot)
        control_contract_json = (
            json.dumps(
                control_contract.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
            )
            if control_contract is not None
            else "{}"
        )
        control_contract_hash = control_contract.digest if control_contract is not None else ""

        existing = (
            self.session.query(ExecutionRun)
            .filter_by(tenant_id=tenant_id, idempotency_key=idempotency_key)
            .order_by(ExecutionRun.created_at.desc())
            .first()
        )
        if existing is not None:
            if existing.operation_hash == operation_hash and (
                not self._is_governed_confirmation(capability)
                or (
                    existing.state_snapshot_hash == state_snapshot_hash
                    and existing.control_contract_hash == control_contract_hash
                )
            ):
                return existing
            raise IdempotencyConflict("idempotency_key_reused_for_different_operation")

        if self._is_governed_confirmation(capability):
            native_plan = native_plan.model_copy(
                update={
                    "arguments": {
                        **native_plan.arguments,
                        "expected_state_snapshot_hash": state_snapshot_hash,
                        "expected_control_contract_hash": control_contract_hash,
                        "control_contract": (
                            control_contract.model_dump(mode="json")
                            if control_contract is not None
                            else {}
                        ),
                    }
                }
            )
        native_plan_json = json.dumps(
            native_plan.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        )
        native_plan_hash = stable_digest(native_plan.model_dump(mode="json"))

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
            native_plan_json=native_plan_json,
            state_snapshot_json=json.dumps(state_snapshot, sort_keys=True, separators=(",", ":")),
            operation_hash=operation_hash,
            native_plan_hash=native_plan_hash,
            state_snapshot_hash=state_snapshot_hash,
            control_contract_json=control_contract_json,
            control_contract_hash=control_contract_hash,
            idempotency_key=idempotency_key,
            status="planned",
            cleanup_plan_json=json.dumps(
                (
                    connector.governed_confirmation_cleanup_plan(
                        live_snapshot,
                        control_contract.model_dump(mode="json") if control_contract is not None else None,
                    )
                    if self._is_governed_confirmation(capability)
                    and hasattr(connector, "governed_confirmation_cleanup_plan")
                    else {}
                ),
                sort_keys=True,
                separators=(",", ":"),
            ),
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

    def approve(
        self,
        *,
        tenant_id: str,
        run_id: str,
        approval_ids: list[str],
        approver_actor_id: str | None = None,
        ttl_seconds: int = 900,
    ) -> ExecutionRun:
        row = self.get(tenant_id=tenant_id, run_id=run_id)
        if row.status != "planned":
            raise RunValidationError(f"run_not_plannable:{row.status}")

        skill_package = self._get_skill_package(tenant_id=tenant_id, skill_package_id=row.skill_package_id)
        if skill_package.status not in _EXECUTABLE_STATUSES:
            raise SkillNotActive("inactive_skill")
        if KillSwitchService(self.session).is_active(tenant_id=tenant_id):
            raise KillSwitchActive("kill_switch_active")
        if ttl_seconds < 1 or ttl_seconds > 900:
            raise RunValidationError("permit_ttl_must_be_between_1_and_900_seconds")

        governed_confirmation = self._is_governed_confirmation(row.capability)
        if governed_confirmation:
            if not approval_ids:
                raise RunValidationError("confirmation_requires_independent_approval")
            current_snapshot = self._confirmation_snapshot(row)
            if stable_digest(current_snapshot) != row.state_snapshot_hash:
                raise RunStateChanged("state_changed_before_approval")
            current_contract = self._confirmation_control_contract(row, current_snapshot)
            if current_contract.digest != row.control_contract_hash:
                raise RunStateChanged("control_contract_changed_before_approval")

        approvals: list[Approval] = []
        expected_scope = self.required_approval_scope(row)
        for approval_id in approval_ids:
            approval = ApprovalService(self.session).get(tenant_id=tenant_id, approval_id=approval_id)
            if approval.used_at is not None:
                raise ApprovalAlreadyUsed(f"approval_already_used:{approval_id}")
            if governed_confirmation:
                if approval.actor_id == row.actor_id:
                    raise RunValidationError("confirmation_approval_must_be_independent")
                if approver_actor_id is None or approval.actor_id != approver_actor_id:
                    raise RunValidationError("confirmation_approval_actor_mismatch")
                if approval.scope != expected_scope:
                    raise RunValidationError("confirmation_approval_scope_mismatch")
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
        if row.status in {"executed", "succeeded", "blocked", "failed", "unknown"}:
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

        if row.status in {"executed", "succeeded", "blocked", "failed", "unknown"}:
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
        if skill_package.status not in _EXECUTABLE_STATUSES:
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
        if self._is_governed_confirmation(row.capability):
            contract = ConfirmationControlContract.model_validate_json(row.control_contract_json)
            checks.append(
                CheckResult(
                    name="automation_fingerprint",
                    status="passed" if contract.automation_fingerprint.complete else "failed",
                    detail=f"digest={contract.automation_fingerprint.digest}",
                )
            )
        else:
            checks.append(
                CheckResult(
                    name="unsupported_fingerprint",
                    status="not_checked",
                    detail="no connector-agnostic fingerprint-requirement schema exists in this codebase",
                )
            )
        return PermitVerificationResult(checks=checks)

    def execute(
        self,
        *,
        tenant_id: str,
        run_id: str,
        executor_actor_id: str | None = None,
    ) -> ExecutionRun:
        row = self.get(tenant_id=tenant_id, run_id=run_id)
        if self._is_governed_confirmation(row.capability) and executor_actor_id != row.actor_id:
            raise WrongActor("confirmation_must_be_executed_by_planning_actor")
        verification = self._verify(row)  # raises on any real failure

        stored_plan = ActionPlan.model_validate(json.loads(row.action_plan_json))
        connector, context = self._connector_for_row(row)
        native_plan = NativeExecutionPlan.model_validate(json.loads(row.native_plan_json or "{}"))
        sdk_permit = SdkExecutionPermit(permit_id=row.id, capability=row.capability, approved=True)

        if self._is_governed_confirmation(row.capability):
            current_snapshot = self._confirmation_snapshot(row)
            if stable_digest(current_snapshot) != row.state_snapshot_hash:
                verification_payload: dict[str, Any] = {
                    "checks": [
                        *[c.model_dump(mode="json") for c in verification.checks],
                        CheckResult(
                            name="altered_state",
                            status="failed",
                            detail="live Odoo snapshot changed after approval",
                        ).model_dump(mode="json"),
                    ],
                    "connector_result": None,
                    "postcondition": None,
                    "current_state_snapshot": current_snapshot,
                }
                row.verification_result_json = json.dumps(
                    verification_payload, sort_keys=True, separators=(",", ":")
                )
                row.status = "blocked"
                row.executed_at = _utc_now()
                self._seal_evidence(row, verification_payload)
                self.session.commit()
                raise RunStateChanged("state_changed_since_approval")
            current_contract = self._confirmation_control_contract(row, current_snapshot)
            if current_contract.digest != row.control_contract_hash:
                verification_payload = {
                    "checks": [
                        *[c.model_dump(mode="json") for c in verification.checks],
                        CheckResult(
                            name="automation_fingerprint",
                            status="failed",
                            detail="control contract changed after approval",
                        ).model_dump(mode="json"),
                    ],
                    "connector_result": None,
                    "postcondition": None,
                    "current_control_contract_hash": current_contract.digest,
                }
                row.verification_result_json = json.dumps(
                    verification_payload, sort_keys=True, separators=(",", ":")
                )
                row.status = "blocked"
                row.executed_at = _utc_now()
                self._seal_evidence(row, verification_payload)
                self.session.commit()
                raise RunStateChanged("control_contract_changed_since_approval")

        execution_error: str | None = None
        try:
            result = asyncio.run(connector.execute_capability(context, native_plan, sdk_permit))
        except Exception as exc:  # transport timeout may occur after the ERP committed
            execution_error = _safe_execution_error(exc)
            payload: dict = {}
            if self._is_governed_confirmation(row.capability):
                try:
                    payload = {
                        "before": json.loads(row.state_snapshot_json),
                        "after": self._confirmation_snapshot(row),
                    }
                except (RunValidationError, json.JSONDecodeError):
                    payload = {}
            result = NativeExecutionResult(
                status="unknown",
                summary="connector_outcome_unknown_verification_required",
                payload=payload,
                errors=[execution_error],
            )

        operation = CanonicalOperation(
            capability=row.capability,
            arguments=stored_plan.capability_payload,
        )
        verify_result = asyncio.run(connector.verify_execution(context, operation, result))
        if result.status == "blocked":
            terminal_status = "blocked"
        elif verify_result.verified:
            terminal_status = "succeeded"
        elif result.status == "unknown":
            terminal_status = "unknown"
        else:
            terminal_status = "failed"

        verification_payload = {
            "checks": [c.model_dump(mode="json") for c in verification.checks],
            "connector_result": result.model_dump(mode="json"),
            "postcondition": verify_result.model_dump(mode="json"),
            "execution_error": execution_error,
        }
        if self._is_governed_confirmation(row.capability):
            evaluation_payload = verify_result.evidence.get("side_effect_evaluation")
            if evaluation_payload:
                evaluation = SideEffectEvaluation.model_validate(evaluation_payload)
                contract = ConfirmationControlContract.model_validate_json(row.control_contract_json)
                compensation = materialize_compensation_plan(
                    contract.compensation_plan,
                    evaluation,
                    json.loads(row.state_snapshot_json).get("order_id"),
                )
                row.cleanup_plan_json = json.dumps(
                    compensation.model_dump(mode="json"),
                    sort_keys=True,
                    separators=(",", ":"),
                )
        row.verification_result_json = json.dumps(
            verification_payload,
            sort_keys=True,
            separators=(",", ":"),
        )
        row.status = terminal_status
        row.executed_at = _utc_now()
        self._seal_evidence(row, verification_payload)
        self.session.commit()
        self.session.refresh(row)
        return row

    def _seal_evidence(self, row: ExecutionRun, verification_payload: dict) -> None:
        approvals = (
            self.session.query(Approval)
            .filter(Approval.id.in_(json.loads(row.approval_ids_json or "[]")))
            .order_by(Approval.id)
            .all()
        )
        evidence = {
            "schema_version": "erpguard.evidence.v1",
            "run_id": row.id,
            "tenant_id": row.tenant_id,
            "actor_id": row.actor_id,
            "connection_id": row.connection_id,
            "connector_id": row.connector_id,
            "capability": row.capability,
            "risk": "R3" if self._is_governed_confirmation(row.capability) else "unknown",
            "status": row.status,
            "action_plan": json.loads(row.action_plan_json),
            "native_plan": json.loads(row.native_plan_json or "{}"),
            "approved_state_snapshot": json.loads(row.state_snapshot_json or "{}"),
            "control_contract": json.loads(row.control_contract_json or "{}"),
            "hashes": {
                "operation_hash": row.operation_hash,
                "native_plan_hash": row.native_plan_hash,
                "state_snapshot_hash": row.state_snapshot_hash,
                "control_contract_hash": row.control_contract_hash,
            },
            "permit": {
                "single_use": row.single_use,
                "approval_ids": json.loads(row.approval_ids_json or "[]"),
                "approved_at": _as_utc_iso(row.approved_at),
                "expires_at": _as_utc_iso(row.expires_at),
                "signature": row.signature,
            },
            "approvals": [
                {
                    "id": approval.id,
                    "actor_id": approval.actor_id,
                    "scope": approval.scope,
                    "created_at": _as_utc_iso(approval.created_at),
                    "used_at": _as_utc_iso(approval.used_at),
                }
                for approval in approvals
            ],
            "verification": verification_payload,
            "cleanup_plan": json.loads(row.cleanup_plan_json or "{}"),
            "timestamps": {
                "created_at": _as_utc_iso(row.created_at),
                "approved_at": _as_utc_iso(row.approved_at),
                "executed_at": _as_utc_iso(row.executed_at),
            },
        }
        evidence["sealed_digest"] = stable_digest(evidence)
        row.evidence_pack_json = json.dumps(evidence, sort_keys=True, separators=(",", ":"))

    def get_evidence(self, *, tenant_id: str, run_id: str) -> dict:
        row = self.get(tenant_id=tenant_id, run_id=run_id)
        evidence = json.loads(row.evidence_pack_json or "{}")
        if not evidence:
            raise EvidenceNotAvailable("evidence_not_available_before_terminal_outcome")
        sealed_digest = evidence.pop("sealed_digest", None)
        if not sealed_digest or stable_digest(evidence) != sealed_digest:
            raise RunTampered("evidence_pack_tampered")
        evidence["sealed_digest"] = sealed_digest
        return evidence

    def get_cleanup_plan(self, *, tenant_id: str, run_id: str) -> dict:
        row = self.get(tenant_id=tenant_id, run_id=run_id)
        plan = json.loads(row.cleanup_plan_json or "{}")
        if not plan:
            raise RunValidationError("cleanup_plan_not_available")
        return plan
