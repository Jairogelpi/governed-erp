from __future__ import annotations

from erpguard.product.erp_adapter_contract import (
    ERPAdapterError,
    ERPAdapterIdentity,
    ERPAdapterOperationRequest,
    ERPAdapterOperationResult,
    ERPAdapterOperationType,
    ERPAdapterSafetyFlags,
    ERPAdapterSafetyTier,
    ERPAdapterType,
    ERPFieldRef,
    ERPObjectRef,
    ERPObjectType,
    default_safety_flags,
    infer_default_safety_tier,
    make_blocked_adapter_result,
    make_contract_only_success_result,
    operation_is_read_like,
    operation_is_write_like,
)


def _identity() -> ERPAdapterIdentity:
    return ERPAdapterIdentity(
        adapter_id="adapter_fake_contract",
        adapter_type=ERPAdapterType.FAKE_ERP,
        display_name="Fake ERP Contract Adapter",
        vendor_name="ERPGuard",
        is_placeholder=True,
    )


def _request(operation_type: ERPAdapterOperationType, object_type: ERPObjectType) -> ERPAdapterOperationRequest:
    return ERPAdapterOperationRequest(
        request_id=f"req_{operation_type.value}",
        adapter_id="adapter_fake_contract",
        operation_type=operation_type,
        object_type=object_type,
        object_ref=ERPObjectRef(object_type=object_type, external_id="ext_1", display_name="Demo object"),
        payload={"query": "demo", "id": "ext_1"},
        field_refs=[
            ERPFieldRef(
                field_name="reference",
                field_label="Reference",
                field_type="string",
                readable=True,
                writable=False,
                required=False,
            )
        ],
        idempotency_key="idem_1",
        requested_by="operator_1",
        reason="Contract verification",
    )


def test_represents_read_object_request_result():
    req = _request(ERPAdapterOperationType.READ_OBJECT, ERPObjectType.SALE_ORDER)
    result = make_contract_only_success_result(
        request=req,
        adapter_identity=_identity(),
        summary="Read-object contract represented.",
        result_payload={"external_id": "ext_1"},
        normalized_payload={"reference": "SO-VALID"},
    )
    assert req.operation_type == ERPAdapterOperationType.READ_OBJECT
    assert result.status == "contract_only"
    assert result.object_type == ERPObjectType.SALE_ORDER


def test_represents_search_objects_request_result():
    req = _request(ERPAdapterOperationType.SEARCH_OBJECTS, ERPObjectType.PARTNER)
    result = make_contract_only_success_result(
        request=req,
        adapter_identity=_identity(),
        summary="Search-objects contract represented.",
        result_payload={"count": 1},
        normalized_payload={"items": [{"display_name": "Acme"}]},
    )
    assert result.operation_type == ERPAdapterOperationType.SEARCH_OBJECTS
    assert result.normalized_payload["items"][0]["display_name"] == "Acme"


def test_represents_inspect_schema_request_result():
    req = _request(ERPAdapterOperationType.INSPECT_SCHEMA, ERPObjectType.CUSTOM_OBJECT)
    result = make_contract_only_success_result(
        request=req,
        adapter_identity=_identity(),
        summary="Inspect-schema contract represented.",
        normalized_payload={"fields": ["reference", "status"]},
    )
    assert result.operation_type == ERPAdapterOperationType.INSPECT_SCHEMA


def test_represents_inspect_permissions_request_result():
    req = _request(ERPAdapterOperationType.INSPECT_PERMISSIONS, ERPObjectType.INVOICE)
    result = make_contract_only_success_result(
        request=req,
        adapter_identity=_identity(),
        summary="Inspect-permissions contract represented.",
        normalized_payload={"readable": True, "writable": False},
    )
    assert result.operation_type == ERPAdapterOperationType.INSPECT_PERMISSIONS


def test_represents_preview_write_request_result():
    req = _request(ERPAdapterOperationType.PREVIEW_WRITE, ERPObjectType.PAYMENT)
    result = make_contract_only_success_result(
        request=req,
        adapter_identity=_identity(),
        summary="Preview-write contract represented.",
        normalized_payload={"would_change": ["status"]},
    )
    assert result.operation_type == ERPAdapterOperationType.PREVIEW_WRITE
    assert infer_default_safety_tier(req.operation_type) == ERPAdapterSafetyTier.PREVIEW_ONLY


