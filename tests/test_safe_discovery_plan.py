"""Tests for Sprint 57 - Safe Discovery Plan service."""

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from erpguard.db.models import Base
from erpguard.db.repositories import (
    create_connector_setup_session,
    update_connector_setup_session,
    get_erp_fingerprinting_plan_by_id,
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


def _create_fingerprinting_plan(
    db,
    *,
    session_id="csess_sd1",
    connector_name="odoo_safe",
    erp_url="https://safe.odoo.com",
    erp_url_host="safe.odoo.com",
    auth_type=AuthType.PASSWORD,
    secret="safe-secret",
    manual_hint=None,
):
    create_connector_setup_session(
        db,
        session_id=session_id,
        connector_name=connector_name,
        erp_url=erp_url,
        erp_url_host=erp_url_host,
        environment_type="production",
        submitted_by="operator_1",
        status="draft",
        credential_mode="not_provided",
        credential_ref=None,
        detected_adapter_type=None,
        blocking_reasons_json="[]",
    )
    vault = CredentialVaultContractService(db)
    credential_input = {
        "setup_session_id": session_id,
        "auth_type": auth_type,
        "submitted_by": "operator_1",
    }
    if auth_type == AuthType.API_KEY:
        credential_input["api_key"] = secret
    elif auth_type == AuthType.TOKEN:
        credential_input["token"] = secret
    else:
        credential_input["username"] = "admin@example.com"
        credential_input["password"] = secret
    credential = vault.seal_credential(CredentialVaultInput(**credential_input))
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
            manual_hint=manual_hint,
        )
    )
    return fingerprint


def _create_safe_plan(db, fingerprint_plan_id, selected_adapter_type=None):
    return SafeDiscoveryPlanService(db).create_plan(
        SafeDiscoveryPlanInput(
            fingerprint_plan_id=fingerprint_plan_id,
            selected_adapter_type=selected_adapter_type,
            created_by="operator_1",
        )
    )


def _object_types(result):
    return {obj["object_type"] for obj in result.read_only_surface["objects"]}


def test_creates_safe_discovery_plan_from_fingerprinting_plan(db):
    fingerprint = _create_fingerprinting_plan(db)

    result = _create_safe_plan(db, fingerprint.fingerprint_plan_id)

    assert result.status == "planned"
    assert result.discovery_plan_id.startswith("dplan_")
    assert result.fingerprint_plan_id == fingerprint.fingerprint_plan_id
    assert result.selected_adapter_type == "odoo"
    assert result.next_safe_step == "read_only_surface_review"


def test_selects_highest_confidence_adapter_when_omitted(db):
    fingerprint = _create_fingerprinting_plan(
        db,
        session_id="csess_sd_hint",
        connector_name="plain_erp",
        erp_url="https://erp.example.com",
        erp_url_host="erp.example.com",
        manual_hint="odoo",
    )

    result = _create_safe_plan(db, fingerprint.fingerprint_plan_id)

    assert result.selected_adapter_type == "odoo"


def test_accepts_explicit_selected_adapter_if_candidate_exists(db):
    fingerprint = _create_fingerprinting_plan(
        db,
        session_id="csess_sd_custom",
        connector_name="plain_erp",
        erp_url="https://erp.example.com",
        erp_url_host="erp.example.com",
    )

    result = _create_safe_plan(
        db, fingerprint.fingerprint_plan_id, selected_adapter_type="custom_rest"
    )

    assert result.status == "planned"
    assert result.selected_adapter_type == "custom_rest"


def test_blocks_unknown_fingerprinting_plan_id(db):
    result = _create_safe_plan(db, "fplan_missing")

    assert result.status == "blocked"
    assert "fingerprinting_plan_not_found" in result.blocking_reasons


def test_blocks_fingerprinting_plan_not_ready(db):
    fingerprint = _create_fingerprinting_plan(db, session_id="csess_sd_not_ready")
    row = get_erp_fingerprinting_plan_by_id(db, fingerprint.fingerprint_plan_id)
    row.status = "blocked"
    db.commit()

    result = _create_safe_plan(db, fingerprint.fingerprint_plan_id)

    assert result.status == "blocked"
    assert "fingerprinting_plan_not_ready" in result.blocking_reasons


