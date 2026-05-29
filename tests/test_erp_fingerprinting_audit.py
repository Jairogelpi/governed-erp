"""Tests for Sprint 56 — ERP Fingerprinting Plan Audit."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from erpguard.db.models import Base
from erpguard.db.repositories import (
    create_connector_setup_session,
    update_connector_setup_session,
)
from erpguard.product.connector_credential_vault import (
    AuthType,
    CredentialVaultContractService,
    CredentialVaultInput,
)
from erpguard.product.erp_fingerprinting_plan import (
    ERPFingerprintingPlanService,
    FingerprintingPlanInput,
)
from erpguard.product.erp_fingerprinting_audit import ERPFingerprintingAuditService


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _make_session_and_seal(db, session_id="csess_audit1"):
    create_connector_setup_session(
        db,
        session_id=session_id,
        connector_name="odoo_audit",
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
    vault = CredentialVaultContractService(db)
    cred = vault.seal_credential(
        CredentialVaultInput(
            setup_session_id=session_id,
            auth_type=AuthType.PASSWORD,
            username="admin@audit.com",
            password="audit-secret",
            submitted_by="operator_audit",
        )
    )
    update_connector_setup_session(
        db,
        session_id,
        credential_ref=cred.credential_ref,
        credential_mode="vault_reference_only",
        status="ready_for_fingerprint",
    )
    return cred.credential_ref


def test_audit_records_plan_created(db):
    cred_ref = _make_session_and_seal(db)
    service = ERPFingerprintingPlanService(db)
    result = service.create_plan(
        FingerprintingPlanInput(
            setup_session_id="csess_audit1",
            credential_ref=cred_ref,
            created_by="operator_audit",
        )
    )
    assert result.status == "planned"

    audit = ERPFingerprintingAuditService(db)
    audit_result = audit.get_audit()
    created_events = [
        e
        for e in audit_result.events
        if e["event_type"] == "fingerprinting_plan_created"
    ]
    assert len(created_events) >= 1
    assert created_events[0]["fingerprint_plan_id"] == result.fingerprint_plan_id


def test_audit_does_not_contain_raw_secret(db):
    cred_ref = _make_session_and_seal(db)
    service = ERPFingerprintingPlanService(db)
    service.create_plan(
        FingerprintingPlanInput(
            setup_session_id="csess_audit1",
            credential_ref=cred_ref,
            created_by="operator_audit",
        )
    )

    audit = ERPFingerprintingAuditService(db)
    audit_result = audit.get_audit()
    for event in audit_result.events:
        assert "audit-secret" not in str(event)


def test_audit_events_include_status(db):
    cred_ref = _make_session_and_seal(db)
    service = ERPFingerprintingPlanService(db)
    result = service.create_plan(
        FingerprintingPlanInput(
            setup_session_id="csess_audit1",
            credential_ref=cred_ref,
            created_by="operator_audit",
        )
    )

    audit = ERPFingerprintingAuditService(db)
    audit_result = audit.get_audit()
    created_events = [
        e
        for e in audit_result.events
        if e["event_type"] == "fingerprinting_plan_created"
    ]
    assert created_events[0]["status"] == "planned"
