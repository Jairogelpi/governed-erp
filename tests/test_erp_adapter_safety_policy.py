from __future__ import annotations

from erpguard.product.erp_adapter_contract import ERPAdapterOperationType, ERPObjectType
from erpguard.product.erp_adapter_safety_policy import (
    ERPAdapterPolicyCheckRequest,
    check_erp_adapter_policy,
)


def test_read_only_capability_is_eligible_and_previewable_but_not_executable():
    result = check_erp_adapter_policy(
        ERPAdapterPolicyCheckRequest(
            adapter_id="odoo_placeholder",
            operation_type=ERPAdapterOperationType.READ_OBJECT,
            object_type=ERPObjectType.PARTNER,
        )
    )
    assert result.eligible is True
    assert result.can_preview is True
    assert result.can_execute is False


def test_preview_write_is_eligible_previewable_not_executable_and_requires_confirmation():
    result = check_erp_adapter_policy(
        ERPAdapterPolicyCheckRequest(
            adapter_id="odoo_placeholder",
            operation_type=ERPAdapterOperationType.PREVIEW_WRITE,
            object_type=ERPObjectType.SALE_ORDER,
            requested_fields=["state"],
        )
    )
    assert result.eligible is True
    assert result.can_preview is True
    assert result.can_execute is False
    assert result.requires_confirmation is True


def test_unsupported_capability_blocks():
    result = check_erp_adapter_policy(
        ERPAdapterPolicyCheckRequest(
            adapter_id="netsuite_placeholder",
            operation_type=ERPAdapterOperationType.INSPECT_SCHEMA,
            object_type=ERPObjectType.CUSTOM_OBJECT,
        )
    )
    assert result.eligible is False
    assert "capability_not_supported" in result.blocking_reasons


def test_requested_field_outside_allowlist_blocks():
    result = check_erp_adapter_policy(
        ERPAdapterPolicyCheckRequest(
            adapter_id="odoo_placeholder",
            operation_type=ERPAdapterOperationType.READ_OBJECT,
            object_type=ERPObjectType.PARTNER,
            requested_fields=["secret_field"],
        )
    )
    assert result.eligible is False
    assert "requested_field_not_supported:secret_field" in result.blocking_reasons


def test_controlled_write_blocks_in_block_c():
    result = check_erp_adapter_policy(
        ERPAdapterPolicyCheckRequest(
            adapter_id="odoo_placeholder",
            operation_type=ERPAdapterOperationType.CREATE_OBJECT,
            object_type=ERPObjectType.PARTNER,
        )
    )
    assert result.eligible is False
    assert "capability_not_supported" in result.blocking_reasons


def test_high_risk_write_blocks_in_block_c():
    result = check_erp_adapter_policy(
        ERPAdapterPolicyCheckRequest(
            adapter_id="odoo_placeholder",
            operation_type=ERPAdapterOperationType.CONFIRM_DOCUMENT,
            object_type=ERPObjectType.SALE_ORDER,
        )
    )
    assert result.eligible is False
    assert "capability_not_supported" in result.blocking_reasons


def test_forbidden_operation_blocks():
    result = check_erp_adapter_policy(
        ERPAdapterPolicyCheckRequest(
            adapter_id="odoo_placeholder",
            operation_type=ERPAdapterOperationType.UNKNOWN,
            object_type=ERPObjectType.PARTNER,
        )
    )
    assert result.eligible is False


def test_real_erp_placeholder_execution_always_can_execute_false():
    result = check_erp_adapter_policy(
        ERPAdapterPolicyCheckRequest(
            adapter_id="sap_placeholder",
            operation_type=ERPAdapterOperationType.READ_OBJECT,
            object_type=ERPObjectType.PARTNER,
        )
    )
    assert result.can_execute is False


def test_fake_erp_sandbox_write_can_be_represented_but_still_not_executable():
    result = check_erp_adapter_policy(
        ERPAdapterPolicyCheckRequest(
            adapter_id="fake_erp",
            operation_type=ERPAdapterOperationType.UPDATE_OBJECT,
            object_type=ERPObjectType.CUSTOM_OBJECT,
            requested_fields=["status"],
        )
    )
    assert result.eligible is True
    assert result.can_preview is True
    assert result.can_execute is False


def test_policy_check_is_advisory_only():
    result = check_erp_adapter_policy(
        ERPAdapterPolicyCheckRequest(
            adapter_id="fake_erp",
            operation_type=ERPAdapterOperationType.READ_OBJECT,
            object_type=ERPObjectType.PRODUCT,
        )
    )
    assert result.is_advisory_only is True


def test_will_execute_false_always():
    result = check_erp_adapter_policy(
        ERPAdapterPolicyCheckRequest(
            adapter_id="fake_erp",
            operation_type=ERPAdapterOperationType.READ_OBJECT,
            object_type=ERPObjectType.PRODUCT,
        )
    )
    assert result.will_execute is False


def test_safety_flags_remain_false():
    result = check_erp_adapter_policy(
        ERPAdapterPolicyCheckRequest(
            adapter_id="custom_rest_placeholder",
            operation_type=ERPAdapterOperationType.READ_OBJECT,
            object_type=ERPObjectType.CUSTOM_OBJECT,
        )
    )
    assert result.safety_flags.real_erp_touched is False
    assert result.safety_flags.external_http_performed is False
    assert result.safety_flags.credentials_used is False