def test_forbidden_operation_can_produce_blocked_result():
    req = _request(ERPAdapterOperationType.UNKNOWN, ERPObjectType.CUSTOM_OBJECT)
    result = make_blocked_adapter_result(
        request=req,
        adapter_identity=_identity(),
        summary="Unknown operation blocked at contract layer.",
        blocking_reasons=["operation_forbidden"],
        errors=[ERPAdapterError(code="operation_forbidden", message="Unknown operation.", blocking=True)],
    )
    assert result.status == "blocked"
    assert "operation_forbidden" in result.blocking_reasons
    assert result.errors[0].code == "operation_forbidden"


def test_safety_flags_default_to_false():
    flags = default_safety_flags()
    assert flags.real_erp_touched is False
    assert flags.real_erp_write_performed is False
    assert flags.external_http_performed is False
    assert flags.credentials_used is False
    assert flags.browser_control_performed is False
    assert flags.mcp_execution_performed is False
    assert flags.scheduler_used is False
    assert flags.endpoint_hint_executed is False
    assert flags.llm_runtime_used is False
    assert flags.odoo_touched is False
    assert flags.sap_touched is False
    assert flags.dynamics_touched is False
    assert flags.netsuite_touched is False


def test_write_like_operation_is_detected():
    assert operation_is_write_like(ERPAdapterOperationType.UPDATE_OBJECT) is True
    assert operation_is_write_like(ERPAdapterOperationType.DELETE_OBJECT) is True


def test_read_like_operation_is_detected():
    assert operation_is_read_like(ERPAdapterOperationType.READ_OBJECT) is True
    assert operation_is_read_like(ERPAdapterOperationType.SEARCH_OBJECTS) is True


def test_default_safety_tier_mapping_works():
    assert infer_default_safety_tier(ERPAdapterOperationType.READ_OBJECT) == ERPAdapterSafetyTier.READ_ONLY
    assert infer_default_safety_tier(ERPAdapterOperationType.CREATE_OBJECT) == ERPAdapterSafetyTier.CONTROLLED_WRITE
    assert infer_default_safety_tier(ERPAdapterOperationType.POST_DOCUMENT) == ERPAdapterSafetyTier.HIGH_RISK_WRITE
    assert infer_default_safety_tier(ERPAdapterOperationType.UNKNOWN) == ERPAdapterSafetyTier.FORBIDDEN


def test_object_types_are_erp_neutral_and_do_not_require_odoo_model_names():
    req = _request(ERPAdapterOperationType.READ_OBJECT, ERPObjectType.SALE_ORDER)
    data = req.model_dump(mode="json")
    assert data["object_type"] == "sale_order"
    assert "sale.order" not in str(data)


def test_adapter_placeholders_do_not_imply_real_connection():
    identity = ERPAdapterIdentity(
        adapter_id="adapter_odoo_placeholder",
        adapter_type=ERPAdapterType.ODOO_PLACEHOLDER,
        display_name="Odoo Placeholder",
        vendor_name="Odoo",
        is_placeholder=True,
    )
    assert identity.is_placeholder is True
    assert identity.supports_real_connection is False


def test_request_serializes_deserializes_cleanly():
    req = _request(ERPAdapterOperationType.SEARCH_OBJECTS, ERPObjectType.PRODUCT)
    round_trip = ERPAdapterOperationRequest.model_validate(req.model_dump(mode="json"))
    assert round_trip == req


def test_result_serializes_deserializes_cleanly():
    req = _request(ERPAdapterOperationType.READ_OBJECT, ERPObjectType.INVOICE)
    result = make_contract_only_success_result(
        request=req,
        adapter_identity=_identity(),
        summary="Read contract round-trip.",
        normalized_payload={"invoice_number": "INV-1"},
    )
    round_trip = ERPAdapterOperationResult.model_validate(result.model_dump(mode="json"))
    assert round_trip == result


def test_safety_flags_serialize_deserializes_cleanly():
    flags = default_safety_flags()
    round_trip = ERPAdapterSafetyFlags.model_validate(flags.model_dump(mode="json"))
    assert round_trip == flags


def test_no_external_execution_flags_are_set():
    req = _request(ERPAdapterOperationType.PREVIEW_WRITE, ERPObjectType.PURCHASE_ORDER)
    result = make_contract_only_success_result(
        request=req,
        adapter_identity=_identity(),
        summary="Preview contract only.",
    )
    assert result.safety_flags.external_http_performed is False
    assert result.safety_flags.credentials_used is False
    assert result.safety_flags.browser_control_performed is False
    assert result.safety_flags.mcp_execution_performed is False
    assert result.safety_flags.scheduler_used is False
    assert result.safety_flags.real_erp_write_performed is False
