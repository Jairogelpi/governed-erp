"""Tests for Sprint 56 — ERP Fingerprinting Plan service.

Covers: plan creation with sealed credential, blocking rules,
adapter candidate heuristics, planned checks, risk summary,
safety invariants (no network/login/schema/capability/activation).
"""

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


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _make_setup_session(db, session_id="csess_fp1", connector_name="odoo_test"):
    return create_connector_setup_session(
        db,
        session_id=session_id,
        connector_name=connector_name,
        erp_url="https://demo.odoo.com",
        erp_url_host="demo.odoo.com",
        environment_type="production",
        submitted_by="operator_1",
        status="draft",
        credential_mode="not_provided",
        credential_ref=None,
        detected_adapter_type=None,
        blocking_reasons_json="[]",
    )


def _seal_credential(db, session_id="csess_fp1"):
    vault = CredentialVaultContractService(db)
    result = vault.seal_credential(
        CredentialVaultInput(
            setup_session_id=session_id,
            auth_type=AuthType.PASSWORD,
            username="admin@example.com",
            password="test-password",
            submitted_by="operator_1",
        )
    )
    return result.credential_ref


# --- Plan creation ---


def test_creates_plan_for_setup_session_with_sealed_credential(db):
    _make_setup_session(db)
    cred_ref = _seal_credential(db)

    # Update setup session with credential ref
    from erpguard.db.repositories import update_connector_setup_session

    update_connector_setup_session(
        db,
        "csess_fp1",
        credential_ref=cred_ref,
        credential_mode="vault_reference_only",
        status="ready_for_fingerprint",
    )

    service = ERPFingerprintingPlanService(db)
    result = service.create_plan(
        FingerprintingPlanInput(
            setup_session_id="csess_fp1",
            credential_ref=cred_ref,
            created_by="operator_1",
        )
    )
    assert result.status == "planned"
    assert result.fingerprint_plan_id.startswith("fplan_")
    assert result.will_connect is False
    assert result.external_http_performed is False
    assert result.login_attempted is False
    assert result.fingerprint_performed is False
    assert result.schema_inspection_performed is False
    assert result.capability_generation_performed is False
    assert result.read_only_activation_performed is False
    assert result.credentials_exposed is False
    assert result.raw_secret_accessed is False


def test_requires_setup_session(db):
    service = ERPFingerprintingPlanService(db)
    result = service.create_plan(
        FingerprintingPlanInput(
            setup_session_id="csess_nonexistent",
            credential_ref="cred_test",
            created_by="operator_1",
        )
    )
    assert result.status == "blocked"
    assert "setup_session_not_found" in result.blocking_reasons


def test_blocks_blocked_session(db):
    create_connector_setup_session(
        db,
        session_id="csess_blocked",
        connector_name="odoo_test",
        erp_url="not-a-url",
        erp_url_host="",
        environment_type="production",
        submitted_by="operator_1",
        status="blocked",
        credential_mode="not_provided",
        credential_ref=None,
        detected_adapter_type=None,
        blocking_reasons_json='["unsafe_url_scheme"]',
    )
    service = ERPFingerprintingPlanService(db)
    result = service.create_plan(
        FingerprintingPlanInput(
            setup_session_id="csess_blocked",
            credential_ref="cred_test",
            created_by="operator_1",
        )
    )
    assert result.status == "blocked"
    assert "setup_session_blocked" in result.blocking_reasons


def test_blocks_missing_credential_ref(db):
    _make_setup_session(db)
    service = ERPFingerprintingPlanService(db)
    result = service.create_plan(
        FingerprintingPlanInput(
            setup_session_id="csess_fp1",
            credential_ref="",
            created_by="operator_1",
        )
    )
    assert result.status == "blocked"
    assert "credential_ref_required" in result.blocking_reasons


def test_blocks_credential_ref_mismatch(db):
    _make_setup_session(db)
    service = ERPFingerprintingPlanService(db)
    result = service.create_plan(
        FingerprintingPlanInput(
            setup_session_id="csess_fp1",
            credential_ref="cred_wrong",
            created_by="operator_1",
        )
    )
    assert result.status == "blocked"
    assert "credential_ref_mismatch" in result.blocking_reasons


def test_blocks_revoked_credential(db):
    _make_setup_session(db)
    cred_ref = _seal_credential(db)
    from erpguard.db.repositories import update_connector_setup_session

    update_connector_setup_session(
        db,
        "csess_fp1",
        credential_ref=cred_ref,
        credential_mode="vault_reference_only",
        status="ready_for_fingerprint",
    )

    vault = CredentialVaultContractService(db)
    vault.revoke_credential(cred_ref, revoked_by="operator_1")

    service = ERPFingerprintingPlanService(db)
    result = service.create_plan(
        FingerprintingPlanInput(
            setup_session_id="csess_fp1",
            credential_ref=cred_ref,
            created_by="operator_1",
        )
    )
    assert result.status == "blocked"
    assert "credential_revoked" in result.blocking_reasons


