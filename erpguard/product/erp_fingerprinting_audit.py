"""Sprint 56 — ERP Fingerprinting Plan Audit.

Read-only audit trail for fingerprinting plan events.
Never includes raw secrets, passwords, API keys, or tokens.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from erpguard.db.repositories import list_erp_fingerprinting_audit_events


@dataclass
class FingerprintingAuditResult:
    events: list[dict[str, Any]]


class ERPFingerprintingAuditService:
    """Read-only audit trail for fingerprinting plan events."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_audit(self, limit: int = 50) -> FingerprintingAuditResult:
        rows = list_erp_fingerprinting_audit_events(self.session, limit=limit)
        events = []
        for row in rows:
            events.append(
                {
                    "id": row.id,
                    "fingerprint_plan_id": row.fingerprint_plan_id,
                    "setup_session_id": row.setup_session_id,
                    "credential_ref": row.credential_ref,
                    "event_type": row.event_type,
                    "status": row.status,
                    "details": row.details_json,
                    "created_at": str(row.created_at),
                }
            )
        return FingerprintingAuditResult(events=events)
