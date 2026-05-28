from __future__ import annotations

from erpguard.product.erp_adapter_contract import ERPAdapterOperationType, ERPObjectType
from erpguard.product.erp_adapter_safety_policy import ERPAdapterPolicyCheckRequest, check_erp_adapter_policy


def test_same_read_object_partner_contract_works_for_fake_erp():
    result = check_erp_adapter_policy(
        ERPAdapterPolicyCheckRequest(
            adapter_id="fake_erp",
            operation_type=ERPAdapterOperationType.READ_OBJECT,
            object_type=ERPObjectType.PARTNER,
        )
    )
    assert result.eligible is True


def test_same_read_object_partner_contract_works_for_odoo_placeholder():
    result = check_erp_adapter_policy(
        ERPAdapterPolicyCheckRequest(
            adapter_id="odoo_placeholder",
            operation_type=ERPAdapterOperationType.READ_OBJECT,
            object_type=ERPObjectType.PARTNER,
        )
    )
    assert result.eligible is True


def test_same_read_object_partner_contract_works_for_sap_placeholder():
    result = check_erp_adapter_policy(
        ERPAdapterPolicyCheckRequest(
            adapter_id="sap_placeholder",
            operation_type=ERPAdapterOperationType.READ_OBJECT,
            object_type=ERPObjectType.PARTNER,
        )
    )
    assert result.eligible is True


def test_same_read_object_partner_contract_works_for_dynamics_placeholder():
    result = check_erp_adapter_policy(
        ERPAdapterPolicyCheckRequest(
            adapter_id="dynamics_placeholder",
            operation_type=ERPAdapterOperationType.READ_OBJECT,
            object_type=ERPObjectType.PARTNER,
        )
    )
    assert result.eligible is True


def test_same_read_object_custom_object_contract_works_for_custom_rest_placeholder():
    result = check_erp_adapter_policy(
        ERPAdapterPolicyCheckRequest(
            adapter_id="custom_rest_placeholder",
            operation_type=ERPAdapterOperationType.READ_OBJECT,
            object_type=ERPObjectType.CUSTOM_OBJECT,
        )
    )
    assert result.eligible is True


def test_unsupported_object_type_blocks_consistently():
    for adapter_id in ("fake_erp", "odoo_placeholder", "sap_placeholder", "dynamics_placeholder"):
        result = check_erp_adapter_policy(
            ERPAdapterPolicyCheckRequest(
                adapter_id=adapter_id,
                operation_type=ERPAdapterOperationType.READ_OBJECT,
                object_type=ERPObjectType.MANUFACTURING_ORDER,
            )
        )
        assert result.eligible is False
        assert "capability_not_supported" in result.blocking_reasons


def test_write_high_risk_operations_block_consistently_for_real_placeholders():
    for adapter_id in ("odoo_placeholder", "sap_placeholder", "dynamics_placeholder", "netsuite_placeholder"):
        result = check_erp_adapter_policy(
            ERPAdapterPolicyCheckRequest(
                adapter_id=adapter_id,
                operation_type=ERPAdapterOperationType.CONFIRM_DOCUMENT,
                object_type=ERPObjectType.SALE_ORDER,
            )
        )
        assert result.eligible is False
        assert result.can_execute is False
