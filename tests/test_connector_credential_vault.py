"""Tests for Sprint 55 — Connector Credential Vault Contract.

Covers: seal password/api_key/token, metadata retrieval, audit, revoke,
blocking rules, safety invariants, setup session linking.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from erpguard.db.models import Base
from erpguard.db.repositories import create_connector_setup_session
from erpguard.product.connector_credential_vault import (
    CredentialVaultContractService,
    CredentialVaultInput,
    AuthType,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _make_setup_session(db, session_id="csess_test1", status="draft"):
    return create_connector_setup_session(
        db,
        session_id=session_id,
        connector_name="odoo_test",
        erp_url="https://demo.odoo.com",
        erp_url_host="demo.odoo.com",
        environment_type="production",
        submitted_by="operator_1",
        status=status,
        credential_mode="not_provided",
        credential_ref=None,
        detected_adapter_type=None,
        blocking_reasons_json="[]",
    )


# --- Seal tests ---


def test_seals_password_credential(db):
    _make_setup_session(db)
    service = CredentialVaultContractService(db)
    result = service.seal_credential(
        CredentialVaultInput(
            setup_session_id="csess_test1",
            auth_type=AuthType.PASSWORD,
            username="admin@example.com",
            password="super-secret-password",
            submitted_by="operator_1",
        )
    )
    assert result.credential_ref.startswith("cred_")
    assert result.status == "sealed"
    assert result.credential_stored is True
    assert result.raw_secret_returned is False
    assert result.raw_secret_logged is False
    assert result.llm_accessible is False
    assert result.external_http_performed is False
    assert result.login_attempted is False
    assert result.fingerprint_performed is False
    assert result.schema_inspection_performed is False
    assert result.capability_generation_performed is False
    assert result.read_only_activation_performed is False
    assert result.erp_write_performed is False
    assert result.blocking_reasons == []
    assert "admin" not in result.metadata.get("username_redacted", "")
    assert result.metadata.get("secret_fingerprint", "").startswith("sha256:")
    assert result.metadata.get("secret_last4") == "word"


def test_seals_api_key_credential(db):
    _make_setup_session(db)
    service = CredentialVaultContractService(db)
    result = service.seal_credential(
        CredentialVaultInput(
            setup_session_id="csess_test1",
            auth_type=AuthType.API_KEY,
            api_key="sk_live_abc123xyz789",
            submitted_by="operator_1",
        )
    )
    assert result.credential_ref.startswith("cred_")
    assert result.status == "sealed"
    assert result.metadata.get("auth_type") == "api_key"
    assert result.metadata.get("secret_last4") == "z789"


def test_seals_token_credential(db):
    _make_setup_session(db)
    service = CredentialVaultContractService(db)
    result = service.seal_credential(
        CredentialVaultInput(
            setup_session_id="csess_test1",
            auth_type=AuthType.TOKEN,
            token="bearer-abc123def456ghi789",
            submitted_by="operator_1",
        )
    )
    assert result.credential_ref.startswith("cred_")
    assert result.status == "sealed"
    assert result.metadata.get("auth_type") == "token"


def test_returns_credential_ref_with_prefix(db):
    _make_setup_session(db)
    service = CredentialVaultContractService(db)
    result = service.seal_credential(
        CredentialVaultInput(
            setup_session_id="csess_test1",
            auth_type=AuthType.PASSWORD,
            username="admin@example.com",
            password="secret123",
            submitted_by="operator_1",
        )
    )
    assert result.credential_ref.startswith("cred_")


def test_does_not_return_raw_secret(db):
    _make_setup_session(db)
    service = CredentialVaultContractService(db)
    result = service.seal_credential(
        CredentialVaultInput(
            setup_session_id="csess_test1",
            auth_type=AuthType.PASSWORD,
            username="admin@example.com",
            password="my-super-secret",
            submitted_by="operator_1",
        )
    )
    assert "my-super-secret" not in str(result.model_dump())


def test_does_not_persist_raw_secret_in_metadata(db):
    _make_setup_session(db)
    service = CredentialVaultContractService(db)
    result = service.seal_credential(
        CredentialVaultInput(
            setup_session_id="csess_test1",
            auth_type=AuthType.PASSWORD,
            username="admin@example.com",
            password="raw-secret-value",
            submitted_by="operator_1",
        )
    )
    # Check metadata does not contain the raw secret
    assert "raw-secret-value" not in str(result.metadata)


def test_stores_fingerprint_not_raw_secret(db):
    _make_setup_session(db)
    service = CredentialVaultContractService(db)
    result = service.seal_credential(
        CredentialVaultInput(
            setup_session_id="csess_test1",
            auth_type=AuthType.PASSWORD,
            username="admin@example.com",
            password="test-password",
            submitted_by="operator_1",
        )
    )
    assert result.metadata.get("secret_fingerprint", "").startswith("sha256:")
    # Verify persisted entry also has fingerprint, no raw secret
    from erpguard.db.repositories import get_credential_vault_entry_by_ref

    entry = get_credential_vault_entry_by_ref(db, result.credential_ref)
    assert entry is not None
    assert entry.secret_fingerprint.startswith("sha256:")
    assert entry.secret_last4 == "word"
    # Raw secret should NOT be in entry
    assert not hasattr(entry, "secret") or not hasattr(entry, "password")


def test_updates_setup_session_to_vault_reference(db):
    _make_setup_session(db)
    service = CredentialVaultContractService(db)
    result = service.seal_credential(
        CredentialVaultInput(
            setup_session_id="csess_test1",
            auth_type=AuthType.PASSWORD,
            username="admin@example.com",
            password="test-password",
            submitted_by="operator_1",
        )
    )
    from erpguard.db.repositories import get_connector_setup_session

    session = get_connector_setup_session(db, "csess_test1")
    assert session is not None
    assert session.credential_mode == "vault_reference_only"
    assert session.credential_ref == result.credential_ref
    assert session.status == "ready_for_fingerprint"


# --- Blocking tests ---


def test_blocks_missing_setup_session(db):
    service = CredentialVaultContractService(db)
    result = service.seal_credential(
        CredentialVaultInput(
            setup_session_id="csess_nonexistent",
            auth_type=AuthType.PASSWORD,
            username="admin@example.com",
            password="test-password",
            submitted_by="operator_1",
        )
    )
    assert result.status == "blocked"
    assert "setup_session_not_found" in result.blocking_reasons
    assert result.credential_stored is False


def test_blocks_blocked_setup_session(db):
    _make_setup_session(db, session_id="csess_blocked", status="blocked")
    service = CredentialVaultContractService(db)
    result = service.seal_credential(
        CredentialVaultInput(
            setup_session_id="csess_blocked",
            auth_type=AuthType.PASSWORD,
            username="admin@example.com",
            password="test-password",
            submitted_by="operator_1",
        )
    )
    assert result.status == "blocked"
    assert "setup_session_blocked" in result.blocking_reasons


def test_blocks_unsupported_auth_type(db):
    _make_setup_session(db)
    service = CredentialVaultContractService(db)
    result = service.seal_credential(
        CredentialVaultInput(
            setup_session_id="csess_test1",
            auth_type=AuthType.UNKNOWN,
            submitted_by="operator_1",
        )
    )
    assert result.status == "blocked"
    assert "unsupported_auth_type" in result.blocking_reasons[0]


def test_blocks_missing_secret_for_password(db):
    _make_setup_session(db)
    service = CredentialVaultContractService(db)
    result = service.seal_credential(
        CredentialVaultInput(
            setup_session_id="csess_test1",
            auth_type=AuthType.PASSWORD,
            username="admin@example.com",
            password=None,
            submitted_by="operator_1",
        )
    )
    assert result.status == "blocked"
    assert "missing_secret" in result.blocking_reasons


def test_blocks_missing_secret_for_api_key(db):
    _make_setup_session(db)
    service = CredentialVaultContractService(db)
    result = service.seal_credential(
        CredentialVaultInput(
            setup_session_id="csess_test1",
            auth_type=AuthType.API_KEY,
            api_key=None,
            submitted_by="operator_1",
        )
    )
    assert result.status == "blocked"
    assert "missing_secret" in result.blocking_reasons


# --- Metadata and audit tests ---


def test_metadata_returns_redacted_only(db):
    _make_setup_session(db)
    service = CredentialVaultContractService(db)
    seal = service.seal_credential(
        CredentialVaultInput(
            setup_session_id="csess_test1",
            auth_type=AuthType.PASSWORD,
            username="admin@example.com",
            password="super-secret-password",
            submitted_by="operator_1",
        )
    )
    metadata = service.get_metadata(seal.credential_ref)
    assert metadata is not None
    assert metadata.auth_type == "password"
    assert metadata.username_redacted is not None
    assert "admin" not in metadata.username_redacted
    assert metadata.secret_fingerprint.startswith("sha256:")
    assert metadata.secret_last4 == "word"
    assert metadata.status == "sealed"


def test_credential_sealed_audit_event(db):
    _make_setup_session(db)
    service = CredentialVaultContractService(db)
    service.seal_credential(
        CredentialVaultInput(
            setup_session_id="csess_test1",
            auth_type=AuthType.PASSWORD,
            username="admin@example.com",
            password="test-password",
            submitted_by="operator_1",
        )
    )
    audit = service.get_audit()
    assert len(audit.events) >= 1
    event = audit.events[0]
    assert event["event_type"] == "credential_sealed"
    assert event["status"] == "sealed"
    assert "test-password" not in str(event)


def test_audit_does_not_contain_raw_secret(db):
    _make_setup_session(db)
    service = CredentialVaultContractService(db)
    service.seal_credential(
        CredentialVaultInput(
            setup_session_id="csess_test1",
            auth_type=AuthType.PASSWORD,
            username="admin@example.com",
            password="my-raw-password-12345",
            submitted_by="operator_1",
        )
    )
    audit = service.get_audit()
    for event in audit.events:
        assert "my-raw-password-12345" not in str(event)


# --- Safety invariant tests ---


def test_external_http_performed_false(db):
    _make_setup_session(db)
    service = CredentialVaultContractService(db)
    result = service.seal_credential(
        CredentialVaultInput(
            setup_session_id="csess_test1",
            auth_type=AuthType.PASSWORD,
            username="admin@example.com",
            password="test-password",
            submitted_by="operator_1",
        )
    )
    assert result.external_http_performed is False


def test_login_attempted_false(db):
    _make_setup_session(db)
    service = CredentialVaultContractService(db)
    result = service.seal_credential(
        CredentialVaultInput(
            setup_session_id="csess_test1",
            auth_type=AuthType.PASSWORD,
            username="admin@example.com",
            password="test-password",
            submitted_by="operator_1",
        )
    )
    assert result.login_attempted is False


def test_fingerprint_performed_false(db):
    _make_setup_session(db)
    service = CredentialVaultContractService(db)
    result = service.seal_credential(
        CredentialVaultInput(
            setup_session_id="csess_test1",
            auth_type=AuthType.PASSWORD,
            username="admin@example.com",
            password="test-password",
            submitted_by="operator_1",
        )
    )
    assert result.fingerprint_performed is False


def test_schema_inspection_performed_false(db):
    _make_setup_session(db)
    service = CredentialVaultContractService(db)
    result = service.seal_credential(
        CredentialVaultInput(
            setup_session_id="csess_test1",
            auth_type=AuthType.PASSWORD,
            username="admin@example.com",
            password="test-password",
            submitted_by="operator_1",
        )
    )
    assert result.schema_inspection_performed is False


def test_capability_generation_performed_false(db):
    _make_setup_session(db)
    service = CredentialVaultContractService(db)
    result = service.seal_credential(
        CredentialVaultInput(
            setup_session_id="csess_test1",
            auth_type=AuthType.PASSWORD,
            username="admin@example.com",
            password="test-password",
            submitted_by="operator_1",
        )
    )
    assert result.capability_generation_performed is False


def test_read_only_activation_performed_false(db):
    _make_setup_session(db)
    service = CredentialVaultContractService(db)
    result = service.seal_credential(
        CredentialVaultInput(
            setup_session_id="csess_test1",
            auth_type=AuthType.PASSWORD,
            username="admin@example.com",
            password="test-password",
            submitted_by="operator_1",
        )
    )
    assert result.read_only_activation_performed is False


def test_ui_exposes_credential_vault_card(client):
    response = client.get("/demo")
    assert response.status_code == 200
    assert b"Credential Vault Contract" in response.content
    assert b"Sprint 55" in response.content
    assert b"credVaultSeal" in response.content
    assert b"credVaultGetMetadata" in response.content
    assert b"credVaultAudit" in response.content
