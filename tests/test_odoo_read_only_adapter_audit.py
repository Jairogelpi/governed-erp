"""Tests for Sprint 74 - Odoo read-only adapter shell audit."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from erpguard.db.models import Base
from erpguard.db.repositories import create_connector_setup_session, update_connector_setup_session
from erpguard.product.connector_credential_vault import AuthType, CredentialVaultContractService, CredentialVaultInput
from erpguard.product.erp_fingerprinting_plan import ERPFingerprintingPlanService, FingerprintingPlanInput
from erpguard.product.generated_capability_set import GeneratedCapabilityInput, GeneratedCapabilitySetService
from erpguard.product.odoo_read_only_adapter import OdooReadOnlyAdapterService, OdooReadOnlyConnectionIntent
from erpguard.product.odoo_read_only_adapter_audit import OdooReadOnlyAdapterAuditService
from erpguard.product.read_only_connector_activation import (
    ReadOnlyActivationApprovalInput,
    ReadOnlyActivationRequestInput,
    ReadOnlyConnectorActivationService,
)
from erpguard.product.safe_discovery_plan import SafeDiscoveryPlanInput, SafeDiscoveryPlanService


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _activation(db, *, secret="odoo-audit-secret"):
    create_connector_setup_session(
        db,
        session_id="csess_odoo_ro_audit",
        connector_name="odoo_adapter_audit",
        erp_url="https://adapter-audit.odoo.com",
        erp_url_host="adapter-audit.odoo.com",
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
            setup_session_id="csess_odoo_ro_audit",
            auth_type=AuthType.PASSWORD,
            username="admin@example.com",
            password=secret,
            submitted_by="operator_1",
        )
    )
    update_connector_setup_session(
        db,
        "csess_odoo_ro_audit",
        credential_ref=credential.credential_ref,
        credential_mode="vault_reference_only",
        status="ready_for_fingerprint",
    )
    fingerprint = ERPFingerprintingPlanService(db).create_plan(
        FingerprintingPlanInput(
            setup_session_id="csess_odoo_ro_audit",
            credential_ref=credential.credential_ref,
            created_by="operator_1",
        )
    )
    discovery = SafeDiscoveryPlanService(db).create_plan(
        SafeDiscoveryPlanInput(fingerprint_plan_id=fingerprint.fingerprint_plan_id)
    )
    capability_set = GeneratedCapabilitySetService(db).generate(
        GeneratedCapabilityInput(discovery_plan_id=discovery.discovery_plan_id)
    )
    activation_service = ReadOnlyConnectorActivationService(db)
    request = activation_service.create_request(
        ReadOnlyActivationRequestInput(capability_set_id=capability_set.capability_set_id)
    )
    return activation_service.approve(
        ReadOnlyActivationApprovalInput(
            activation_request_id=request.activation_request_id,
            approved_by="operator_1",
        )
    )


def _prepare(db, activation_id):
    return OdooReadOnlyAdapterService(db).prepare_session(
        OdooReadOnlyConnectionIntent(activation_id=activation_id, created_by="operator_1")
    )


def test_audit_records_adapter_session_created(db):
    activation = _activation(db)
    result = _prepare(db, activation.activation_id)

    audit = OdooReadOnlyAdapterAuditService(db).get_audit()

    assert any(
        event["event_type"] == "odoo_read_only_adapter_session_created"
        and event["adapter_session_id"] == result.adapter_session_id
        for event in audit.events
    )


def test_audit_records_blocked_session(db):
    _prepare(db, "roconn_missing")

    audit = OdooReadOnlyAdapterAuditService(db).get_audit()

    assert any(
        event["event_type"] == "odoo_read_only_adapter_session_blocked"
        and event["status"] == "blocked"
        for event in audit.events
    )


def test_audit_does_not_contain_raw_secret(db):
    activation = _activation(db, secret="never-odoo-audit")
    _prepare(db, activation.activation_id)

    audit = OdooReadOnlyAdapterAuditService(db).get_audit()

    assert "never-odoo-audit" not in str(audit.events)
