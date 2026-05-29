"""Tests for Sprint 58 - generated capabilities from safe discovery."""

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from erpguard.db.models import Base
from erpguard.db.repositories import (
    create_connector_setup_session,
    get_safe_discovery_plan_by_id,
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


def _create_safe_discovery_plan(db, *, session_id="csess_gc1", secret="gc-secret"):
    create_connector_setup_session(
        db,
        session_id=session_id,
        connector_name="odoo_generated",
        erp_url="https://generated.odoo.com",
        erp_url_host="generated.odoo.com",
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
    return SafeDiscoveryPlanService(db).create_plan(
        SafeDiscoveryPlanInput(
            fingerprint_plan_id=fingerprint.fingerprint_plan_id,
            created_by="operator_1",
        )
    )


def _generate(db, discovery_plan_id):
    return GeneratedCapabilitySetService(db).generate(
        GeneratedCapabilityInput(
            discovery_plan_id=discovery_plan_id,
            created_by="operator_1",
        )
    )


def _capabilities_by_operation(result, operation_type):
    return [
        cap
        for cap in result.capabilities
        if cap["operation_type"] == operation_type
    ]


def test_generates_capability_set_from_odoo_safe_discovery_plan(db):
    discovery = _create_safe_discovery_plan(db)

    result = _generate(db, discovery.discovery_plan_id)

    assert result.status == "generated"
    assert result.capability_set_id.startswith("gcaps_")
    assert result.discovery_plan_id == discovery.discovery_plan_id
    assert result.adapter_type == "odoo"
    assert result.adapter_id.startswith("generated_odoo_")


def test_generates_read_search_schema_and_permission_capabilities(db):
    discovery = _create_safe_discovery_plan(db)

    result = _generate(db, discovery.discovery_plan_id)

    assert _capabilities_by_operation(result, "read_object")
    assert _capabilities_by_operation(result, "search_objects")
    schema_caps = _capabilities_by_operation(result, "inspect_schema")
    permission_caps = _capabilities_by_operation(result, "inspect_permissions")
    assert schema_caps
    assert permission_caps
    assert all(cap["safety_tier"] == "read_only" for cap in schema_caps)
    assert all(cap["supports_schema_inspection"] is True for cap in schema_caps)
    assert all(
        cap["supports_permission_inspection"] is True for cap in permission_caps
    )


def test_generated_capabilities_are_advisory_and_non_executable(db):
    discovery = _create_safe_discovery_plan(db)

    result = _generate(db, discovery.discovery_plan_id)

    for capability in result.capabilities:
        assert capability["supports_execution"] is False
        assert capability["is_advisory_only"] is True
        assert capability["will_execute"] is False
        assert capability["can_execute"] is False


def test_field_allowlists_are_read_only_and_exclude_redacted_fields(db):
    discovery = _create_safe_discovery_plan(db)

    result = _generate(db, discovery.discovery_plan_id)

    for capability in result.capabilities:
        assert capability["field_write_allowlist"] == []
        assert "external_reference" not in capability["field_read_allowlist"]
        assert {"id", "display_name"}.issubset(
            set(capability["field_read_allowlist"])
        )


def test_blocked_write_capabilities_are_generated_from_blocked_surface(db):
    discovery = _create_safe_discovery_plan(db)

    result = _generate(db, discovery.discovery_plan_id)

    blocked_ops = {cap["operation_type"] for cap in result.blocked_capabilities}
    assert {
        "create_object",
        "update_object",
        "delete_object",
        "post_document",
        "confirm_document",
        "reconcile_payment",
        "produce_manufacturing_order",
    }.issubset(blocked_ops)
    assert all(cap["supported"] is False for cap in result.blocked_capabilities)
    assert all(cap["blocked"] is True for cap in result.blocked_capabilities)
    assert all(
        "write_blocked_by_safe_discovery_plan" in cap["blocking_reasons"]
        for cap in result.blocked_capabilities
    )


def test_blocks_missing_safe_discovery_plan(db):
    result = _generate(db, "dplan_missing")

    assert result.status == "blocked"
    assert "safe_discovery_plan_not_found" in result.blocking_reasons


def test_blocks_non_planned_safe_discovery_plan(db):
    discovery = _create_safe_discovery_plan(db, session_id="csess_gc_blocked")
    row = get_safe_discovery_plan_by_id(db, discovery.discovery_plan_id)
    row.status = "blocked"
    db.commit()

    result = _generate(db, discovery.discovery_plan_id)

    assert result.status == "blocked"
    assert "safe_discovery_plan_not_ready" in result.blocking_reasons


def test_blocks_revoked_credential(db):
    discovery = _create_safe_discovery_plan(db, session_id="csess_gc_revoked")
    CredentialVaultContractService(db).revoke_credential(
        discovery.credential_ref, revoked_by="operator_1"
    )

    result = _generate(db, discovery.discovery_plan_id)

    assert result.status == "blocked"
    assert "credential_revoked" in result.blocking_reasons


def test_blocks_missing_read_only_surface(db):
    discovery = _create_safe_discovery_plan(db, session_id="csess_gc_no_surface")
    row = get_safe_discovery_plan_by_id(db, discovery.discovery_plan_id)
    row.read_only_surface_json = json.dumps({"objects": [], "fields": []})
    db.commit()

    result = _generate(db, discovery.discovery_plan_id)

    assert result.status == "blocked"
    assert "read_only_surface_required" in result.blocking_reasons


def test_policy_summary_and_safety_flags(db):
    discovery = _create_safe_discovery_plan(db)

    result = _generate(db, discovery.discovery_plan_id)

    assert result.policy_summary["is_advisory_only"] is True
    assert result.policy_summary["capability_generation_performed"] is True
    assert result.policy_summary["real_erp_touched"] is False
    assert result.is_advisory_only is True
    assert result.will_execute is False
    assert result.can_execute is False
    assert result.external_http_performed is False
    assert result.login_attempted is False
    assert result.schema_inspection_performed is False
    assert result.permission_inspection_performed is False
    assert result.sample_data_read is False
    assert result.capability_generation_performed is True
    assert result.read_only_activation_performed is False
    assert result.erp_write_performed is False
    assert result.credentials_exposed is False
    assert result.raw_secret_accessed is False


def test_generated_capability_set_does_not_contain_raw_secret(db):
    discovery = _create_safe_discovery_plan(db, secret="never-store-this")

    result = _generate(db, discovery.discovery_plan_id)
    loaded = GeneratedCapabilitySetService(db).get(result.capability_set_id)

    assert "never-store-this" not in json.dumps(loaded)
