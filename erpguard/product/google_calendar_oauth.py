from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode

from sqlalchemy.orm import Session

from erpguard.db import repositories as repo
from erpguard.product.external_connector_audit import ExternalConnectorAuditService
from erpguard.product.oauth_state_store import OAuthStateStore
from erpguard.product.oauth_token_vault import OAuthTokenVault

_ALLOWED_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"
_CONNECTOR_ID = "google_calendar_readonly"

_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"

# Credentials from environment — NEVER hardcoded, NEVER logged
_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "placeholder_client_id")
_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "placeholder_client_secret")
_DEFAULT_REDIRECT_URI = os.environ.get(
    "OAUTH_REDIRECT_URI", "http://localhost:8000/v1/oauth/google-calendar/callback"
)

_PLACEHOLDER_MODE = _CLIENT_ID in ("", "placeholder_client_id") or _CLIENT_SECRET in ("", "placeholder_client_secret")


@dataclass
class AuthUrlResult:
    authorization_url: str
    state_token: str
    profile_id: str
    scope_requested: str
    redirect_uri: str
    placeholder_mode: bool
    token_exposed: bool = False
    secret_redacted: bool = True

    def model_dump(self) -> dict:
        return {
            "authorization_url": self.authorization_url,
            "state_token": self.state_token,
            "profile_id": self.profile_id,
            "scope_requested": self.scope_requested,
            "redirect_uri": self.redirect_uri,
            "placeholder_mode": self.placeholder_mode,
            "token_exposed": self.token_exposed,
            "secret_redacted": self.secret_redacted,
        }


@dataclass
class TokenExchangeResult:
    profile_id: str
    connector_id: str
    vault_ref: str
    secret_fingerprint: str
    scope_granted: list[str]
    scope_compliant: bool
    has_refresh_token: bool
    placeholder_mode: bool
    token_exposed: bool = False
    secret_redacted: bool = True
    token_record_id: str = ""

    def model_dump(self) -> dict:
        return {
            "profile_id": self.profile_id,
            "connector_id": self.connector_id,
            "vault_ref": self.vault_ref,
            "secret_fingerprint": self.secret_fingerprint,
            "scope_granted": self.scope_granted,
            "scope_compliant": self.scope_compliant,
            "has_refresh_token": self.has_refresh_token,
            "placeholder_mode": self.placeholder_mode,
            "token_exposed": self.token_exposed,
            "secret_redacted": self.secret_redacted,
            "token_record_id": self.token_record_id,
        }


@dataclass
class OAuthStatusResult:
    profile_id: str
    connector_id: str
    authorized: bool
    scope_compliant: bool
    scope_granted: list[str]
    placeholder_mode: bool
    token_record_id: str
    status: str
    token_exposed: bool = False
    secret_redacted: bool = True

    def model_dump(self) -> dict:
        return {
            "profile_id": self.profile_id,
            "connector_id": self.connector_id,
            "authorized": self.authorized,
            "scope_compliant": self.scope_compliant,
            "scope_granted": self.scope_granted,
            "placeholder_mode": self.placeholder_mode,
            "token_record_id": self.token_record_id,
            "status": self.status,
            "token_exposed": self.token_exposed,
            "secret_redacted": self.secret_redacted,
        }


@dataclass
class ScopeVerificationResult:
    profile_id: str
    scope_compliant: bool
    scope_granted: list[str]
    allowed_scope: str
    violations: list[str] = field(default_factory=list)
    token_exposed: bool = False

    def model_dump(self) -> dict:
        return {
            "profile_id": self.profile_id,
            "scope_compliant": self.scope_compliant,
            "scope_granted": self.scope_granted,
            "allowed_scope": self.allowed_scope,
            "violations": self.violations,
            "token_exposed": self.token_exposed,
        }