def test_blocks_credential_not_found(db):
    _make_setup_session(db)
    from erpguard.db.repositories import update_connector_setup_session

    # Set a fake credential ref that doesn't exist in vault
    update_connector_setup_session(
        db,
        "csess_fp1",
        credential_ref="cred_nonexistent",
        credential_mode="vault_reference_only",
        status="ready_for_fingerprint",
    )

    service = ERPFingerprintingPlanService(db)
    result = service.create_plan(
        FingerprintingPlanInput(
            setup_session_id="csess_fp1",
            credential_ref="cred_nonexistent",
            created_by="operator_1",
        )
    )
    assert result.status == "blocked"
    assert "credential_not_found" in result.blocking_reasons


# --- Adapter candidate heuristics ---


def test_detects_odoo_candidate_from_host(db):
    _make_setup_session(db, connector_name="odoo_prod")
    cred_ref = _seal_credential(db)
    from erpguard.db.repositories import update_connector_setup_session

    update_connector_setup_session(
        db,
        "csess_fp1",
        credential_ref=cred_ref,
        credential_mode="vault_reference_only",
        status="ready_for_fingerprint",
    )

    service = ERPFingerprintingPlanService(db)
    result = service.create_plan(
        FingerprintingPlanInput(
            setup_session_id="csess_fp1",
            credential_ref=cred_ref,
            created_by="operator_1",
        )
    )
    assert result.status == "planned"
    adapter_types = [c["adapter_type"] for c in result.adapter_candidates]
    assert "odoo" in adapter_types


def test_detects_holded_candidate(db):
    create_connector_setup_session(
        db,
        session_id="csess_holded2",
        connector_name="holded_main",
        erp_url="https://app.holded.com",
        erp_url_host="app.holded.com",
        environment_type="production",
        submitted_by="operator_1",
        status="draft",
        credential_mode="not_provided",
        credential_ref=None,
        detected_adapter_type=None,
        blocking_reasons_json="[]",
    )
    vault = CredentialVaultContractService(db)
    cred = vault.seal_credential(
        CredentialVaultInput(
            setup_session_id="csess_holded2",
            auth_type=AuthType.API_KEY,
            api_key="hk_live_abc123",
            submitted_by="operator_1",
        )
    )
    update_connector_setup_session(
        db,
        "csess_holded2",
        credential_ref=cred.credential_ref,
        credential_mode="vault_reference_only",
        status="ready_for_fingerprint",
    )
    service = ERPFingerprintingPlanService(db)
    result = service.create_plan(
        FingerprintingPlanInput(
            setup_session_id="csess_holded2",
            credential_ref=cred.credential_ref,
            created_by="operator_1",
        )
    )
    adapter_types = [c["adapter_type"] for c in result.adapter_candidates]
    assert "holded" in adapter_types


def test_detects_sap_candidate_from_host(db):
    create_connector_setup_session(
        db,
        session_id="csess_sap",
        connector_name="sap_erp",
        erp_url="https://sap.example.com",
        erp_url_host="sap.example.com",
        environment_type="production",
        submitted_by="operator_1",
        status="draft",
        credential_mode="not_provided",
        credential_ref=None,
        detected_adapter_type=None,
        blocking_reasons_json="[]",
    )
    vault = CredentialVaultContractService(db)
    cred = vault.seal_credential(
        CredentialVaultInput(
            setup_session_id="csess_sap",
            auth_type=AuthType.PASSWORD,
            username="admin",
            password="sap-pass",
            submitted_by="operator_1",
        )
    )
    from erpguard.db.repositories import update_connector_setup_session

    update_connector_setup_session(
        db,
        "csess_sap",
        credential_ref=cred.credential_ref,
        credential_mode="vault_reference_only",
        status="ready_for_fingerprint",
    )

    service = ERPFingerprintingPlanService(db)
    result = service.create_plan(
        FingerprintingPlanInput(
            setup_session_id="csess_sap",
            credential_ref=cred.credential_ref,
            created_by="operator_1",
        )
    )
    adapter_types = [c["adapter_type"] for c in result.adapter_candidates]
    assert "sap" in adapter_types


