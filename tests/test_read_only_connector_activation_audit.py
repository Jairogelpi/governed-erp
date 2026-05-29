"""Tests for Sprint 59 - Read-Only Connector Activation audit."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from erpguard.db.models import Base
from erpguard.db.repositories import create_connector_setup_session, update_connector_setup_session
from erpguard.product.connector_credential_vault import AuthType, CredentialVaultContractService, CredentialVaultInput
from erpguard.product.erp_fingerprinting_plan import ERPFingerprintingPlanService, FingerprintingPlanInput
from erpguard.product.generated_capability_set import GeneratedCapabilityInput, GeneratedCapabilitySetService
from erpguard.product.read_only_connector_activation import (
    ReadOnlyActivationApprovalInput,
    ReadOnlyActivationRequestInput,
    ReadOnlyConnectorActivationService,
)
from erpguard.product.read_only_connector_activation_audit import ReadOnlyConnectorActivationAuditService
from erpguard.product.safe_discovery_plan import SafeDiscoveryPlanInput, SafeDiscoveryPlanService


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _capability_set(db, *, secret="audit-ro-secret"):
    create_connector_setup_session(
        db,
        session_id="csess_ro_audit",
        connector_name="odoo_ro_audit",
        erp_url="https://readonly-audit.odoo.com",
        erp_url_host="readonly-audit.odoo.com",
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
            setup_session_id="csess_ro_audit",
            auth_type=AuthType.PASSWORD,
            username="admin@example.com",
            password=secret,
            submitted_by="operator_1",
        )
    )
    update_connector_setup_session(
        db,
        "csess_ro_audit",
        credential_ref=credential.credential_ref,
        credential_mode="vault_reference_only",
        status="ready_for_fingerprint",
    )
    fingerprint = ERPFingerprintingPlanService(db).create_plan(
        FingerprintingPlanInput(
            setup_session_id="csess_ro_audit",
            credential_ref=credential.credential_ref,
            created_by="operator_1",
        )
    )
    discovery = SafeDiscoveryPlanService(db).create_plan(
        SafeDiscoveryPlanInput(
            fingerprint_plan_id=fingerprint.fingerprint_plan_id,
            created_by="operator_1",
        )
    )
    return GeneratedCapabilitySetService(db).generate(
        GeneratedCapabilityInput(
            discovery_plan_id=discovery.discovery_plan_id,
            created_by="operator_1",
        )
    )


def _request(db, capability_set_id):
    return ReadOnlyConnectorActivationService(db).create_request(
        ReadOnlyActivationRequestInput(
            capability_set_id=capability_set_id,
            requested_by="operator_1",
            mode="read_only",
        )
    )


def test_audit_records_request_created_approval_and_activation(db):
    capability_set = _capability_set(db)
    request = _request(db, capability_set.capability_set_id)
    ReadOnlyConnectorActivationService(db).approve(
        ReadOnlyActivationApprovalInput(
            activation_request_id=request.activation_request_id,
            approved_by="operator_1",
        )
    )

    audit = ReadOnlyConnectorActivationAuditService(db).get_audit()
    event_types = {event["event_type"] for event in audit.events}

    assert "read_only_activation_request_created" in event_types
    assert "read_only_activation_approved" in event_types
    assert "read_only_connector_activated" in event_types


def test_audit_records_blocked_request(db):
    _request(db, "gcaps_missing")

    audit = ReadOnlyConnectorActivationAuditService(db).get_audit()

    assert any(
        event["event_type"] == "read_only_activation_request_blocked"
        and event["status"] == "blocked"
        for event in audit.events
    )


def test_audit_does_not_contain_raw_secret(db):
    capability_set = _capability_set(db, secret="never-audit-ro")
    request = _request(db, capability_set.capability_set_id)
    ReadOnlyConnectorActivationService(db).approve(
        ReadOnlyActivationApprovalInput(
            activation_request_id=request.activation_request_id,
            approved_by="operator_1",
        )
    )

    audit = ReadOnlyConnectorActivationAuditService(db).get_audit()

    assert "never-audit-ro" not in str(audit.events)
