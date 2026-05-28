from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ERPAdapterOperationType(StrEnum):
    READ_OBJECT = "read_object"
    SEARCH_OBJECTS = "search_objects"
    INSPECT_SCHEMA = "inspect_schema"
    INSPECT_PERMISSIONS = "inspect_permissions"
    PREVIEW_WRITE = "preview_write"
    CREATE_OBJECT = "create_object"
    UPDATE_OBJECT = "update_object"
    DELETE_OBJECT = "delete_object"
    POST_DOCUMENT = "post_document"
    CONFIRM_DOCUMENT = "confirm_document"
    RECONCILE_PAYMENT = "reconcile_payment"
    PRODUCE_MANUFACTURING_ORDER = "produce_manufacturing_order"
    UNKNOWN = "unknown"


class ERPObjectType(StrEnum):
    PARTNER = "partner"
    PRODUCT = "product"
    SALE_ORDER = "sale_order"
    PURCHASE_ORDER = "purchase_order"
    INVOICE = "invoice"
    PAYMENT = "payment"
    STOCK_ITEM = "stock_item"
    STOCK_MOVE = "stock_move"
    MANUFACTURING_ORDER = "manufacturing_order"
    JOURNAL_ENTRY = "journal_entry"
    CUSTOM_OBJECT = "custom_object"


class ERPAdapterSafetyTier(StrEnum):
    READ_ONLY = "read_only"
    PREVIEW_ONLY = "preview_only"
    SANDBOX_WRITE = "sandbox_write"
    CONTROLLED_WRITE = "controlled_write"
    HIGH_RISK_WRITE = "high_risk_write"
    FORBIDDEN = "forbidden"


class ERPAdapterType(StrEnum):
    FAKE_ERP = "fake_erp"
    ODOO_PLACEHOLDER = "odoo_placeholder"
    HOLDED_PLACEHOLDER = "holded_placeholder"
    SAP_PLACEHOLDER = "sap_placeholder"
    DYNAMICS_PLACEHOLDER = "dynamics_placeholder"
    NETSUITE_PLACEHOLDER = "netsuite_placeholder"
    CUSTOM_REST_PLACEHOLDER = "custom_rest_placeholder"


class ERPAdapterContractModel(BaseModel):
    model_config = ConfigDict(use_enum_values=False)


class ERPAdapterIdentity(ERPAdapterContractModel):
    adapter_id: str
    adapter_type: ERPAdapterType
    display_name: str
    vendor_name: str
    is_placeholder: bool = True
    supports_real_connection: bool = False


class ERPObjectRef(ERPAdapterContractModel):
    object_type: ERPObjectType
    external_id: str | None = None
    display_name: str | None = None
    raw_ref: dict[str, Any] = Field(default_factory=dict)


class ERPFieldRef(ERPAdapterContractModel):
    field_name: str
    field_label: str | None = None
    field_type: str | None = None
    readable: bool = False
    writable: bool = False
    required: bool = False


class ERPAdapterOperationRequest(ERPAdapterContractModel):
    request_id: str
    adapter_id: str
    operation_type: ERPAdapterOperationType
    object_type: ERPObjectType
    object_ref: ERPObjectRef | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    field_refs: list[ERPFieldRef] = Field(default_factory=list)
    idempotency_key: str | None = None
    requested_by: str | None = None
    reason: str | None = None


class ERPAdapterSafetyFlags(ERPAdapterContractModel):
    real_erp_touched: bool = False
    real_erp_write_performed: bool = False
    external_http_performed: bool = False
    credentials_used: bool = False
    browser_control_performed: bool = False
    mcp_execution_performed: bool = False
    scheduler_used: bool = False
    endpoint_hint_executed: bool = False
    llm_runtime_used: bool = False
    odoo_touched: bool = False
    sap_touched: bool = False
    dynamics_touched: bool = False
    netsuite_touched: bool = False


class ERPAdapterEvidence(ERPAdapterContractModel):
    evidence_id: str | None = None
    request_id: str
    adapter_id: str
    operation_type: ERPAdapterOperationType
    object_type: ERPObjectType
    summary: str
    payload_snapshot: dict[str, Any] = Field(default_factory=dict)
    normalized_snapshot: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ERPAdapterError(ERPAdapterContractModel):
    code: str
    message: str
    blocking: bool = True
    field: str | None = None


class ERPAdapterOperationResult(ERPAdapterContractModel):
    request_id: str
    adapter_id: str
    adapter_type: ERPAdapterType
    operation_type: ERPAdapterOperationType
    object_type: ERPObjectType
    status: str
    result_payload: dict[str, Any] = Field(default_factory=dict)
    normalized_payload: dict[str, Any] = Field(default_factory=dict)
    evidence: ERPAdapterEvidence
    safety_flags: ERPAdapterSafetyFlags
    audit_ref: str | None = None
    blocking_reasons: list[str] = Field(default_factory=list)
    errors: list[ERPAdapterError] = Field(default_factory=list)


def default_safety_flags() -> ERPAdapterSafetyFlags:
    return ERPAdapterSafetyFlags()


