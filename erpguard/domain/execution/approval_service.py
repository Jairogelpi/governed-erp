"""Approval records for execution permit binding (master spec 19.3's
`approval_ids`). Single-use: once bound to a run it cannot be reused --
enforced by `PermitService` marking `used_at`/`used_by_run_id`, which the
`Approval` model's immutability listener then locks in permanently.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from erpguard.db.model_packages.execution import Approval


class ApprovalNotFound(KeyError):
    pass


class ApprovalService:
    def __init__(self, session: Session):
        self.session = session

    def create(self, *, tenant_id: str, actor_id: str, scope: str) -> Approval:
        row = Approval(id=f"approval_{uuid4().hex}", tenant_id=tenant_id, actor_id=actor_id, scope=scope)
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def get(self, *, tenant_id: str, approval_id: str) -> Approval:
        row = self.session.query(Approval).filter_by(tenant_id=tenant_id, id=approval_id).one_or_none()
        if row is None:
            raise ApprovalNotFound(approval_id)
        return row

    def list(self, *, tenant_id: str) -> list[Approval]:
        return self.session.query(Approval).filter_by(tenant_id=tenant_id).order_by(Approval.created_at.desc()).all()
