from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel


class CredentialVaultRecord(BaseModel):
    credential_ref: str
    secret_fingerprint: str
    has_secret: bool
    secret_redacted: bool = True
    storage_mode: str = "reference_only"


class CredentialVault:
    def store(self, credential: dict[str, Any] | None) -> CredentialVaultRecord:
        normalized = json.dumps(credential or {}, sort_keys=True, default=str)
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return CredentialVaultRecord(
            credential_ref=f"vault_ref_{digest[:16]}",
            secret_fingerprint=f"sha256:{digest[:12]}",
            has_secret=bool(credential),
            secret_redacted=True,
        )
