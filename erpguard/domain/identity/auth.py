"""Small signed bearer-token boundary for the Phase 3 local identity slice."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass


class AuthenticationError(Exception):
    """Raised when a bearer token cannot establish identity."""


@dataclass(frozen=True)
class Principal:
    user_id: str
    tenant_id: str
    role_name: str


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def issue_token(
    user_id: str,
    tenant_id: str,
    secret: str,
    *,
    expires_at: int | None = None,
) -> str:
    """Issue a token for trusted bootstrap/test tooling, never from a public route."""
    payload = {
        "sub": user_id,
        "tenant": tenant_id,
        "exp": expires_at if expires_at is not None else int(time.time()) + 900,
    }
    encoded_payload = _encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
    signature = hmac.new(secret.encode(), encoded_payload.encode(), hashlib.sha256).digest()
    return f"{encoded_payload}.{_encode(signature)}"


def verify_token(token: str, secret: str, *, now: int | None = None) -> tuple[str, str]:
    try:
        encoded_payload, encoded_signature = token.split(".", 1)
        expected = hmac.new(secret.encode(), encoded_payload.encode(), hashlib.sha256).digest()
        supplied = _decode(encoded_signature)
        if not hmac.compare_digest(expected, supplied):
            raise AuthenticationError("invalid_token_signature")
        payload = json.loads(_decode(encoded_payload))
        user_id = payload["sub"]
        tenant_id = payload["tenant"]
        expires_at = int(payload["exp"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise AuthenticationError("invalid_token") from exc

    if not isinstance(user_id, str) or not isinstance(tenant_id, str):
        raise AuthenticationError("invalid_token_claims")
    current_time = int(time.time()) if now is None else now
    if expires_at <= current_time:
        raise AuthenticationError("token_expired")
    return user_id, tenant_id
