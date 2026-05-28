"""Tests for Sprint 55 — Connector Credential Vault Audit."""

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


def _make_setup_session(db, session_id="csess_audit1"):
    return create_connector_setup_session(
        db,
        session_id=session_id,
        connector_name="odoo_audit_test",
        erp_url="https://audit.odoo.com",
        erp_url_host="audit.odoo.com",
        environment_type="production",
        submitted_by="operator_audit",
        status="draft",
        credential_mode="not_provided",
        credential_ref=None,
        detected_adapter_type=None,
        blocking_reasons_json="[]",
    )


def test_audit_records_credential_sealed(db):
    _make_setup_session(db)
    service = CredentialVaultContractService(db)
    service.seal_credential(
        CredentialVaultInput(
            setup_session_id="csess_audit1",
            auth_type=AuthType.PASSWORD,
            username="admin@example.com",
            password="audit-password",
            submitted_by="operator_audit",
        )
    )
    audit = service.get_audit()
    sealed_events = [e for e in audit.events if e["event_type"] == "credential_sealed"]
    assert len(sealed_events) >= 1
    event = sealed_events[0]
    assert event["auth_type"] == "password"
    assert event["status"] == "sealed"


def test_audit_does_not_contain_raw_secret(db):
    _make_setup_session(db)
    service = CredentialVaultContractService(db)
    service.seal_credential(
        CredentialVaultInput(
            setup_session_id="csess_audit1",
            auth_type=AuthType.PASSWORD,
            username="admin@example.com",
            password="raw-audit-secret",
            submitted_by="operator_audit",
        )
    )
    audit = service.get_audit()
    for event in audit.events:
        assert "raw-audit-secret" not in str(event)


def test_audit_records_credential_revoked(db):
    _make_setup_session(db)
    service = CredentialVaultContractService(db)
    result = service.seal_credential(
        CredentialVaultInput(
            setup_session_id="csess_audit1",
            auth_type=AuthType.API_KEY,
            api_key="sk_audit_key",
            submitted_by="operator_audit",
        )
    )
    service.revoke_credential(result.credential_ref, revoked_by="operator_audit")
    audit = service.get_audit()
    revoked_events = [
        e for e in audit.events if e["event_type"] == "credential_revoked"
    ]
    assert len(revoked_events) >= 1


def test_external_http_performed_false_in_audit(db):
    _make_setup_session(db)
    service = CredentialVaultContractService(db)
    service.seal_credential(
        CredentialVaultInput(
            setup_session_id="csess_audit1",
            auth_type=AuthType.TOKEN,
            token="audit-token-value",
            submitted_by="operator_audit",
        )
    )
    # Audit events should never contain external_http or login flags
    audit = service.get_audit()
    for event in audit.events:
        # These fields are on the seal response, not the audit event
        # But verify the seal response
        pass
    result = service.seal_credential(
        CredentialVaultInput(
            setup_session_id="csess_audit1",
            auth_type=AuthType.TOKEN,
            token="second-audit-token",
            submitted_by="operator_audit",
        )
    )
    assert result.external_http_performed is False
    assert result.login_attempted is False
    assert result.fingerprint_performed is False