def test_blocks_revoked_credential(db):
    fingerprint = _create_fingerprinting_plan(db, session_id="csess_sd_revoked")
    CredentialVaultContractService(db).revoke_credential(
        fingerprint.credential_ref, revoked_by="operator_1"
    )

    result = _create_safe_plan(db, fingerprint.fingerprint_plan_id)

    assert result.status == "blocked"
    assert "credential_revoked" in result.blocking_reasons


@pytest.mark.parametrize(
    ("adapter_type", "connector_name", "host", "expected_objects"),
    [
        (
            "odoo",
            "odoo_main",
            "demo.odoo.com",
            {
                "partner",
                "product",
                "sale_order",
                "invoice",
                "stock_item",
                "manufacturing_order",
            },
        ),
        (
            "holded",
            "holded_main",
            "app.holded.com",
            {"partner", "product", "invoice", "payment", "custom_object"},
        ),
        (
            "sap",
            "sap_main",
            "sap.example.com",
            {
                "partner",
                "product",
                "sale_order",
                "purchase_order",
                "stock_item",
                "journal_entry",
                "custom_object",
            },
        ),
        (
            "custom_rest",
            "custom_api",
            "api.example.com",
            {"custom_object"},
        ),
    ],
)
def test_adapter_static_surface_templates(
    db, adapter_type, connector_name, host, expected_objects
):
    fingerprint = _create_fingerprinting_plan(
        db,
        session_id=f"csess_sd_{adapter_type}",
        connector_name=connector_name,
        erp_url=f"https://{host}",
        erp_url_host=host,
    )

    result = _create_safe_plan(
        db, fingerprint.fingerprint_plan_id, selected_adapter_type=adapter_type
    )

    assert expected_objects.issubset(_object_types(result))


def test_all_fields_are_not_writable(db):
    fingerprint = _create_fingerprinting_plan(db)

    result = _create_safe_plan(db, fingerprint.fingerprint_plan_id)

    for field in result.read_only_surface["fields"]:
        assert field["writable_planned"] is False


def test_blocked_write_surface_blocks_all_write_like_operations(db):
    fingerprint = _create_fingerprinting_plan(db)

    result = _create_safe_plan(db, fingerprint.fingerprint_plan_id)

    blocked_ops = {op["operation_type"] for op in result.blocked_write_surface}
    assert {
        "create_object",
        "update_object",
        "delete_object",
        "post_document",
        "confirm_document",
        "reconcile_payment",
        "produce_manufacturing_order",
    }.issubset(blocked_ops)
    assert all(op["blocked"] is True for op in result.blocked_write_surface)


def test_planned_steps_are_plan_only_and_do_not_write(db):
    fingerprint = _create_fingerprinting_plan(db)

    result = _create_safe_plan(db, fingerprint.fingerprint_plan_id)

    for step in result.planned_discovery_steps:
        assert step["method"] == "plan_only"
        assert step["would_write_data"] is False
        assert step["status"] == "planned"


def test_all_sprint_57_safety_flags_are_false(db):
    fingerprint = _create_fingerprinting_plan(db)

    result = _create_safe_plan(db, fingerprint.fingerprint_plan_id)

    assert result.will_connect is False
    assert result.external_http_performed is False
    assert result.login_attempted is False
    assert result.schema_inspection_performed is False
    assert result.permission_inspection_performed is False
    assert result.sample_data_read is False
    assert result.capability_generation_performed is False
    assert result.read_only_activation_performed is False
    assert result.erp_write_performed is False
    assert result.credentials_exposed is False
    assert result.raw_secret_accessed is False


def test_persisted_plan_can_be_loaded(db):
    fingerprint = _create_fingerprinting_plan(db)
    result = _create_safe_plan(db, fingerprint.fingerprint_plan_id)

    loaded = SafeDiscoveryPlanService(db).get_plan(result.discovery_plan_id)

    assert loaded["discovery_plan_id"] == result.discovery_plan_id
    assert loaded["read_only_surface"]["objects"]
    assert loaded["permission_surface"]
    assert loaded["blocking_reasons"] == []


def test_persisted_json_contains_no_raw_secret(db):
    fingerprint = _create_fingerprinting_plan(db, secret="do-not-leak-me")
    result = _create_safe_plan(db, fingerprint.fingerprint_plan_id)

    loaded = SafeDiscoveryPlanService(db).get_plan(result.discovery_plan_id)

    assert "do-not-leak-me" not in json.dumps(loaded)
