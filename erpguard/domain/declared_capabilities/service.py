"""User-declared field-write capabilities: declare -> approve -> activate.

Approval reuses `Approval` exactly like Workstreams A/B/C
(`erpguard/application/recommendations/service.py`'s pattern): creator
cannot approve their own declaration, scope is bound to the capability's
content hash, single-use.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from erpguard.db.model_packages.declared_capabilities import DeclaredWriteCapability
from erpguard.db.model_packages.execution import Approval
from erpguard.domain.declared_capabilities.denylist import is_denylisted
from erpguard.domain.processes.candidate_integrity import stable_digest

_SUPPORTED_FIELD_TYPES = {"string", "integer", "decimal", "boolean"}
_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"approved", "rejected"},
    "approved": {"active", "rejected"},
    "active": {"deprecated"},
    "rejected": set(),
    "deprecated": set(),
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _dump(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


class DeclaredCapabilityNotFound(KeyError):
    pass


class DeclaredCapabilityValidationError(ValueError):
    pass


class DeclaredCapabilityDenied(DeclaredCapabilityValidationError):
    pass


class DeclaredCapabilityApprovalRejected(DeclaredCapabilityValidationError):
    pass


class DeclaredCapabilityTransitionError(DeclaredCapabilityValidationError):
    pass


class DeclaredCapabilityService:
    def __init__(self, session: Session):
        self.session = session

    def _get(self, *, tenant_id: str, capability_id: str) -> DeclaredWriteCapability:
        row = (
            self.session.query(DeclaredWriteCapability)
            .filter_by(tenant_id=tenant_id, id=capability_id)
            .one_or_none()
        )
        if row is None:
            raise DeclaredCapabilityNotFound(capability_id)
        return row

    def get(self, *, tenant_id: str, capability_id: str) -> DeclaredWriteCapability:
        return self._get(tenant_id=tenant_id, capability_id=capability_id)

    def list(self, *, tenant_id: str) -> list[DeclaredWriteCapability]:
        return (
            self.session.query(DeclaredWriteCapability)
            .filter_by(tenant_id=tenant_id)
            .order_by(DeclaredWriteCapability.created_at.desc())
            .all()
        )

    def get_active(self, *, tenant_id: str, capability_id: str) -> DeclaredWriteCapability | None:
        row = (
            self.session.query(DeclaredWriteCapability)
            .filter_by(tenant_id=tenant_id, id=capability_id, status="active")
            .one_or_none()
        )
        return row

    @staticmethod
    def approval_scope(row: DeclaredWriteCapability) -> str:
        return f"declared_write_capability:{row.id}:approve:{row.content_hash}"

    def _require_transition(self, *, current: str, target: str) -> None:
        if target not in _TRANSITIONS.get(current, set()):
            raise DeclaredCapabilityTransitionError(f"cannot_transition_from:{current}:to:{target}")

    def declare(
        self,
        *,
        tenant_id: str,
        name: str,
        target_model: str,
        target_field: str,
        field_type: str,
        created_by: str,
        minimum_value: str | None = None,
        maximum_value: str | None = None,
        allowed_values: list[str] | None = None,
        max_records_per_run: int = 1,
    ) -> DeclaredWriteCapability:
        if field_type not in _SUPPORTED_FIELD_TYPES:
            raise DeclaredCapabilityValidationError(f"unsupported_field_type:{field_type}")
        if is_denylisted(model=target_model, field=target_field):
            raise DeclaredCapabilityDenied(f"denylisted_target:{target_model}.{target_field}")
        if max_records_per_run < 1:
            raise DeclaredCapabilityValidationError("max_records_per_run_must_be_positive")

        content = {
            "target_model": target_model,
            "target_field": target_field,
            "field_type": field_type,
            "minimum_value": minimum_value,
            "maximum_value": maximum_value,
            "allowed_values": sorted(allowed_values or []),
            "max_records_per_run": max_records_per_run,
        }
        row = DeclaredWriteCapability(
            id=f"declaredcap_{uuid4().hex}",
            tenant_id=tenant_id,
            name=name,
            target_model=target_model,
            target_field=target_field,
            field_type=field_type,
            minimum_value=minimum_value,
            maximum_value=maximum_value,
            allowed_values_json=_dump(sorted(allowed_values or [])),
            max_records_per_run=max_records_per_run,
            status="draft",
            content_hash=stable_digest(content),
            created_by=created_by,
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def approve(
        self, *, tenant_id: str, capability_id: str, approval_id: str, approver_actor_id: str
    ) -> DeclaredWriteCapability:
        row = self._get(tenant_id=tenant_id, capability_id=capability_id)
        self._require_transition(current=row.status, target="approved")

        approval = self.session.query(Approval).filter_by(tenant_id=tenant_id, id=approval_id).one_or_none()
        if approval is None:
            raise DeclaredCapabilityApprovalRejected("approval_not_found")
        if approval.used_at is not None:
            raise DeclaredCapabilityApprovalRejected("approval_already_used")
        if approval.actor_id == row.created_by:
            raise DeclaredCapabilityApprovalRejected("declarer_cannot_approve_own_capability")
        if approval.actor_id != approver_actor_id:
            raise DeclaredCapabilityApprovalRejected("approval_actor_mismatch")
        if approval.scope != self.approval_scope(row):
            raise DeclaredCapabilityApprovalRejected("approval_scope_mismatch")

        approval.used_at = _utc_now()
        approval.used_by_run_id = row.id
        row.status = "approved"
        row.approved_by = approver_actor_id
        row.approved_at = _utc_now()
        self.session.commit()
        self.session.refresh(row)
        return row

    def reject(self, *, tenant_id: str, capability_id: str) -> DeclaredWriteCapability:
        row = self._get(tenant_id=tenant_id, capability_id=capability_id)
        self._require_transition(current=row.status, target="rejected")
        row.status = "rejected"
        self.session.commit()
        self.session.refresh(row)
        return row

    def activate(self, *, tenant_id: str, capability_id: str) -> DeclaredWriteCapability:
        row = self._get(tenant_id=tenant_id, capability_id=capability_id)
        self._require_transition(current=row.status, target="active")
        row.status = "active"
        row.activated_at = _utc_now()
        self.session.commit()
        self.session.refresh(row)
        return row

    def deprecate(self, *, tenant_id: str, capability_id: str) -> DeclaredWriteCapability:
        row = self._get(tenant_id=tenant_id, capability_id=capability_id)
        self._require_transition(current=row.status, target="deprecated")
        row.status = "deprecated"
        self.session.commit()
        self.session.refresh(row)
        return row
