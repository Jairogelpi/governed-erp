from __future__ import annotations

import json

from sqlalchemy.orm import Session

from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import (
    create_advisory_session,
    get_advisory_session,
    list_advisory_proposals_for_session,
)


class AdvisorySessionService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, created_by: dict) -> dict:
        row = create_advisory_session(self.session, json.dumps(created_by, default=str))
        return self._model(row)

    def get(self, session_id: str) -> dict:
        row = get_advisory_session(self.session, session_id)
        if row is None:
            raise ObjectNotFoundError(f"AdvisorySession '{session_id}' not found.")
        return self._model(row)

    def _model(self, row) -> dict:
        return {
            "session_id": row.id,
            "status": row.status,
            "request_text": row.request_text,
            "latest_proposal_id": row.latest_proposal_id,
            "created_by": json.loads(row.created_by_actor_json or "{}"),
            "created_at": row.created_at.isoformat(),
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            "is_advisory_only": True,
            "can_execute": False,
        }
