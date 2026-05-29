"""Sprint 57 - Safe Discovery Plan audit.

Read-only audit projection for plan/model-only discovery events.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from erpguard.db.repositories import list_safe_discovery_audit_events


@dataclass
class SafeDiscoveryAuditResult:
    events: list[dict[str, Any]]


class SafeDiscoveryAuditService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_audit(self, limit: int = 50) -> SafeDiscoveryAuditResult:
        rows = list_safe_discovery_audit_events(self.session, limit=limit)
        events = []
        for row in rows:
            events.append(
                {
                    "id": row.id,
                    "discovery_plan_id": row.discovery_plan_id,
                    "fingerprint_plan_id": row.fingerprint_plan_id,
                    "setup_session_id": row.setup_session_id,
                    "credential_ref": row.credential_ref,
                    "event_type": row.event_type,
                    "status": row.status,
                    "created_by": row.created_by,
                    "details": row.details_json,
                    "created_at": str(row.created_at),
                }
            )
        return SafeDiscoveryAuditResult(events=events)
