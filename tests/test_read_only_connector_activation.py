"""Tests for Sprint 59 - Read-Only Connector Activation."""

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from erpguard.db.models import Base
from erpguard.db.repositories import (
    create_connector_setup_session,
    get_generated_capability_set_by_id,
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


def _capability_set(db, *, session_id="csess_ro1", secret="ro-secret"):
    create_connector_setup_session(
        db,
        session_id=session_id,
        connector_name="odoo_ro",
        erp_url="https://readonly.odoo.com",
        erp_url_host="readonly.odoo.com",
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


def _request(db, capability_set_id, mode="read_only"):
    return ReadOnlyConnectorActivationService(db).create_request(
        ReadOnlyActivationRequestInput(
            capability_set_id=capability_set_id,
            requested_by="operator_1",
            mode=mode,
        )
    )


def test_creates_activation_request_from_generated_capability_set(db):
    capability_set = _capability_set(db)

    result = _request(db, capability_set.capability_set_id)

    assert result.activation_request_id.startswith("roactreq_")
    assert result.status == "requested"
    assert result.requires_human_approval is True
    assert result.will_connect is False
    assert result.can_read_real_erp is False
    assert result.can_write_real_erp is False


def test_blocks_missing_capability_set(db):
    result = _request(db, "gcaps_missing")

    assert result.status == "blocked"
    assert "capability_set_not_found" in result.blocking_reasons


def test_blocks_non_generated_capability_set(db):
    capability_set = _capability_set(db, session_id="csess_ro_blocked")
    row = get_generated_capability_set_by_id(db, capability_set.capability_set_id)
    row.status = "blocked"
    db.commit()

    result = _request(db, capability_set.capability_set_id)

    assert result.status == "blocked"
    assert "capability_set_not_ready" in result.blocking_reasons


def test_blocks_revoked_credential(db):
    capability_set = _capability_set(db, session_id="csess_ro_revoked")
    CredentialVaultContractService(db).revoke_credential(
        capability_set.credential_ref, revoked_by="operator_1"
    )

    result = _request(db, capability_set.capability_set_id)

    assert result.status == "blocked"
    assert "credential_revoked" in result.blocking_reasons


def test_blocks_executable_write_capability_injected(db):
    capability_set = _capability_set(db, session_id="csess_ro_exec")
    row = get_generated_capability_set_by_id(db, capability_set.capability_set_id)
    capabilities = json.loads(row.capabilities_json)
    capabilities.append(
        {
            "operation_type": "update_object",
            "object_type": "partner",
            "supports_execution": True,
            "supported": True,
            "safety_tier": "write",
        }
    )
    row.capabilities_json = json.dumps(capabilities)
    db.commit()

    result = _request(db, capability_set.capability_set_id)

    assert result.status == "blocked"
    assert "executable_write_capability_detected" in result.blocking_reasons


def test_blocks_requested_mode_other_than_read_only(db):
    capability_set = _capability_set(db)

    result = _request(db, capability_set.capability_set_id, mode="write")

    assert result.status == "blocked"
    assert "mode_not_allowed" in result.blocking_reasons


def test_approval_requires_existing_request(db):
    result = ReadOnlyConnectorActivationService(db).approve(
        ReadOnlyActivationApprovalInput(
            activation_request_id="roactreq_missing",
            approved_by="operator_1",
        )
    )

    assert result.status == "blocked"
    assert "activation_request_not_found" in result.blocking_reasons


def test_approval_requires_requested_status(db):
    capability_set = _capability_set(db)
    request = _request(db, capability_set.capability_set_id)
    service = ReadOnlyConnectorActivationService(db)
    service.approve(
        ReadOnlyActivationApprovalInput(
            activation_request_id=request.activation_request_id,
            approved_by="operator_1",
        )
    )

    result = service.approve(
        ReadOnlyActivationApprovalInput(
            activation_request_id=request.activation_request_id,
            approved_by="operator_1",
        )
    )

    assert result.status == "blocked"
    assert "activation_request_not_ready" in result.blocking_reasons


def test_approval_requires_actor(db):
    capability_set = _capability_set(db)
    request = _request(db, capability_set.capability_set_id)

    result = ReadOnlyConnectorActivationService(db).approve(
        ReadOnlyActivationApprovalInput(
            activation_request_id=request.activation_request_id,
            approved_by="",
        )
    )

    assert result.status == "blocked"
    assert "approval_actor_required" in result.blocking_reasons


def test_approval_creates_active_read_only_connector_artifact(db):
    capability_set = _capability_set(db)
    request = _request(db, capability_set.capability_set_id)

    result = ReadOnlyConnectorActivationService(db).approve(
        ReadOnlyActivationApprovalInput(
            activation_request_id=request.activation_request_id,
            approved_by="operator_1",
        )
    )

    assert result.activation_id.startswith("roconn_")
    assert result.status == "active_read_only"
    assert result.mode == "read_only"
    assert result.real_erp_connection_established is False
    assert result.real_erp_read_enabled is False
    assert result.real_erp_write_enabled is False


def test_all_safety_flags_remain_false(db):
    capability_set = _capability_set(db)
    request = _request(db, capability_set.capability_set_id)
    activation = ReadOnlyConnectorActivationService(db).approve(
        ReadOnlyActivationApprovalInput(
            activation_request_id=request.activation_request_id,
            approved_by="operator_1",
        )
    )

    for result in (request, activation):
        assert result.external_http_performed is False
        assert result.login_attempted is False
        assert result.browser_control_performed is False
        assert result.mcp_execution_performed is False
        assert result.scheduler_used is False
        assert result.credentials_exposed is False
        assert result.raw_secret_accessed is False


def test_activation_payload_does_not_contain_raw_secret(db):
    capability_set = _capability_set(db, secret="never-activate-this")
    request = _request(db, capability_set.capability_set_id)
    activation = ReadOnlyConnectorActivationService(db).approve(
        ReadOnlyActivationApprovalInput(
            activation_request_id=request.activation_request_id,
            approved_by="operator_1",
        )
    )

    assert "never-activate-this" not in json.dumps(request.__dict__)
    assert "never-activate-this" not in json.dumps(activation.__dict__)