def test_unknown_host_returns_custom_rest_and_unknown(db):
    create_connector_setup_session(
        db,
        session_id="csess_unknown",
        connector_name="my_custom_erp",
        erp_url="https://erp.mycompany.com",
        erp_url_host="erp.mycompany.com",
        environment_type="production",
        submitted_by="operator_1",
        status="draft",
        credential_mode="not_provided",
        credential_ref=None,
        detected_adapter_type=None,
        blocking_reasons_json="[]",
    )
    vault = CredentialVaultContractService(db)
    cred = vault.seal_credential(
        CredentialVaultInput(
            setup_session_id="csess_unknown",
            auth_type=AuthType.API_KEY,
            api_key="ak_12345",
            submitted_by="operator_1",
        )
    )
    from erpguard.db.repositories import update_connector_setup_session

    update_connector_setup_session(
        db,
        "csess_unknown",
        credential_ref=cred.credential_ref,
        credential_mode="vault_reference_only",
        status="ready_for_fingerprint",
    )

    service = ERPFingerprintingPlanService(db)
    result = service.create_plan(
        FingerprintingPlanInput(
            setup_session_id="csess_unknown",
            credential_ref=cred.credential_ref,
            created_by="operator_1",
        )
    )
    adapter_types = [c["adapter_type"] for c in result.adapter_candidates]
    assert "custom_rest" in adapter_types
    assert "unknown" in adapter_types


def test_manual_hint_odoo(db):
    create_connector_setup_session(
        db,
        session_id="csess_hint",
        connector_name="my_erp",
        erp_url="https://erp.mycompany.com",
        erp_url_host="erp.mycompany.com",
        environment_type="production",
        submitted_by="operator_1",
        status="draft",
        credential_mode="not_provided",
        credential_ref=None,
        detected_adapter_type=None,
        blocking_reasons_json="[]",
    )
    vault = CredentialVaultContractService(db)
    cred = vault.seal_credential(
        CredentialVaultInput(
            setup_session_id="csess_hint",
            auth_type=AuthType.TOKEN,
            token="tok_12345",
            submitted_by="operator_1",
        )
    )
    from erpguard.db.repositories import update_connector_setup_session

    update_connector_setup_session(
        db,
        "csess_hint",
        credential_ref=cred.credential_ref,
        credential_mode="vault_reference_only",
        status="ready_for_fingerprint",
    )

    service = ERPFingerprintingPlanService(db)
    result = service.create_plan(
        FingerprintingPlanInput(
            setup_session_id="csess_hint",
            credential_ref=cred.credential_ref,
            created_by="operator_1",
            manual_hint="odoo",
        )
    )
    adapter_types = [c["adapter_type"] for c in result.adapter_candidates]
    assert "odoo" in adapter_types


# --- Planned checks are plan_only ---


def test_planned_checks_are_plan_only(db):
    _make_setup_session(db)
    cred_ref = _seal_credential(db)
    from erpguard.db.repositories import update_connector_setup_session

    update_connector_setup_session(
        db,
        "csess_fp1",
        credential_ref=cred_ref,
        credential_mode="vault_reference_only",
        status="ready_for_fingerprint",
    )

    service = ERPFingerprintingPlanService(db)
    result = service.create_plan(
        FingerprintingPlanInput(
            setup_session_id="csess_fp1",
            credential_ref=cred_ref,
            created_by="operator_1",
        )
    )
    for check in result.planned_checks:
        assert check["method"] == "plan_only"
        assert check["status"] == "planned"


def test_planned_checks_do_not_perform_network(db):
    _make_setup_session(db)
    cred_ref = _seal_credential(db)
    from erpguard.db.repositories import update_connector_setup_session

    update_connector_setup_session(
        db,
        "csess_fp1",
        credential_ref=cred_ref,
        credential_mode="vault_reference_only",
        status="ready_for_fingerprint",
    )

    service = ERPFingerprintingPlanService(db)
    result = service.create_plan(
        FingerprintingPlanInput(
            setup_session_id="csess_fp1",
            credential_ref=cred_ref,
            created_by="operator_1",
        )
    )
    # would_require_network tracks what would happen in the future, not what was done
    assert result.will_connect is False
    assert result.external_http_performed is False


# --- Safety invariants ---


def test_all_safety_flags_are_false(db):
    _make_setup_session(db)
    cred_ref = _seal_credential(db)
    from erpguard.db.repositories import update_connector_setup_session

    update_connector_setup_session(
        db,
        "csess_fp1",
        credential_ref=cred_ref,
        credential_mode="vault_reference_only",
        status="ready_for_fingerprint",
    )

    service = ERPFingerprintingPlanService(db)
    result = service.create_plan(
        FingerprintingPlanInput(
            setup_session_id="csess_fp1",
            credential_ref=cred_ref,
            created_by="operator_1",
        )
    )
    assert result.will_connect is False
    assert result.external_http_performed is False
    assert result.login_attempted is False
    assert result.fingerprint_performed is False
    assert result.schema_inspection_performed is False
    assert result.capability_generation_performed is False
    assert result.read_only_activation_performed is False
    assert result.credentials_exposed is False
    assert result.raw_secret_accessed is False
