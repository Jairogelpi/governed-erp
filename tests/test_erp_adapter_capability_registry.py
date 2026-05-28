from __future__ import annotations

from erpguard.product.erp_adapter_capability_registry import (
    ERPAdapterCapabilityCheckRequest,
    check_erp_adapter_capability,
    find_erp_adapter_capability,
    list_erp_adapter_capabilities,
    list_erp_adapter_identities,
)
from erpguard.product.erp_adapter_contract import ERPAdapterOperationType, ERPAdapterSafetyTier, ERPObjectType


def test_fake_erp_adapter_exists():
    assert any(item.adapter_id == "fake_erp" for item in list_erp_adapter_identities())


def test_odoo_placeholder_adapter_exists():
    assert any(item.adapter_id == "odoo_placeholder" for item in list_erp_adapter_identities())


def test_holded_placeholder_adapter_exists():
    assert any(item.adapter_id == "holded_placeholder" for item in list_erp_adapter_identities())


def test_sap_placeholder_adapter_exists():
    assert any(item.adapter_id == "sap_placeholder" for item in list_erp_adapter_identities())


def test_dynamics_placeholder_adapter_exists():
    assert any(item.adapter_id == "dynamics_placeholder" for item in list_erp_adapter_identities())


def test_netsuite_placeholder_adapter_exists():
    assert any(item.adapter_id == "netsuite_placeholder" for item in list_erp_adapter_identities())


def test_custom_rest_placeholder_adapter_exists():
    assert any(item.adapter_id == "custom_rest_placeholder" for item in list_erp_adapter_identities())


def test_placeholders_have_supports_real_connection_false():
    for item in list_erp_adapter_identities():
        assert item.supports_real_connection is False


def test_capability_lookup_works_by_adapter_id():
    capabilities = list_erp_adapter_capabilities("odoo_placeholder")
    assert capabilities


def test_capability_lookup_works_by_adapter_id_operation_and_object():
    capability = find_erp_adapter_capability(
        "odoo_placeholder",
        ERPAdapterOperationType.READ_OBJECT,
        ERPObjectType.PARTNER,
    )
    assert capability is not None


def test_supported_read_object_partner_on_odoo_placeholder_returns_read_only():
    result = check_erp_adapter_capability(
        ERPAdapterCapabilityCheckRequest(
            adapter_id="odoo_placeholder",
            operation_type=ERPAdapterOperationType.READ_OBJECT,
            object_type=ERPObjectType.PARTNER,
            requested_fields=["name", "email"],
        )
    )
    assert result.supported is True
    assert result.safety_tier == ERPAdapterSafetyTier.READ_ONLY


def test_unsupported_capability_returns_blocking_reason():
    result = check_erp_adapter_capability(
        ERPAdapterCapabilityCheckRequest(
            adapter_id="netsuite_placeholder",
            operation_type=ERPAdapterOperationType.INSPECT_SCHEMA,
            object_type=ERPObjectType.CUSTOM_OBJECT,
        )
    )
    assert result.supported is False
    assert "capability_not_supported" in result.blocking_reasons


def test_high_risk_write_operation_is_not_executable():
    result = check_erp_adapter_capability(
        ERPAdapterCapabilityCheckRequest(
            adapter_id="fake_erp",
            operation_type=ERPAdapterOperationType.UPDATE_OBJECT,
            object_type=ERPObjectType.CUSTOM_OBJECT,
        )
    )
    assert result.supports_execution is False
    assert result.can_execute is False


def test_capability_check_is_advisory_only():
    result = check_erp_adapter_capability(
        ERPAdapterCapabilityCheckRequest(
            adapter_id="fake_erp",
            operation_type=ERPAdapterOperationType.READ_OBJECT,
            object_type=ERPObjectType.PRODUCT,
        )
    )
    assert result.is_advisory_only is True


def test_capability_check_returns_will_execute_false_and_can_execute_false():
    result = check_erp_adapter_capability(
        ERPAdapterCapabilityCheckRequest(
            adapter_id="fake_erp",
            operation_type=ERPAdapterOperationType.SEARCH_OBJECTS,
            object_type=ERPObjectType.PRODUCT,
        )
    )
    assert result.will_execute is False
    assert result.can_execute is False


def test_no_real_credentials_required_in_block_c():
    result = check_erp_adapter_capability(
        ERPAdapterCapabilityCheckRequest(
            adapter_id="odoo_placeholder",
            operation_type=ERPAdapterOperationType.READ_OBJECT,
            object_type=ERPObjectType.PARTNER,
        )
    )
    assert result.requires_credentials is False


def test_safety_flags_default_false():
    result = check_erp_adapter_capability(
        ERPAdapterCapabilityCheckRequest(
            adapter_id="sap_placeholder",
            operation_type=ERPAdapterOperationType.READ_OBJECT,
            object_type=ERPObjectType.PRODUCT,
        )
    )
    assert result.safety_flags.real_erp_touched is False
    assert result.safety_flags.real_erp_write_performed is False


def test_no_external_http_occurs():
    result = check_erp_adapter_capability(
        ERPAdapterCapabilityCheckRequest(
            adapter_id="custom_rest_placeholder",
            operation_type=ERPAdapterOperationType.READ_OBJECT,
            object_type=ERPObjectType.CUSTOM_OBJECT,
        )
    )
    assert result.safety_flags.external_http_performed is False


def test_no_vendor_touch_flags_are_set():
    result = check_erp_adapter_capability(
        ERPAdapterCapabilityCheckRequest(
            adapter_id="odoo_placeholder",
            operation_type=ERPAdapterOperationType.READ_OBJECT,
            object_type=ERPObjectType.PARTNER,
        )
    )
    assert result.safety_flags.odoo_touched is False
    assert result.safety_flags.sap_touched is False
    assert result.safety_flags.dynamics_touched is False
    assert result.safety_flags.netsuite_touched is False


def test_requested_field_outside_allowlist_blocks_support():
    result = check_erp_adapter_capability(
        ERPAdapterCapabilityCheckRequest(
            adapter_id="odoo_placeholder",
            operation_type=ERPAdapterOperationType.READ_OBJECT,
            object_type=ERPObjectType.PARTNER,
            requested_fields=["name", "secret_field"],
        )
    )
    assert result.supported is False
    assert "requested_field_not_supported:secret_field" in result.blocking_reasons