class GoogleCalendarOAuthService:
    def __init__(self, session: Session):
        self._session = session
        self._state_store = OAuthStateStore(session)
        self._token_vault = OAuthTokenVault(session)
        self._audit = ExternalConnectorAuditService(session)

    def build_authorization_url(
        self,
        profile_id: str,
        redirect_uri: str | None = None,
        actor: dict | None = None,
    ) -> AuthUrlResult:
        effective_redirect = redirect_uri or _DEFAULT_REDIRECT_URI
        state_record = self._state_store.create(
            profile_id=profile_id,
            connector_id=_CONNECTOR_ID,
            redirect_uri=effective_redirect,
            scope_requested=_ALLOWED_SCOPE,
        )

        if _PLACEHOLDER_MODE:
            auth_url = (
                f"https://placeholder.oauth.example/authorize"
                f"?client_id=placeholder&scope={_ALLOWED_SCOPE}"
                f"&state={state_record.state_token}&redirect_uri={effective_redirect}"
                f"&response_type=code&access_type=offline&prompt=consent"
            )
        else:
            params = {
                "client_id": _CLIENT_ID,
                "redirect_uri": effective_redirect,
                "response_type": "code",
                "scope": _ALLOWED_SCOPE,
                "state": state_record.state_token,
                "access_type": "offline",
                "prompt": "consent",
            }
            auth_url = f"{_GOOGLE_AUTH_URL}?{urlencode(params)}"

        self._audit.record(
            auth_profile_id=profile_id,
            connector_id=_CONNECTOR_ID,
            event_type="oauth_authorize_url_generated",
            operation="build_authorization_url",
            status="generated",
            fixture_mode=_PLACEHOLDER_MODE,
            actor=actor or {},
            details={
                "placeholder_mode": _PLACEHOLDER_MODE,
                "scope_requested": _ALLOWED_SCOPE,
                "state_token_created": True,
                "token_exposed": False,
            },
        )

        return AuthUrlResult(
            authorization_url=auth_url,
            state_token=state_record.state_token,
            profile_id=profile_id,
            scope_requested=_ALLOWED_SCOPE,
            redirect_uri=effective_redirect,
            placeholder_mode=_PLACEHOLDER_MODE,
        )

    def exchange_code(
        self,
        code: str,
        state_token: str,
        actor: dict | None = None,
    ) -> TokenExchangeResult:
        state = self._state_store.consume(state_token)
        if state is None:
            raise ValueError("Invalid, expired, or already-used OAuth state token.")

        profile_id = state.profile_id

        token_data: dict[str, Any]
        if _PLACEHOLDER_MODE:
            token_data = {
                "access_token": "placeholder_access_token_redacted",
                "refresh_token": "placeholder_refresh_token_redacted",
                "token_type": "Bearer",
                "scope": _ALLOWED_SCOPE,
                "expires_in": 3600,
            }
        else:
            token_data = self._real_exchange(
                code=code,
                redirect_uri=state.redirect_uri,
            )

        vault_record = self._token_vault.store(
            profile_id=profile_id,
            connector_id=_CONNECTOR_ID,
            token_data=token_data,
            placeholder_mode=_PLACEHOLDER_MODE,
            expires_in_seconds=token_data.get("expires_in"),
        )

        repo.update_connector_auth_profile(
            self._session, profile_id, status="oauth_authorized"
        )

        self._audit.record(
            auth_profile_id=profile_id,
            connector_id=_CONNECTOR_ID,
            event_type="oauth_token_exchanged",
            operation="exchange_code",
            status="success",
            fixture_mode=_PLACEHOLDER_MODE,
            actor=actor or {},
            details={
                "placeholder_mode": _PLACEHOLDER_MODE,
                "scope_compliant": vault_record.scope_compliant,
                "has_refresh_token": vault_record.has_refresh_token,
                "token_exposed": False,
                "secret_redacted": True,
            },
        )

        return TokenExchangeResult(
            profile_id=profile_id,
            connector_id=_CONNECTOR_ID,
            vault_ref=vault_record.vault_ref,
            secret_fingerprint=vault_record.secret_fingerprint,
            scope_granted=vault_record.scope_granted,
            scope_compliant=vault_record.scope_compliant,
            has_refresh_token=vault_record.has_refresh_token,
            placeholder_mode=_PLACEHOLDER_MODE,
            token_record_id=vault_record.token_record_id,
        )

    def get_auth_status(self, profile_id: str) -> OAuthStatusResult:
        row = self._token_vault.get_record(profile_id)
        if row is None:
            return OAuthStatusResult(
                profile_id=profile_id,
                connector_id=_CONNECTOR_ID,
                authorized=False,
                scope_compliant=False,
                scope_granted=[],
                placeholder_mode=_PLACEHOLDER_MODE,
                token_record_id="",
                status="not_authorized",
            )
        scope_granted = json.loads(row.scope_granted_json) if row.scope_granted_json else []
        return OAuthStatusResult(
            profile_id=profile_id,
            connector_id=_CONNECTOR_ID,
            authorized=row.status == "active",
            scope_compliant=row.scope_compliant,
            scope_granted=scope_granted,
            placeholder_mode=row.placeholder_mode,
            token_record_id=row.id,
            status=row.status,
        )

    def verify_scope(self, profile_id: str) -> ScopeVerificationResult:
        row = self._token_vault.get_record(profile_id)
        if row is None:
            return ScopeVerificationResult(
                profile_id=profile_id,
                scope_compliant=False,
                scope_granted=[],
                allowed_scope=_ALLOWED_SCOPE,
                violations=["no active token found for profile"],
            )
        scope_granted = json.loads(row.scope_granted_json) if row.scope_granted_json else []
        violations = []
        if _ALLOWED_SCOPE not in scope_granted:
            violations.append(f"required scope '{_ALLOWED_SCOPE}' not granted")
        for scope in scope_granted:
            if scope != _ALLOWED_SCOPE and "calendar" in scope.lower() and "readonly" not in scope.lower():
                violations.append(f"non-read scope detected: {scope}")
        return ScopeVerificationResult(
            profile_id=profile_id,
            scope_compliant=row.scope_compliant,
            scope_granted=scope_granted,
            allowed_scope=_ALLOWED_SCOPE,
            violations=violations,
        )

    def revoke(self, profile_id: str, actor: dict | None = None) -> dict:
        revoked = self._token_vault.revoke(profile_id)
        repo.update_connector_auth_profile(self._session, profile_id, status="revoked")

        self._audit.record(
            auth_profile_id=profile_id,
            connector_id=_CONNECTOR_ID,
            event_type="oauth_token_revoked",
            operation="revoke",
            status="revoked" if revoked else "no_token_found",
            fixture_mode=_PLACEHOLDER_MODE,
            actor=actor or {},
            details={"token_exposed": False, "secret_redacted": True},
        )
        return {
            "profile_id": profile_id,
            "revoked": revoked,
            "placeholder_mode": _PLACEHOLDER_MODE,
            "token_exposed": False,
            "secret_redacted": True,
        }

    def _real_exchange(self, code: str, redirect_uri: str) -> dict:
        """Exchange authorization code for tokens via Google's token endpoint."""
        import urllib.request
        import urllib.parse

        payload = urlencode({
            "code": code,
            "client_id": _CLIENT_ID,
            "client_secret": _CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }).encode("utf-8")

        req = urllib.request.Request(
            _GOOGLE_TOKEN_URL,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
