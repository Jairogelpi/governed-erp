"""Sprint 74 - Odoo read-only adapter shell audit."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from erpguard.db.repositories import list_odoo_read_only_adapter_audit_events


@dataclass
class OdooReadOnlyAdapterAuditResult:
    events: list[dict[str, Any]]


class OdooReadOnlyAdapterAuditService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_audit(self, limit: int = 50) -> OdooReadOnlyAdapterAuditResult:
        rows = list_odoo_read_only_adapter_audit_events(self.session, limit=limit)
        return OdooReadOnlyAdapterAuditResult(
            events=[
                {
                    "id": row.id,
                    "adapter_session_id": row.adapter_session_id,
                    "activation_id": row.activation_id,
                    "capability_set_id": row.capability_set_id,
                    "setup_session_id": row.setup_session_id,
                    "credential_ref": row.credential_ref,
                    "event_type": row.event_type,
                    "status": row.status,
                    "actor": row.actor,
                    "details": row.details_json,
                    "created_at": str(row.created_at),
                }
                for row in rows
            ]
        )
