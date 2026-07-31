"""Spec 92 Workstream B: `CanaryRouterService` -- policy lifecycle, deterministic
routing, safety incidents, dashboard. Approval reuses `ApprovalService`/
`Approval` exactly like `RecommendationService` does (same
creator-cannot-approve-own rule, same scope-binding idiom).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from erpguard.db.model_packages.canary import CanaryPolicy, CanaryRoutingDecision, CanarySafetyIncident
from erpguard.db.model_packages.execution import Approval
from erpguard.db.model_packages.skill_package import SkillPackage
from erpguard.domain.canary import metrics
from erpguard.domain.canary.routing import compute_bucket, select_lane
from erpguard.domain.execution.kill_switch_service import KillSwitchService
from erpguard.domain.processes.candidate_integrity import stable_digest


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _dump(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _run_amount(run) -> float:
    """Best-effort amount for a run, used for cumulative-amount tracking
    (Spec 92 Sec 9.6's `maximum_total_amount` safety pause). `ExecutionRun`
    has no dedicated amount column -- confirmation runs carry it in the
    bound state snapshot; pricing-scenario (and other line-based) runs
    carry it as `quantity * price_unit` per line in the capability payload."""

    try:
        payload = json.loads(run.action_plan_json).get("capability_payload", {})
    except (json.JSONDecodeError, TypeError, AttributeError):
        return 0.0
    lines = payload.get("lines")
    if isinstance(lines, list) and lines:
        total = 0.0
        for line in lines:
            try:
                total += float(line.get("quantity", 0)) * float(line.get("price_unit", 0))
            except (TypeError, ValueError):
                continue
        return total
    try:
        state_snapshot = json.loads(run.state_snapshot_json or "{}")
        return float(state_snapshot.get("amount_total") or 0)
    except (json.JSONDecodeError, TypeError, ValueError):
        return 0.0


class CanaryPolicyNotFound(KeyError):
    pass


class CanaryValidationError(ValueError):
    pass


class CanaryApprovalRejected(CanaryValidationError):
    pass


class CanaryTransitionError(CanaryValidationError):
    pass


_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"approved", "aborted"},
    "approved": {"active", "aborted"},
    "active": {"paused", "completed", "aborted"},
    "paused": {"active", "aborted"},
    "completed": set(),
    "aborted": set(),
}


class CanaryRouterService:
    def __init__(self, session: Session):
        self.session = session

    def _get(self, *, tenant_id: str, policy_id: str) -> CanaryPolicy:
        row = self.session.query(CanaryPolicy).filter_by(tenant_id=tenant_id, id=policy_id).one_or_none()
        if row is None:
            raise CanaryPolicyNotFound(policy_id)
        return row

    def get(self, *, tenant_id: str, policy_id: str) -> CanaryPolicy:
        return self._get(tenant_id=tenant_id, policy_id=policy_id)

    @staticmethod
    def approval_scope(policy: CanaryPolicy) -> str:
        return f"canary_policy:{policy.id}:approve:{policy.content_hash}"

    def _require_transition(self, *, current: str, target: str) -> None:
        if target not in _TRANSITIONS.get(current, set()):
            raise CanaryTransitionError(f"cannot_transition_from:{current}:to:{target}")

    def create_policy(
        self,
        *,
        tenant_id: str,
        process_key: str,
        stable_skill_package_id: str,
        canary_skill_package_id: str,
        shadow_deployment_id: str,
        percentage_basis_points: int,
        maximum_cases: int,
        maximum_total_amount: float,
        allowed_capabilities: list[str],
        maximum_amount: float,
        created_by: str,
        company_ids: list[int] | None = None,
        minimum_amount: float = 0.0,
        object_types: list[str] | None = None,
        safety_thresholds: dict | None = None,
    ) -> CanaryPolicy:
        candidate = (
            self.session.query(SkillPackage)
            .filter_by(tenant_id=tenant_id, id=canary_skill_package_id)
            .one_or_none()
        )
        if candidate is None or candidate.status != "canary":
            raise CanaryValidationError("canary_skill_package_must_be_in_canary_status")
        stable = (
            self.session.query(SkillPackage)
            .filter_by(tenant_id=tenant_id, id=stable_skill_package_id)
            .one_or_none()
        )
        if stable is None or stable.status != "active":
            raise CanaryValidationError("stable_skill_package_must_be_current_active_package")
        if not (0 <= percentage_basis_points <= 10000):
            raise CanaryValidationError("percentage_basis_points_out_of_range")

        content = {
            "process_key": process_key,
            "stable_skill_package_id": stable_skill_package_id,
            "canary_skill_package_id": canary_skill_package_id,
            "shadow_deployment_id": shadow_deployment_id,
            "percentage_basis_points": percentage_basis_points,
        }
        row = CanaryPolicy(
            id=f"canarypolicy_{uuid4().hex}",
            tenant_id=tenant_id,
            process_key=process_key,
            stable_skill_package_id=stable_skill_package_id,
            canary_skill_package_id=canary_skill_package_id,
            shadow_deployment_id=shadow_deployment_id,
            status="draft",
            percentage_basis_points=percentage_basis_points,
            maximum_cases=maximum_cases,
            maximum_total_amount=maximum_total_amount,
            allowed_capabilities_json=_dump(sorted(allowed_capabilities)),
            company_ids_json=_dump(sorted(company_ids or [])),
            minimum_amount=minimum_amount,
            maximum_amount=maximum_amount,
            object_types_json=_dump(sorted(object_types or [])),
            safety_thresholds_json=_dump(safety_thresholds or {}),
            content_hash=stable_digest(content),
            created_by=created_by,
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def approve_policy(self, *, tenant_id: str, policy_id: str, approval_id: str, approver_actor_id: str) -> CanaryPolicy:
        row = self._get(tenant_id=tenant_id, policy_id=policy_id)
        self._require_transition(current=row.status, target="approved")

        approval = self.session.query(Approval).filter_by(tenant_id=tenant_id, id=approval_id).one_or_none()
        if approval is None:
            raise CanaryApprovalRejected("approval_not_found")
        if approval.used_at is not None:
            raise CanaryApprovalRejected("approval_already_used")
        if approval.actor_id == row.created_by:
            raise CanaryApprovalRejected("policy_creator_cannot_be_sole_approver")
        if approval.actor_id != approver_actor_id:
            raise CanaryApprovalRejected("approval_actor_mismatch")
        if approval.scope != self.approval_scope(row):
            raise CanaryApprovalRejected("approval_scope_mismatch")

        approval.used_at = _utc_now()
        approval.used_by_run_id = row.id
        row.status = "approved"
        row.approved_by = approver_actor_id
        self.session.commit()
        self.session.refresh(row)
        return row

    def activate(self, *, tenant_id: str, policy_id: str) -> CanaryPolicy:
        row = self._get(tenant_id=tenant_id, policy_id=policy_id)
        self._require_transition(current=row.status, target="active")

        existing_active = (
            self.session.query(CanaryPolicy)
            .filter_by(tenant_id=tenant_id, process_key=row.process_key, status="active")
            .one_or_none()
        )
        if existing_active is not None:
            raise CanaryValidationError("another_canary_policy_already_active_for_process")

        row.status = "active"
        row.activated_at = _utc_now()
        self.session.commit()
        self.session.refresh(row)
        return row

    def pause(self, *, tenant_id: str, policy_id: str) -> CanaryPolicy:
        row = self._get(tenant_id=tenant_id, policy_id=policy_id)
        self._require_transition(current=row.status, target="paused")
        row.status = "paused"
        row.paused_at = _utc_now()
        self.session.commit()
        self.session.refresh(row)
        return row

    def resume(self, *, tenant_id: str, policy_id: str) -> CanaryPolicy:
        row = self._get(tenant_id=tenant_id, policy_id=policy_id)
        self._require_transition(current=row.status, target="active")
        row.status = "active"
        self.session.commit()
        self.session.refresh(row)
        return row

    def complete(self, *, tenant_id: str, policy_id: str) -> CanaryPolicy:
        row = self._get(tenant_id=tenant_id, policy_id=policy_id)
        self._require_transition(current=row.status, target="completed")
        row.status = "completed"
        row.completed_at = _utc_now()
        self.session.commit()
        self.session.refresh(row)
        return row

    def abort(self, *, tenant_id: str, policy_id: str) -> CanaryPolicy:
        row = self._get(tenant_id=tenant_id, policy_id=policy_id)
        self._require_transition(current=row.status, target="aborted")
        row.status = "aborted"
        row.aborted_at = _utc_now()
        self.session.commit()
        self.session.refresh(row)
        return row

    def _active_policy(self, *, tenant_id: str, process_key: str) -> CanaryPolicy | None:
        return (
            self.session.query(CanaryPolicy)
            .filter_by(tenant_id=tenant_id, process_key=process_key, status="active")
            .one_or_none()
        )

    def _consumed(self, *, tenant_id: str, policy_id: str) -> tuple[int, float]:
        from erpguard.db.model_packages.execution import ExecutionRun

        decisions = (
            self.session.query(CanaryRoutingDecision)
            .filter_by(tenant_id=tenant_id, canary_policy_id=policy_id, selected_lane="canary")
            .filter(CanaryRoutingDecision.execution_run_id.isnot(None))
            .all()
        )
        run_ids = [row.execution_run_id for row in decisions]
        runs = (
            self.session.query(ExecutionRun).filter(ExecutionRun.id.in_(run_ids)).all() if run_ids else []
        )
        return len(decisions), sum(_run_amount(run) for run in runs)

    def route(
        self,
        *,
        tenant_id: str,
        process_key: str,
        business_object_key: str,
        object_type: str | None = None,
        company_id: int | None = None,
        capability: str | None = None,
        amount: float | None = None,
        execution_run_id: str | None = None,
    ) -> CanaryRoutingDecision:
        routing_context_hash = stable_digest(
            {
                "business_object_key": business_object_key,
                "object_type": object_type,
                "company_id": company_id,
                "capability": capability,
                "amount": str(amount) if amount is not None else None,
            }
        )

        if KillSwitchService(self.session).is_active(tenant_id=tenant_id):
            return self._persist_decision(
                tenant_id=tenant_id, policy=None, process_key=process_key,
                business_object_key=business_object_key, routing_context_hash=routing_context_hash,
                bucket=None, lane="blocked", reason="kill_switch",
                selected_skill_package_id=None, execution_run_id=execution_run_id,
            )

        policy = self._active_policy(tenant_id=tenant_id, process_key=process_key)
        if policy is None:
            return self._persist_decision(
                tenant_id=tenant_id, policy=None, process_key=process_key,
                business_object_key=business_object_key, routing_context_hash=routing_context_hash,
                bucket=None, lane="stable", reason="policy_not_active",
                selected_skill_package_id=None, execution_run_id=execution_run_id,
            )

        allowed_capabilities = json.loads(policy.allowed_capabilities_json)
        company_ids = json.loads(policy.company_ids_json)
        object_types = json.loads(policy.object_types_json)
        out_of_scope = (
            (allowed_capabilities and capability not in allowed_capabilities)
            or (company_ids and company_id not in company_ids)
            or (object_types and object_type not in object_types)
            or (amount is not None and not (policy.minimum_amount <= amount <= policy.maximum_amount))
        )
        if out_of_scope:
            return self._persist_decision(
                tenant_id=tenant_id, policy=policy, process_key=process_key,
                business_object_key=business_object_key, routing_context_hash=routing_context_hash,
                bucket=None, lane="stable", reason="outside_scope",
                selected_skill_package_id=policy.stable_skill_package_id, execution_run_id=execution_run_id,
            )

        canary_case_count, canary_amount_consumed = self._consumed(tenant_id=tenant_id, policy_id=policy.id)
        if canary_case_count >= policy.maximum_cases:
            return self._persist_decision(
                tenant_id=tenant_id, policy=policy, process_key=process_key,
                business_object_key=business_object_key, routing_context_hash=routing_context_hash,
                bucket=None, lane="stable", reason="maximum_cases_reached",
                selected_skill_package_id=policy.stable_skill_package_id, execution_run_id=execution_run_id,
            )
        if amount is not None and canary_amount_consumed + amount > policy.maximum_total_amount:
            return self._persist_decision(
                tenant_id=tenant_id, policy=policy, process_key=process_key,
                business_object_key=business_object_key, routing_context_hash=routing_context_hash,
                bucket=None, lane="stable", reason="maximum_amount_reached",
                selected_skill_package_id=policy.stable_skill_package_id, execution_run_id=execution_run_id,
            )

        bucket = compute_bucket(
            tenant_id=tenant_id, canary_policy_id=policy.id, process_key=process_key,
            business_object_key=business_object_key,
        )
        lane = select_lane(bucket=bucket, percentage_basis_points=policy.percentage_basis_points)
        selected = policy.canary_skill_package_id if lane == "canary" else policy.stable_skill_package_id
        reason = "hash_selected_canary" if lane == "canary" else "hash_selected_stable"
        return self._persist_decision(
            tenant_id=tenant_id, policy=policy, process_key=process_key,
            business_object_key=business_object_key, routing_context_hash=routing_context_hash,
            bucket=bucket, lane=lane, reason=reason, selected_skill_package_id=selected,
            execution_run_id=execution_run_id,
        )

    def _persist_decision(
        self, *, tenant_id, policy, process_key, business_object_key, routing_context_hash, bucket, lane, reason,
        selected_skill_package_id, execution_run_id=None,
    ) -> CanaryRoutingDecision:
        row = CanaryRoutingDecision(
            id=f"canaryroute_{uuid4().hex}",
            tenant_id=tenant_id,
            canary_policy_id=policy.id if policy is not None else None,
            process_key=process_key,
            business_object_key=business_object_key,
            routing_context_hash=routing_context_hash,
            bucket=bucket,
            selected_lane=lane,
            stable_skill_package_id=policy.stable_skill_package_id if policy is not None else None,
            canary_skill_package_id=policy.canary_skill_package_id if policy is not None else None,
            selected_skill_package_id=selected_skill_package_id,
            selection_reason=reason,
            execution_run_id=execution_run_id,
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def record_incident(
        self, *, tenant_id: str, policy_id: str, incident_type: str, severity: str, details: dict,
        routing_decision_id: str | None = None, execution_run_id: str | None = None,
        evidence_pack_id: str | None = None,
    ) -> CanarySafetyIncident:
        policy = self._get(tenant_id=tenant_id, policy_id=policy_id)
        row = CanarySafetyIncident(
            id=f"canaryincident_{uuid4().hex}",
            tenant_id=tenant_id,
            canary_policy_id=policy_id,
            routing_decision_id=routing_decision_id,
            execution_run_id=execution_run_id,
            incident_type=incident_type,
            severity=severity,
            details_json=_dump(details),
            evidence_pack_id=evidence_pack_id,
        )
        self.session.add(row)
        if severity == "critical" and policy.status == "active":
            policy.status = "paused"
            policy.paused_at = _utc_now()
        self.session.commit()
        self.session.refresh(row)
        return row

    def resolve_incident(
        self, *, tenant_id: str, incident_id: str, resolved_by: str, resolution_notes: str
    ) -> CanarySafetyIncident:
        row = self.session.query(CanarySafetyIncident).filter_by(tenant_id=tenant_id, id=incident_id).one_or_none()
        if row is None:
            raise CanaryPolicyNotFound(incident_id)
        row.resolved_at = _utc_now()
        row.resolved_by = resolved_by
        row.resolution_notes = resolution_notes
        self.session.commit()
        self.session.refresh(row)
        return row

    def list_routing_decisions(self, *, tenant_id: str, policy_id: str) -> list[CanaryRoutingDecision]:
        return (
            self.session.query(CanaryRoutingDecision)
            .filter_by(tenant_id=tenant_id, canary_policy_id=policy_id)
            .order_by(CanaryRoutingDecision.created_at.asc())
            .all()
        )

    def list_incidents(self, *, tenant_id: str, policy_id: str) -> list[CanarySafetyIncident]:
        return (
            self.session.query(CanarySafetyIncident)
            .filter_by(tenant_id=tenant_id, canary_policy_id=policy_id)
            .order_by(CanarySafetyIncident.created_at.asc())
            .all()
        )

    def dashboard(self, *, tenant_id: str, policy_id: str) -> dict:
        from erpguard.db.model_packages.execution import ExecutionRun

        policy = self._get(tenant_id=tenant_id, policy_id=policy_id)
        decisions = self.list_routing_decisions(tenant_id=tenant_id, policy_id=policy_id)
        stable_count = sum(1 for row in decisions if row.selected_lane == "stable")
        canary_count = sum(1 for row in decisions if row.selected_lane == "canary")

        run_ids = [row.execution_run_id for row in decisions if row.execution_run_id]
        runs = (
            self.session.query(ExecutionRun).filter(ExecutionRun.id.in_(run_ids)).all()
            if run_ids
            else []
        )
        succeeded_count = sum(1 for run in runs if run.status == "succeeded")
        blocked_count = sum(1 for run in runs if run.status == "blocked")
        failed_count = sum(1 for run in runs if run.status in {"failed", "unknown"})
        postcondition_failure_count = sum(
            1 for run in runs if run.status == "succeeded" and "verification_failed" in (run.verification_result_json or "")
        )
        unexpected_side_effect_count = sum(
            1 for run in runs if "forbidden_effect_observed" in (run.verification_result_json or "")
        )
        cumulative_amount = sum(_run_amount(run) for run in runs)

        incidents = self.list_incidents(tenant_id=tenant_id, policy_id=policy_id)
        unresolved_incidents = sum(1 for row in incidents if row.resolved_at is None)
        reviewed_incidents = len(incidents) - unresolved_incidents

        return metrics.build_dashboard(
            stable_count=stable_count,
            canary_count=canary_count,
            succeeded_count=succeeded_count,
            blocked_count=blocked_count,
            failed_count=failed_count,
            postcondition_failure_count=postcondition_failure_count,
            unexpected_side_effect_count=unexpected_side_effect_count,
            cumulative_amount=cumulative_amount,
            estimated_opportunity_value=None,
            reviewed_incidents=reviewed_incidents,
            unresolved_incidents=unresolved_incidents,
            minimum_cases=10,
        ) | {"policy_id": policy.id, "policy_status": policy.status}
