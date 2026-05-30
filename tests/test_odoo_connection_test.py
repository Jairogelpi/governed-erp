"""Tests for Sprint 75 - controlled Odoo connection test."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from erpguard.db.models import Base
from erpguard.db.repositories import (
    create_connector_setup_session,
    get_odoo_read_only_adapter_session_by_id,
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
from erpguard.product.generated_capability_set import (
    GeneratedCapabilityInput,
    GeneratedCapabilitySetService,
)
from erpguard.product.odoo_connection_test import (
    OdooConnectionTestInput,
    OdooConnectionTestService,
)
from erpguard.product.odoo_read_only_adapter import (
    OdooReadOnlyAdapterService,
    OdooReadOnlyConnectionIntent,
)
from erpguard.product.read_only_connector_activation import (
    ReadOnlyActivationApprovalInput,
    ReadOnlyActivationRequestInput,
    ReadOnlyConnectorActivationService,
)
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


class MockOdooConnectionClient:
    def __init__(self, *, succeeds=True, version="19.0-mock"):
        self.succeeds = succeeds
        self.version = version
        self.calls = []

    def test_authentication(self, *, adapter_session, credential_metadata):
        self.calls.append(
            {
                "adapter_session_id": adapter_session.adapter_session_id,
                "credential_ref": credential_metadata.credential_ref,
            }
        )
        if not self.succeeds:
            return {"login_succeeded": False, "blocking_reason": "authentication_failed"}
        return {"login_succeeded": True, "odoo_server_version": self.version}


def _adapter_session(db, *, session_id="csess_odoo_ct", secret="odoo-ct-secret"):
    create_connector_setup_session(
        db,
        session_id=session_id,
        connector_name="odoo_connection_test",
        erp_url="https://connection-test.odoo.com",
        erp_url_host="connection-test.odoo.com",
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
    activation = activation_service.approve(
        ReadOnlyActivationApprovalInput(
            activation_request_id=request.activation_request_id,
            approved_by="operator_1",
        )
    )
    return OdooReadOnlyAdapterService(db).prepare_session(
        OdooReadOnlyConnectionIntent(
            activation_id=activation.activation_id,
            created_by="operator_1",
        )
    )


def _run(db, adapter_session_id, *, allow_network_test=False, client=None):
    return OdooConnectionTestService(db, connection_client=client).run_test(
        OdooConnectionTestInput(
            adapter_session_id=adapter_session_id,
            requested_by="operator_1",
            allow_network_test=allow_network_test,
        )
    )


def test_blocks_by_default_without_network_or_login(db):
    adapter_session = _adapter_session(db)

    result = _run(db, adapter_session.adapter_session_id)

    assert result.status == "blocked"
    assert "network_test_not_allowed" in result.blocking_reasons
    assert result.network_test_allowed is False
    assert result.external_http_performed is False
    assert result.login_attempted is False
    assert result.odoo_rpc_performed is False


def test_blocks_missing_adapter_session(db):
    result = _run(db, "odoo_ro_missing", allow_network_test=True)

    assert result.status == "blocked"
    assert "adapter_session_not_found" in result.blocking_reasons


def test_blocks_non_prepared_adapter_session(db):
    adapter_session = _adapter_session(db, session_id="csess_odoo_ct_blocked")
    row = get_odoo_read_only_adapter_session_by_id(db, adapter_session.adapter_session_id)
    row.status = "blocked"
    db.commit()

    result = _run(db, adapter_session.adapter_session_id, allow_network_test=True)

    assert result.status == "blocked"
    assert "adapter_session_not_prepared" in result.blocking_reasons


def test_blocks_non_odoo_adapter_type(db):
    adapter_session = _adapter_session(db, session_id="csess_odoo_ct_type")
    row = get_odoo_read_only_adapter_session_by_id(db, adapter_session.adapter_session_id)
    row.adapter_type = "sap"
    db.commit()

    result = _run(db, adapter_session.adapter_session_id, allow_network_test=True)

    assert result.status == "blocked"
    assert "adapter_type_not_odoo" in result.blocking_reasons


def test_blocks_mode_not_read_only(db):
    adapter_session = _adapter_session(db, session_id="csess_odoo_ct_mode")
    row = get_odoo_read_only_adapter_session_by_id(db, adapter_session.adapter_session_id)
    row.mode = "write"
    db.commit()

    result = _run(db, adapter_session.adapter_session_id, allow_network_test=True)

    assert result.status == "blocked"
    assert "mode_not_read_only" in result.blocking_reasons


def test_blocks_credential_not_found(db):
    adapter_session = _adapter_session(db, session_id="csess_odoo_ct_missing_cred")
    row = get_odoo_read_only_adapter_session_by_id(db, adapter_session.adapter_session_id)
    row.credential_ref = "cred_missing"
    db.commit()

    result = _run(db, adapter_session.adapter_session_id, allow_network_test=True)

    assert result.status == "blocked"
    assert "credential_not_found" in result.blocking_reasons


def test_blocks_credential_revoked(db):
    adapter_session = _adapter_session(db, session_id="csess_odoo_ct_revoked")
    CredentialVaultContractService(db).revoke_credential(
        adapter_session.credential_ref, revoked_by="operator_1"
    )

    result = _run(db, adapter_session.adapter_session_id, allow_network_test=True)

    assert result.status == "blocked"
    assert "credential_revoked" in result.blocking_reasons


def test_successful_mocked_connection_sets_only_connection_flags(db):
    adapter_session = _adapter_session(db)
    client = MockOdooConnectionClient(succeeds=True, version="19.0-safe")

    result = _run(
        db,
        adapter_session.adapter_session_id,
        allow_network_test=True,
        client=client,
    )

    assert result.connection_test_id.startswith("odoo_ct_")
    assert result.status == "passed"
    assert result.external_http_performed is True
    assert result.login_attempted is True
    assert result.login_succeeded is True
    assert result.odoo_rpc_performed is True
    assert result.odoo_server_version == "19.0-safe"
    assert result.business_data_read is False
    assert result.schema_inspection_performed is False
    assert result.permission_inspection_performed is False
    assert result.odoo_write_performed is False
    assert result.credentials_exposed is False
    assert result.raw_secret_accessed is False
    assert client.calls == [
        {
            "adapter_session_id": adapter_session.adapter_session_id,
            "credential_ref": adapter_session.credential_ref,
        }
    ]


def test_failed_mocked_authentication_is_recorded_without_business_access(db):
    adapter_session = _adapter_session(db)

    result = _run(
        db,
        adapter_session.adapter_session_id,
        allow_network_test=True,
        client=MockOdooConnectionClient(succeeds=False),
    )

    assert result.status == "failed"
    assert "authentication_failed" in result.blocking_reasons
    assert result.external_http_performed is True
    assert result.login_attempted is True
    assert result.login_succeeded is False
    assert result.business_data_read is False
    assert result.odoo_write_performed is False


def test_public_response_does_not_include_raw_secret(db):
    adapter_session = _adapter_session(db, secret="super-private-odoo-password")

    result = _run(
        db,
        adapter_session.adapter_session_id,
        allow_network_test=True,
        client=MockOdooConnectionClient(),
    )

    payload = str(result.__dict__)
    assert "super-private-odoo-password" not in payload
    assert "raw_secret" not in payload.replace("raw_secret_accessed", "")
