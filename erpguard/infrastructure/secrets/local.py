"""Encrypted local SecretProvider for staging and self-hosted deployments."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol

from cryptography.fernet import Fernet, InvalidToken


class SecretProviderConfigurationError(ValueError):
    """Raised when encrypted secret storage has no valid key."""


@dataclass(frozen=True)
class SealedSecret:
    ciphertext: str
    fingerprint: str


class SecretProvider(Protocol):
    def seal(self, plaintext: str) -> SealedSecret: ...

    def reveal(self, ciphertext: str) -> str: ...


class EncryptedLocalSecretProvider:
    """Fernet-backed provider; plaintext is never persisted by this class."""

    def __init__(self, key: str | bytes | None):
        if not key:
            raise SecretProviderConfigurationError("local_secret_key_required")
        try:
            self._fernet = Fernet(key)
        except (TypeError, ValueError) as exc:
            raise SecretProviderConfigurationError("invalid_local_secret_key") from exc

    def seal(self, plaintext: str) -> SealedSecret:
        if not plaintext:
            raise ValueError("secret_required")
        encoded = plaintext.encode("utf-8")
        return SealedSecret(
            ciphertext=self._fernet.encrypt(encoded).decode("ascii"),
            fingerprint=f"sha256:{hashlib.sha256(encoded).hexdigest()[:16]}",
        )

    def reveal(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode("ascii")).decode("utf-8")
        except (InvalidToken, UnicodeDecodeError, ValueError) as exc:
            raise ValueError("secret_decryption_failed") from exc

