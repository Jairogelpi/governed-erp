"""Per-tenant kill switch (master spec 19.4's "kill switch" rejection reason).

This is exactly a tenant-scoped on/off flag an admin can toggle -- not a
broader circuit-breaker system, not tied to any live monitoring signal.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from erpguard.db.model_packages.execution import KillSwitch


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class KillSwitchService:
    def __init__(self, session: Session):
        self.session = session

    def set(self, *, tenant_id: str, active: bool) -> KillSwitch:
        row = self.session.query(KillSwitch).filter_by(tenant_id=tenant_id).one_or_none()
        if row is None:
            row = KillSwitch(tenant_id=tenant_id, active=active)
            self.session.add(row)
        else:
            row.active = active
            row.updated_at = _utc_now()
        self.session.commit()
        self.session.refresh(row)
        return row

    def is_active(self, *, tenant_id: str) -> bool:
        row = self.session.query(KillSwitch).filter_by(tenant_id=tenant_id).one_or_none()
        return row is not None and row.active
