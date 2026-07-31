"""Skill deployment lifecycle: canary -> active -> rollback (Phase 19, spec 18.4).

`SkillPackage.status` is the state; `SkillDeploymentEvent` is the append-only
audit trail of how it got there. "Active version" for a process is derived,
not stored: whichever `SkillPackage` row currently has `status == "active"`
for that `(tenant_id, process_key)` -- this service enforces there is ever
at most one.
"""

from __future__ import annotations

from uuid import uuid4

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


class SkillDeploymentService:
    def __init__(self, session: Session):
        self.session = session

    def _get(self, *, tenant_id: str, skill_id: str) -> SkillPackage:
        row = self.session.query(SkillPackage).filter_by(tenant_id=tenant_id, id=skill_id).one_or_none()
        if row is None:
            raise SkillPackageNotFound(skill_id)
        return row

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
        self.session.commit()
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
