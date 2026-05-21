from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy.orm import Session

from erpguard.db import repositories as repo
from erpguard.db.models import OAuthTokenRecord
from erpguard.product.credential_vault import CredentialVault

# In-memory token store: vault_ref -> token_data.
# Tokens are NEVER persisted to the database or returned in API responses.
# Cleared on process restart — acceptable for this demo/TFM context.
_TOKEN_STORE: dict[str, dict] = {}

_ALLOWED_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"
_FORBIDDEN_SCOPE_SUBSTRINGS = [
    "calendar.events.write",
    "calendar.readonly.write",
    "gmail",
    "drive",
    "whatsapp",
    "send",
    "write",
    "delete",
    "insert",
    "update",
    "modify",
]


@dataclass
class OAuthTokenVaultRecord:
    vault_ref: str
    secret_fingerprint: str
    scope_granted: list[str]
    scope_compliant: bool
    has_refresh_token: bool
    token_type: str
    placeholder_mode: bool
    token_exposed: bool = False
    secret_redacted: bool = True
    token_record_id: str = ""

    def model_dump(self) -> dict:
        return {
            "vault_ref": self.vault_ref,
            "secret_fingerprint": self.secret_fingerprint,
            "scope_granted": self.scope_granted,
            "scope_compliant": self.scope_compliant,
            "has_refresh_token": self.has_refresh_token,
            "token_type": self.token_type,
            "placeholder_mode": self.placeholder_mode,
            "token_exposed": self.token_exposed,
            "secret_redacted": self.secret_redacted,
            "token_record_id": self.token_record_id,
        }


def _check_scope_compliance(scope_granted: list[str]) -> bool:
    """Returns True only if granted scopes are exclusively calendar.readonly."""
    if not scope_granted:
        return False
    for scope in scope_granted:
        lower = scope.lower()
        for forbidden in _FORBIDDEN_SCOPE_SUBSTRINGS:
            if forbidden in lower:
                return False
        if scope != _ALLOWED_SCOPE and scope not in (
            "openid", "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
        ):
            # Anything beyond calendar.readonly and basic OIDC is non-compliant
            if "calendar" in lower and scope != _ALLOWED_SCOPE:
                return False
    return _ALLOWED_SCOPE in scope_granted


class OAuthTokenVault:
    def __init__(self, session: Session):
        self._session = session
        self._vault = CredentialVault()

    def store(
        self,
        *,
        profile_id: str,
        connector_id: str,
        token_data: dict[str, Any],
        placeholder_mode: bool = True,
        expires_in_seconds: int | None = None,
    ) -> OAuthTokenVaultRecord:
        vault_record = self._vault.store(token_data)
        # Store token in-memory only — never in DB
        _TOKEN_STORE[vault_record.credential_ref] = token_data

        scope_str = token_data.get("scope", "")
        scope_granted = [s.strip() for s in scope_str.split() if s.strip()] if scope_str else []
        scope_compliant = _check_scope_compliance(scope_granted)
        has_refresh = bool(token_data.get("refresh_token"))
        token_type = token_data.get("token_type", "Bearer")

        expires_at = None
        if expires_in_seconds:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)

        row = repo.create_oauth_token_record(
            self._session,
            profile_id=profile_id,
            connector_id=connector_id,
            vault_ref=vault_record.credential_ref,
            secret_fingerprint=vault_record.secret_fingerprint,
            scope_granted_json=json.dumps(scope_granted),
            scope_compliant=scope_compliant,
            has_refresh_token=has_refresh,
            token_type=token_type,
            placeholder_mode=placeholder_mode,
            expires_at=expires_at,
        )

        return OAuthTokenVaultRecord(
            vault_ref=vault_record.credential_ref,
            secret_fingerprint=vault_record.secret_fingerprint,
            scope_granted=scope_granted,
            scope_compliant=scope_compliant,
            has_refresh_token=has_refresh,
            token_type=token_type,
            placeholder_mode=placeholder_mode,
            token_record_id=row.id,
        )

    def retrieve_token(self, vault_ref: str) -> dict | None:
        """Return raw token data for internal use only. Never expose in API responses."""
        return _TOKEN_STORE.get(vault_ref)

    def get_record(self, profile_id: str) -> OAuthTokenRecord | None:
        return repo.get_oauth_token_record_for_profile(self._session, profile_id)

    def revoke(self, profile_id: str) -> bool:
        row = repo.get_oauth_token_record_for_profile(self._session, profile_id)
        if row:
            _TOKEN_STORE.pop(row.vault_ref, None)
            repo.revoke_oauth_token_record(self._session, profile_id)
            return True
        return False