def infer_default_safety_tier(operation_type: ERPAdapterOperationType | str) -> ERPAdapterSafetyTier:
    mapping = {
        ERPAdapterOperationType.READ_OBJECT: ERPAdapterSafetyTier.READ_ONLY,
        ERPAdapterOperationType.SEARCH_OBJECTS: ERPAdapterSafetyTier.READ_ONLY,
        ERPAdapterOperationType.INSPECT_SCHEMA: ERPAdapterSafetyTier.READ_ONLY,
        ERPAdapterOperationType.INSPECT_PERMISSIONS: ERPAdapterSafetyTier.READ_ONLY,
        ERPAdapterOperationType.PREVIEW_WRITE: ERPAdapterSafetyTier.PREVIEW_ONLY,
        ERPAdapterOperationType.CREATE_OBJECT: ERPAdapterSafetyTier.CONTROLLED_WRITE,
        ERPAdapterOperationType.UPDATE_OBJECT: ERPAdapterSafetyTier.CONTROLLED_WRITE,
        ERPAdapterOperationType.DELETE_OBJECT: ERPAdapterSafetyTier.HIGH_RISK_WRITE,
        ERPAdapterOperationType.POST_DOCUMENT: ERPAdapterSafetyTier.HIGH_RISK_WRITE,
        ERPAdapterOperationType.CONFIRM_DOCUMENT: ERPAdapterSafetyTier.HIGH_RISK_WRITE,
        ERPAdapterOperationType.RECONCILE_PAYMENT: ERPAdapterSafetyTier.HIGH_RISK_WRITE,
        ERPAdapterOperationType.PRODUCE_MANUFACTURING_ORDER: ERPAdapterSafetyTier.HIGH_RISK_WRITE,
    }
    try:
        normalized = (
            operation_type
            if isinstance(operation_type, ERPAdapterOperationType)
            else ERPAdapterOperationType(str(operation_type))
        )
    except ValueError:
        return ERPAdapterSafetyTier.FORBIDDEN
    return mapping.get(normalized, ERPAdapterSafetyTier.FORBIDDEN)


def operation_is_write_like(operation_type: ERPAdapterOperationType | str) -> bool:
    return infer_default_safety_tier(operation_type) in {
        ERPAdapterSafetyTier.PREVIEW_ONLY,
        ERPAdapterSafetyTier.SANDBOX_WRITE,
        ERPAdapterSafetyTier.CONTROLLED_WRITE,
        ERPAdapterSafetyTier.HIGH_RISK_WRITE,
    }


def operation_is_read_like(operation_type: ERPAdapterOperationType | str) -> bool:
    return infer_default_safety_tier(operation_type) == ERPAdapterSafetyTier.READ_ONLY


def make_blocked_adapter_result(
    *,
    request: ERPAdapterOperationRequest,
    adapter_identity: ERPAdapterIdentity,
    summary: str,
    blocking_reasons: list[str] | None = None,
    errors: list[ERPAdapterError] | None = None,
    audit_ref: str | None = None,
) -> ERPAdapterOperationResult:
    return ERPAdapterOperationResult(
        request_id=request.request_id,
        adapter_id=adapter_identity.adapter_id,
        adapter_type=adapter_identity.adapter_type,
        operation_type=request.operation_type,
        object_type=request.object_type,
        status="blocked",
        result_payload={},
        normalized_payload={},
        evidence=ERPAdapterEvidence(
            request_id=request.request_id,
            adapter_id=adapter_identity.adapter_id,
            operation_type=request.operation_type,
            object_type=request.object_type,
            summary=summary,
            payload_snapshot=request.payload,
            normalized_snapshot={},
        ),
        safety_flags=default_safety_flags(),
        audit_ref=audit_ref,
        blocking_reasons=list(blocking_reasons or []),
        errors=list(errors or []),
    )


def make_contract_only_success_result(
    *,
    request: ERPAdapterOperationRequest,
    adapter_identity: ERPAdapterIdentity,
    summary: str,
    result_payload: dict[str, Any] | None = None,
    normalized_payload: dict[str, Any] | None = None,
    audit_ref: str | None = None,
) -> ERPAdapterOperationResult:
    return ERPAdapterOperationResult(
        request_id=request.request_id,
        adapter_id=adapter_identity.adapter_id,
        adapter_type=adapter_identity.adapter_type,
        operation_type=request.operation_type,
        object_type=request.object_type,
        status="contract_only",
        result_payload=dict(result_payload or {}),
        normalized_payload=dict(normalized_payload or {}),
        evidence=ERPAdapterEvidence(
            request_id=request.request_id,
            adapter_id=adapter_identity.adapter_id,
            operation_type=request.operation_type,
            object_type=request.object_type,
            summary=summary,
            payload_snapshot=request.payload,
            normalized_snapshot=dict(normalized_payload or {}),
        ),
        safety_flags=default_safety_flags(),
        audit_ref=audit_ref,
        blocking_reasons=[],
        errors=[],
    )
