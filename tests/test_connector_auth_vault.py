from __future__ import annotations

from erpguard.product.credential_vault import CredentialVault
from erpguard.product.scope_registry import ScopeRegistry


def test_credential_vault_returns_reference_without_plaintext_secret():
    secret = "sk_live_super_secret_token"

    record = CredentialVault().store({"access_token": secret, "refresh_token": "refresh_secret"})

    assert record.credential_ref.startswith("vault_ref_")
    assert record.secret_fingerprint.startswith("sha256:")
    assert record.has_secret is True
    assert record.secret_redacted is True
    assert secret not in record.model_dump_json()
    assert "refresh_secret" not in record.model_dump_json()


def test_scope_registry_exposes_placeholder_oauth_readiness_only():
    scopes = ScopeRegistry().list_scopes()
    gmail = next(item for item in scopes if item.connector_id == "gmail")

    assert gmail.oauth_flow_enabled is False
    assert gmail.provider_api_calls_enabled is False
    assert gmail.oauth_readiness == "placeholder_only"
    assert "gmail.readonly" in gmail.available_scopes
