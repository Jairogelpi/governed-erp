from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from erpguard.db import repositories as repo
from erpguard.db.models import OAuthState

_STATE_TTL_SECONDS = 600  # 10 minutes


@dataclass
class OAuthStateRecord:
    id: str
    state_token: str
    profile_id: str
    connector_id: str
    redirect_uri: str
    scope_requested: str
    status: str
    created_at: datetime
    expires_at: datetime
    used_at: datetime | None = None

    @property
    def is_valid(self) -> bool:
        now = datetime.now(timezone.utc)
        exp = self.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return self.status == "pending" and now < exp

    def model_dump(self) -> dict:
        return {
            "id": self.id,
            "state_token": self.state_token,
            "profile_id": self.profile_id,
            "connector_id": self.connector_id,
            "redirect_uri": self.redirect_uri,
            "scope_requested": self.scope_requested,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "used_at": self.used_at.isoformat() if self.used_at else None,
        }


class OAuthStateStore:
    def __init__(self, session: Session):
        self._session = session

    def create(
        self,
        *,
        profile_id: str,
        connector_id: str,
        redirect_uri: str,
        scope_requested: str,
    ) -> OAuthStateRecord:
        state_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=_STATE_TTL_SECONDS)
        row = repo.create_oauth_state(
            self._session,
            state_token=state_token,
            profile_id=profile_id,
            connector_id=connector_id,
            redirect_uri=redirect_uri,
            scope_requested=scope_requested,
            expires_at=expires_at,
        )
        return self._to_model(row)

    def get(self, state_token: str) -> OAuthStateRecord | None:
        row = repo.get_oauth_state_by_token(self._session, state_token)
        return self._to_model(row) if row else None

    def consume(self, state_token: str) -> OAuthStateRecord | None:
        """Mark state as used; returns None if already used, expired, or not found."""
        row = repo.get_oauth_state_by_token(self._session, state_token)
        if row is None:
            return None
        record = self._to_model(row)
        if not record.is_valid:
            return None
        consumed = repo.consume_oauth_state(self._session, state_token)
        return self._to_model(consumed) if consumed else None

    def _to_model(self, row: OAuthState) -> OAuthStateRecord:
        return OAuthStateRecord(
            id=row.id,
            state_token=row.state_token,
            profile_id=row.profile_id,
            connector_id=row.connector_id,
            redirect_uri=row.redirect_uri,
            scope_requested=row.scope_requested,
            status=row.status,
            created_at=row.created_at,
            expires_at=row.expires_at,
            used_at=row.used_at,
        )
