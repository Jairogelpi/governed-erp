from __future__ import annotations

from typing import Any

_SECRET_REDACTION_ENFORCED = True

_REDACTED_KEY_PATTERNS = frozenset({
    "api_key", "apikey", "password", "passwd", "secret", "token",
    "credential", "credentials", "private_key", "privatekey",
    "auth", "authorization", "bearer", "access_token", "refresh_token",
    "client_secret", "webhook_secret",
})

_REDACTED_SENTINEL = "***REDACTED***"


def _is_sensitive_key(key: str) -> bool:
    key_lower = key.lower().replace("-", "_").replace(" ", "_")
    return key_lower in _REDACTED_KEY_PATTERNS or any(p in key_lower for p in _REDACTED_KEY_PATTERNS)


def redact(value: Any, depth: int = 0) -> Any:
    if not _SECRET_REDACTION_ENFORCED or depth > 20:
        return value
    if isinstance(value, dict):
        return {
            k: _REDACTED_SENTINEL if _is_sensitive_key(k) else redact(v, depth + 1)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [redact(item, depth + 1) for item in value]
    return value


class SecretRedactionService:
    def redact(self, data: Any) -> Any:
        return redact(data)

    def redact_keys(self, data: dict, extra_keys: list[str] | None = None) -> dict:
        extra = frozenset(k.lower() for k in (extra_keys or []))
        result = {}
        for k, v in data.items():
            if _is_sensitive_key(k) or k.lower() in extra:
                result[k] = _REDACTED_SENTINEL
            else:
                result[k] = redact(v)
        return result
