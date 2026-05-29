"""Tests for Sprint 74 - Odoo read-only adapter shell."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from erpguard.db.models import Base
from erpguard.db.repositories import (
    create_connector_setup_session,
    get_read_only_connector_activation_by_id,
    update_connector_setup_session,
)
from erpguard.product.connector_credential_vault import AuthType, CredentialVaultContractService, CredentialVaultInput
from erpguard.product.erp_fingerprinting_plan import ERPFingerprintingPlanService, FingerprintingPlanInput
from erpguard.product.generated_capability_set import GeneratedCapabilityInput, GeneratedCapabilitySetService
from erpguard.product.odoo_read_only_adapter import OdooReadOnlyAdapterService, OdooReadOnlyConnectionIntent
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


def _activation(db, *, session_id="csess_odoo_ro", secret="odoo-ro-secret"):
    create_connector_setup_session(
        db,
        session_id=session_id,
        connector_name="odoo_adapter_shell",
        erp_url="https://adapter-shell.odoo.com",
        erp_url_host="adapter-shell.odoo.com",
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
            setup_session_id=session_id,
            auth_type=AuthType.PASSWORD,
            username="admin@example.com",
            password=secret,
            submitted_by="operator_1",
        )
    )
    update_connector_setup_session(
        db,
        session_id,
        credential_ref=credential.credential_ref,
        credential_mode="vault_reference_only",
        status="ready_for_fingerprint",
    )
    fingerprint = ERPFingerprintingPlanService(db).create_plan(
        FingerprintingPlanInput(
            setup_session_id=session_id,
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
        OdooReadOnlyConnectionIntent(
            activation_id=activation_id,
            created_by="operator_1",
        )
    )


def test_creates_adapter_shell_from_active_read_only_activation(db):
    activation = _activation(db)

    result = _prepare(db, activation.activation_id)

    assert result.adapter_session_id.startswith("odoo_ro_")
    assert result.status == "prepared"
    assert result.can_connect_later is True
    assert result.will_connect_now is False
    assert result.adapter_type == "odoo"
    assert result.mode == "read_only"


def test_blocks_missing_activation(db):
    result = _prepare(db, "roconn_missing")

    assert result.status == "blocked"
    assert "activation_not_found" in result.blocking_reasons


def test_blocks_non_active_activation(db):
    activation = _activation(db, session_id="csess_odoo_ro_blocked")
    row = get_read_only_connector_activation_by_id(db, activation.activation_id)
    row.status = "revoked"
    db.commit()

    result = _prepare(db, activation.activation_id)

    assert result.status == "blocked"
    assert "activation_not_active_read_only" in result.blocking_reasons


def test_blocks_non_odoo_adapter_type(db):
    activation = _activation(db, session_id="csess_odoo_ro_type")
    row = get_read_only_connector_activation_by_id(db, activation.activation_id)
    row.adapter_type = "sap"
    db.commit()

    result = _prepare(db, activation.activation_id)

    assert result.status == "blocked"
    assert "adapter_type_not_odoo" in result.blocking_reasons


def test_blocks_mode_not_read_only(db):
    activation = _activation(db, session_id="csess_odoo_ro_mode")
    row = get_read_only_connector_activation_by_id(db, activation.activation_id)
    row.mode = "write"
    db.commit()

    result = _prepare(db, activation.activation_id)

    assert result.status == "blocked"
    assert "mode_not_read_only" in result.blocking_reasons


def test_blocks_missing_credential_ref(db):
    activation = _activation(db, session_id="csess_odoo_ro_no_cred")
    row = get_read_only_connector_activation_by_id(db, activation.activation_id)
    row.credential_ref = ""
    db.commit()

    result = _prepare(db, activation.activation_id)

    assert result.status == "blocked"
    assert "credential_ref_required" in result.blocking_reasons


def test_blocks_credential_not_found(db):
    activation = _activation(db, session_id="csess_odoo_ro_missing_cred")
    row = get_read_only_connector_activation_by_id(db, activation.activation_id)
    row.credential_ref = "cred_missing"
    db.commit()

    result = _prepare(db, activation.activation_id)

    assert result.status == "blocked"
    assert "credential_not_found" in result.blocking_reasons


def test_blocks_credential_revoked(db):
    activation = _activation(db, session_id="csess_odoo_ro_revoked")
    CredentialVaultContractService(db).revoke_credential(
        activation.credential_ref, revoked_by="operator_1"
    )

    result = _prepare(db, activation.activation_id)

    assert result.status == "blocked"
    assert "credential_revoked" in result.blocking_reasons


def test_all_shell_flags_are_false(db):
    activation = _activation(db)

    result = _prepare(db, activation.activation_id)

    assert result.external_http_performed is False
    assert result.login_attempted is False
    assert result.odoo_rpc_performed is False
    assert result.odoo_read_performed is False
    assert result.odoo_write_performed is False
    assert result.schema_inspection_performed is False
    assert result.permission_inspection_performed is False
    assert result.credentials_exposed is False
    assert result.raw_secret_accessed is False
