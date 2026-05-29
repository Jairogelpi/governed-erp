"""Tests for Sprint 58 - generated capability audit."""

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
from erpguard.product.generated_capability_audit import GeneratedCapabilityAuditService
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


def _safe_plan(db, *, password="audit-generated-secret"):
    create_connector_setup_session(
        db,
        session_id="csess_gca",
        connector_name="odoo_generated_audit",
        erp_url="https://audit-generated.odoo.com",
        erp_url_host="audit-generated.odoo.com",
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
            setup_session_id="csess_gca",
            auth_type=AuthType.PASSWORD,
            username="admin@example.com",
            password=password,
            submitted_by="operator_1",
        )
    )
    update_connector_setup_session(
        db,
        "csess_gca",
        credential_ref=credential.credential_ref,
        credential_mode="vault_reference_only",
        status="ready_for_fingerprint",
    )
    fingerprint = ERPFingerprintingPlanService(db).create_plan(
        FingerprintingPlanInput(
            setup_session_id="csess_gca",
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


def test_audit_records_generated_capabilities_created(db):
    discovery = _safe_plan(db)

    result = GeneratedCapabilitySetService(db).generate(
        GeneratedCapabilityInput(
            discovery_plan_id=discovery.discovery_plan_id,
            created_by="operator_1",
        )
    )

    audit = GeneratedCapabilityAuditService(db).get_audit()
    created = [
        event
        for event in audit.events
        if event["event_type"] == "generated_capabilities_created"
    ]
    assert created
    assert created[0]["capability_set_id"] == result.capability_set_id


def test_audit_records_blocked_generation(db):
    GeneratedCapabilitySetService(db).generate(
        GeneratedCapabilityInput(
            discovery_plan_id="dplan_missing",
            created_by="operator_1",
        )
    )

    audit = GeneratedCapabilityAuditService(db).get_audit()

    assert any(
        event["event_type"] == "generated_capabilities_blocked"
        and event["status"] == "blocked"
        for event in audit.events
    )


def test_audit_does_not_contain_raw_secret(db):
    discovery = _safe_plan(db, password="never-audit-this")

    GeneratedCapabilitySetService(db).generate(
        GeneratedCapabilityInput(
            discovery_plan_id=discovery.discovery_plan_id,
            created_by="operator_1",
        )
    )

    audit = GeneratedCapabilityAuditService(db).get_audit()
    assert "never-audit-this" not in str(audit.events)
