"""Skill deployment lifecycle: canary -> active -> rollback (Phase 19, spec 18.4).

`SkillPackage.status` is the state; `SkillDeploymentEvent` is the append-only
audit trail of how it got there. "Active version" for a process is derived,
not stored: whichever `SkillPackage` row currently has `status == "active"`
for that `(tenant_id, process_key)` -- this service enforces there is ever
at most one.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from erpguard.db.model_packages.skill_deployment import SkillDeploymentEvent
from erpguard.db.model_packages.skill_package import SkillPackage
from erpguard.domain.shadow.service import ShadowNotFound, ShadowService


class SkillPackageNotFound(KeyError):
    pass


class CanaryNotEligible(ValueError):
    pass


class InvalidStatusTransition(ValueError):
    pass


class NoActiveSkillPackage(ValueError):
    pass


class CanaryPromotionNotEligible(InvalidStatusTransition):
    pass


class ConcurrentPromotionConflict(InvalidStatusTransition):
    """Raised when the database's partial-unique index (PostgreSQL --
    see migration 0028) rejects a second concurrent promotion to `active`
    for the same process. The check-then-insert query above can't see a
    same-instant concurrent writer; this is the real backstop."""


class SkillDeploymentService:
    def __init__(self, session: Session):
        self.session = session

    def _get(self, *, tenant_id: str, skill_id: str) -> SkillPackage:
        row = self.session.query(SkillPackage).filter_by(tenant_id=tenant_id, id=skill_id).one_or_none()
        if row is None:
            raise SkillPackageNotFound(skill_id)
        return row

    def _check_canary_policy_eligibility(self, *, tenant_id: str, skill_id: str) -> None:
        """Spec 92 Sec 9.9: if a `CanaryPolicy` names this package as its
        canary candidate, `canary` status alone is not enough to promote --
        the policy must be `completed`, with no unresolved critical
        incident and enough operational evidence. Packages promoted
        without ever having a canary policy (Phase 19's original path)
        are unaffected -- this check is a no-op when no policy exists."""

        from erpguard.db.model_packages.canary import CanaryPolicy, CanaryRoutingDecision, CanarySafetyIncident
        from erpguard.db.model_packages.execution import ExecutionRun
        from erpguard.domain.canary.eligibility import check_promotion_eligibility

        policy = (
            self.session.query(CanaryPolicy)
            .filter_by(tenant_id=tenant_id, canary_skill_package_id=skill_id)
            .order_by(CanaryPolicy.created_at.desc())
            .first()
        )
        if policy is None:
            return

        canary_decisions = (
            self.session.query(CanaryRoutingDecision)
            .filter_by(tenant_id=tenant_id, canary_policy_id=policy.id, selected_lane="canary")
            .filter(CanaryRoutingDecision.execution_run_id.isnot(None))
            .all()
        )
        canary_case_count = len(canary_decisions)
        run_ids = [row.execution_run_id for row in canary_decisions]
        runs = (
            self.session.query(ExecutionRun).filter(ExecutionRun.id.in_(run_ids)).all() if run_ids else []
        )
        # Only *terminal* outcomes count as observed evidence -- a run still
        # `planned`/`approved` has no postcondition result yet and must not
        # be silently treated as either a success or a failure.
        terminal_runs = [run for run in runs if run.status in {"succeeded", "blocked", "failed", "unknown"}]
        postcondition_success_rate = (
            sum(1 for run in terminal_runs if run.status == "succeeded") / len(terminal_runs)
            if terminal_runs
            else None
        )
        unresolved_critical = (
            self.session.query(CanarySafetyIncident)
            .filter_by(tenant_id=tenant_id, canary_policy_id=policy.id, severity="critical", resolved_at=None)
            .count()
        )
        coverage = min(1.0, canary_case_count / policy.maximum_cases) if policy.maximum_cases else 0.0
        issues = check_promotion_eligibility(
            policy_status=policy.status,
            unresolved_critical_incidents=unresolved_critical,
            canary_case_count=canary_case_count,
            postcondition_success_rate=postcondition_success_rate,
            observation_coverage=coverage,
        )
        if issues:
            raise CanaryPromotionNotEligible(f"canary_policy_not_eligible_for_promotion:{','.join(issues)}")

    def _record_event(
        self,
        *,
        tenant_id: str,
        process_key: str,
        skill_package_id: str,
        event_type: str,
        from_status: str,
        to_status: str,
        actor: str,
        reason: str,
        shadow_deployment_id: str | None = None,
    ) -> SkillDeploymentEvent:
        event = SkillDeploymentEvent(
            id=f"skdeploy_{uuid4().hex}",
            tenant_id=tenant_id,
            process_key=process_key,
            skill_package_id=skill_package_id,
            event_type=event_type,
            from_status=from_status,
            to_status=to_status,
            shadow_deployment_id=shadow_deployment_id,
            reason=reason,
            actor=actor,
        )
        self.session.add(event)
        return event

    def promote_to_canary(
        self, *, tenant_id: str, skill_id: str, shadow_deployment_id: str, actor: str, reason: str = ""
    ) -> SkillPackage:
        row = self._get(tenant_id=tenant_id, skill_id=skill_id)
        if row.status != "approved":
            raise InvalidStatusTransition(f"cannot_promote_to_canary_from:{row.status}")

        try:
            report = ShadowService(self.session).dashboard(
                tenant_id=tenant_id, deployment_id=shadow_deployment_id
            )
        except ShadowNotFound as exc:
            raise CanaryNotEligible("shadow_deployment_not_found") from exc

        if report["recommendation"] != "eligible_for_canary":
            raise CanaryNotEligible("shadow_evidence_not_eligible_for_canary")

        row.status = "canary"
        self._record_event(
            tenant_id=tenant_id,
            process_key=row.process_key,
            skill_package_id=row.id,
            event_type="promote_to_canary",
            from_status="approved",
            to_status="canary",
            actor=actor,
            reason=reason,
            shadow_deployment_id=shadow_deployment_id,
        )
        self.session.commit()
        self.session.refresh(row)
        return row

    def promote_to_active(self, *, tenant_id: str, skill_id: str, actor: str, reason: str = "") -> SkillPackage:
        row = self._get(tenant_id=tenant_id, skill_id=skill_id)
        if row.status != "canary":
            raise InvalidStatusTransition(f"cannot_promote_to_active_from:{row.status}")

        self._check_canary_policy_eligibility(tenant_id=tenant_id, skill_id=skill_id)

        previous_active = (
            self.session.query(SkillPackage)
            .filter_by(tenant_id=tenant_id, process_key=row.process_key, status="active")
            .one_or_none()
        )
        if previous_active is not None:
            previous_active.status = "deprecated"
            self._record_event(
                tenant_id=tenant_id,
                process_key=row.process_key,
                skill_package_id=previous_active.id,
                event_type="deprecate",
                from_status="active",
                to_status="deprecated",
                actor=actor,
                reason=f"superseded_by:{row.id}",
            )

        row.status = "active"
        self._record_event(
            tenant_id=tenant_id,
            process_key=row.process_key,
            skill_package_id=row.id,
            event_type="promote_to_active",
            from_status="canary",
            to_status="active",
            actor=actor,
            reason=reason,
        )
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConcurrentPromotionConflict(
                f"concurrent_promotion_for_process:{row.process_key}"
            ) from exc
        self.session.refresh(row)
        return row

    def rollback(self, *, tenant_id: str, process_key: str, actor: str, reason: str = "") -> SkillPackage | None:
        active = (
            self.session.query(SkillPackage)
            .filter_by(tenant_id=tenant_id, process_key=process_key, status="active")
            .one_or_none()
        )
        if active is None:
            raise NoActiveSkillPackage(process_key)

        promote_events = (
            self.session.query(SkillDeploymentEvent)
            .filter_by(
                tenant_id=tenant_id,
                process_key=process_key,
                event_type="promote_to_active",
            )
            .order_by(SkillDeploymentEvent.created_at.asc(), SkillDeploymentEvent.id.asc())
            .all()
        )
        previous_package_id = None
        for prior_event in reversed(promote_events):
            if prior_event.skill_package_id == active.id:
                continue
            previous_package_id = prior_event.skill_package_id
            break

        active.status = "rolled_back"
        self._record_event(
            tenant_id=tenant_id,
            process_key=process_key,
            skill_package_id=active.id,
            event_type="rollback",
            from_status="active",
            to_status="rolled_back",
            actor=actor,
            reason=reason,
        )

        restored: SkillPackage | None = None
        if previous_package_id is not None:
            candidate = self.session.query(SkillPackage).filter_by(tenant_id=tenant_id, id=previous_package_id).one_or_none()
            if candidate is not None and candidate.status == "deprecated":
                candidate.status = "active"
                self._record_event(
                    tenant_id=tenant_id,
                    process_key=process_key,
                    skill_package_id=candidate.id,
                    event_type="promote_to_active",
                    from_status="deprecated",
                    to_status="active",
                    actor=actor,
                    reason=f"restored_by_rollback_of:{active.id}",
                )
                restored = candidate

        self.session.commit()
        if restored is not None:
            self.session.refresh(restored)
        return restored

    def get_active(self, *, tenant_id: str, process_key: str) -> SkillPackage | None:
        return (
            self.session.query(SkillPackage)
            .filter_by(tenant_id=tenant_id, process_key=process_key, status="active")
            .one_or_none()
        )
