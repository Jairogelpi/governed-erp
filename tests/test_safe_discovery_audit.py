"""Tests for Sprint 57 - Safe Discovery audit."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from erpguard.db.models import Base
from erpguard.db.repositories import create_connector_setup_session
from erpguard.product.connector_credential_vault import (
    AuthType,
    CredentialVaultContractService,
    CredentialVaultInput,
)
from erpguard.product.erp_fingerprinting_plan import (
    ERPFingerprintingPlanService,
    FingerprintingPlanInput,
)
from erpguard.product.safe_discovery_audit import SafeDiscoveryAuditService
from erpguard.product.safe_discovery_plan import (
    SafeDiscoveryPlanInput,
    SafeDiscoveryPlanService,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _fingerprint(db, *, password="audit-secret"):
    create_connector_setup_session(
        db,
        session_id="csess_sda",
        connector_name="odoo_audit",
        erp_url="https://audit.odoo.com",
        erp_url_host="audit.odoo.com",
        environment_type="production",
        submitted_by="operator_1",
        status="draft",
        credential_mode="not_provided",
        credential_ref=None,
        detected_adapter_type=None,
        blocking_reasons_json="[]",
    )
    credential = CredentialVaultContractService(db).seal_credential(
        CredentialVaultInput(
            setup_session_id="csess_sda",
            auth_type=AuthType.PASSWORD,
            username="admin@example.com",
            password=password,
            submitted_by="operator_1",
        )
    )
    return ERPFingerprintingPlanService(db).create_plan(
        FingerprintingPlanInput(
            setup_session_id="csess_sda",
            credential_ref=credential.credential_ref,
            created_by="operator_1",
        )
    )


def test_audit_records_safe_discovery_plan_created(db):
    fingerprint = _fingerprint(db)

    result = SafeDiscoveryPlanService(db).create_plan(
        SafeDiscoveryPlanInput(
            fingerprint_plan_id=fingerprint.fingerprint_plan_id,
            created_by="operator_1",
        )
    )

    audit = SafeDiscoveryAuditService(db).get_audit()
    created = [
        event
        for event in audit.events
        if event["event_type"] == "safe_discovery_plan_created"
    ]
    assert created
    assert created[0]["discovery_plan_id"] == result.discovery_plan_id


def test_audit_records_blocked_request(db):
    SafeDiscoveryPlanService(db).create_plan(
        SafeDiscoveryPlanInput(
            fingerprint_plan_id="fplan_missing",
            created_by="operator_1",
        )
    )

    audit = SafeDiscoveryAuditService(db).get_audit()

    assert any(
        event["event_type"] == "safe_discovery_plan_blocked"
        and event["status"] == "blocked"
        for event in audit.events
    )


def test_audit_does_not_contain_raw_secret(db):
    fingerprint = _fingerprint(db, password="never-log-this-secret")

    SafeDiscoveryPlanService(db).create_plan(
        SafeDiscoveryPlanInput(
            fingerprint_plan_id=fingerprint.fingerprint_plan_id,
            created_by="operator_1",
        )
    )

    audit = SafeDiscoveryAuditService(db).get_audit()

    assert "never-log-this-secret" not in str(audit.events)
