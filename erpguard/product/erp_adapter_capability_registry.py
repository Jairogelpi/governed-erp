from __future__ import annotations

from typing import Any

from pydantic import Field

from erpguard.product.erp_adapter_contract import (
    ERPAdapterContractModel,
    ERPAdapterIdentity,
    ERPAdapterOperationType,
    ERPAdapterSafetyFlags,
    ERPAdapterSafetyTier,
    ERPAdapterType,
    ERPObjectType,
    default_safety_flags,
)


class ERPAdapterCapability(ERPAdapterContractModel):
    adapter_id: str
    adapter_type: ERPAdapterType
    adapter_display_name: str
    operation_type: ERPAdapterOperationType
    object_type: ERPObjectType
    supported: bool
    safety_tier: ERPAdapterSafetyTier
    requires_credentials: bool = False
    requires_confirmed_token: bool = False
    supports_preview: bool = False
    supports_execution: bool = False
    supports_schema_inspection: bool = False
    supports_permission_inspection: bool = False
    field_read_allowlist: list[str] = Field(default_factory=list)
    field_write_allowlist: list[str] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)


class ERPAdapterCapabilityCheckRequest(ERPAdapterContractModel):
    adapter_id: str
    operation_type: ERPAdapterOperationType
    object_type: ERPObjectType
    requested_fields: list[str] = Field(default_factory=list)


class ERPAdapterCapabilityCheckResult(ERPAdapterContractModel):
    adapter_id: str
    adapter_type: ERPAdapterType
    adapter_display_name: str
    operation_type: ERPAdapterOperationType
    object_type: ERPObjectType
    supported: bool
    safety_tier: ERPAdapterSafetyTier
    requires_credentials: bool
    requires_confirmed_token: bool
    supports_preview: bool
    supports_execution: bool
    supports_schema_inspection: bool
    supports_permission_inspection: bool
    field_read_allowlist: list[str] = Field(default_factory=list)
    field_write_allowlist: list[str] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)
    is_advisory_only: bool = True
    will_execute: bool = False
    can_execute: bool = False
    safety_flags: ERPAdapterSafetyFlags = Field(default_factory=default_safety_flags)


class ERPAdapterRegistrySnapshot(ERPAdapterContractModel):
    adapters: list[ERPAdapterIdentity] = Field(default_factory=list)
    capabilities: list[ERPAdapterCapability] = Field(default_factory=list)


def _identity(
    adapter_id: str,
    adapter_type: ERPAdapterType,
    display_name: str,
    vendor_name: str,
) -> ERPAdapterIdentity:
    return ERPAdapterIdentity(
        adapter_id=adapter_id,
        adapter_type=adapter_type,
        display_name=display_name,
        vendor_name=vendor_name,
        is_placeholder=True,
        supports_real_connection=False,
    )


_ADAPTER_IDENTITIES: list[ERPAdapterIdentity] = [
    _identity("fake_erp", ERPAdapterType.FAKE_ERP, "Fake ERP Adapter", "ERPGuard"),
    _identity("odoo_placeholder", ERPAdapterType.ODOO_PLACEHOLDER, "Odoo Placeholder Adapter", "Odoo"),
    _identity("holded_placeholder", ERPAdapterType.HOLDED_PLACEHOLDER, "Holded Placeholder Adapter", "Holded"),
    _identity("sap_placeholder", ERPAdapterType.SAP_PLACEHOLDER, "SAP Placeholder Adapter", "SAP"),
    _identity("dynamics_placeholder", ERPAdapterType.DYNAMICS_PLACEHOLDER, "Dynamics Placeholder Adapter", "Microsoft Dynamics"),
    _identity("netsuite_placeholder", ERPAdapterType.NETSUITE_PLACEHOLDER, "NetSuite Placeholder Adapter", "NetSuite"),
    _identity(
        "custom_rest_placeholder",
        ERPAdapterType.CUSTOM_REST_PLACEHOLDER,
        "Custom REST Placeholder Adapter",
        "Custom REST",
    ),
]


def _cap(
    adapter_id: str,
    adapter_type: ERPAdapterType,
    adapter_display_name: str,
    operation_type: ERPAdapterOperationType,
    object_type: ERPObjectType,
    *,
    safety_tier: ERPAdapterSafetyTier,
    field_read_allowlist: list[str] | None = None,
    field_write_allowlist: list[str] | None = None,
    supports_preview: bool = False,
    supports_execution: bool = False,
    supports_schema_inspection: bool = False,
    supports_permission_inspection: bool = False,
    supported: bool = True,
    blocking_reasons: list[str] | None = None,
) -> ERPAdapterCapability:
    return ERPAdapterCapability(
        adapter_id=adapter_id,
        adapter_type=adapter_type,
        adapter_display_name=adapter_display_name,
        operation_type=operation_type,
        object_type=object_type,
        supported=supported,
        safety_tier=safety_tier,
        requires_credentials=False,
        requires_confirmed_token=False,
        supports_preview=supports_preview,
        supports_execution=supports_execution,
        supports_schema_inspection=supports_schema_inspection,
        supports_permission_inspection=supports_permission_inspection,
        field_read_allowlist=list(field_read_allowlist or []),
        field_write_allowlist=list(field_write_allowlist or []),
        blocking_reasons=list(blocking_reasons or []),
    )


_COMMON_READ_FIELDS = ["name", "email", "phone"]
_PRODUCT_READ_FIELDS = ["name", "default_code", "type"]
_SALE_ORDER_READ_FIELDS = ["reference", "state", "total_amount"]
_INVOICE_READ_FIELDS = ["number", "state", "amount_total"]
_CUSTOM_READ_FIELDS = ["id", "name", "status"]

_CAPABILITIES: list[ERPAdapterCapability] = [
    _cap("fake_erp", ERPAdapterType.FAKE_ERP, "Fake ERP Adapter", ERPAdapterOperationType.READ_OBJECT, ERPObjectType.PARTNER, safety_tier=ERPAdapterSafetyTier.READ_ONLY, field_read_allowlist=_COMMON_READ_FIELDS),
    _cap("fake_erp", ERPAdapterType.FAKE_ERP, "Fake ERP Adapter", ERPAdapterOperationType.READ_OBJECT, ERPObjectType.PRODUCT, safety_tier=ERPAdapterSafetyTier.READ_ONLY, field_read_allowlist=_PRODUCT_READ_FIELDS),
    _cap("fake_erp", ERPAdapterType.FAKE_ERP, "Fake ERP Adapter", ERPAdapterOperationType.READ_OBJECT, ERPObjectType.SALE_ORDER, safety_tier=ERPAdapterSafetyTier.READ_ONLY, field_read_allowlist=_SALE_ORDER_READ_FIELDS),
    _cap("fake_erp", ERPAdapterType.FAKE_ERP, "Fake ERP Adapter", ERPAdapterOperationType.SEARCH_OBJECTS, ERPObjectType.PARTNER, safety_tier=ERPAdapterSafetyTier.READ_ONLY, field_read_allowlist=_COMMON_READ_FIELDS),
    _cap("fake_erp", ERPAdapterType.FAKE_ERP, "Fake ERP Adapter", ERPAdapterOperationType.SEARCH_OBJECTS, ERPObjectType.PRODUCT, safety_tier=ERPAdapterSafetyTier.READ_ONLY, field_read_allowlist=_PRODUCT_READ_FIELDS),
    _cap("fake_erp", ERPAdapterType.FAKE_ERP, "Fake ERP Adapter", ERPAdapterOperationType.SEARCH_OBJECTS, ERPObjectType.SALE_ORDER, safety_tier=ERPAdapterSafetyTier.READ_ONLY, field_read_allowlist=_SALE_ORDER_READ_FIELDS),
    _cap("fake_erp", ERPAdapterType.FAKE_ERP, "Fake ERP Adapter", ERPAdapterOperationType.INSPECT_SCHEMA, ERPObjectType.CUSTOM_OBJECT, safety_tier=ERPAdapterSafetyTier.READ_ONLY, supports_schema_inspection=True, field_read_allowlist=_CUSTOM_READ_FIELDS),
    _cap("fake_erp", ERPAdapterType.FAKE_ERP, "Fake ERP Adapter", ERPAdapterOperationType.INSPECT_PERMISSIONS, ERPObjectType.CUSTOM_OBJECT, safety_tier=ERPAdapterSafetyTier.READ_ONLY, supports_permission_inspection=True, field_read_allowlist=_CUSTOM_READ_FIELDS),
    _cap("fake_erp", ERPAdapterType.FAKE_ERP, "Fake ERP Adapter", ERPAdapterOperationType.PREVIEW_WRITE, ERPObjectType.SALE_ORDER, safety_tier=ERPAdapterSafetyTier.PREVIEW_ONLY, supports_preview=True, field_read_allowlist=_SALE_ORDER_READ_FIELDS, field_write_allowlist=["state"]),
    _cap("fake_erp", ERPAdapterType.FAKE_ERP, "Fake ERP Adapter", ERPAdapterOperationType.UPDATE_OBJECT, ERPObjectType.CUSTOM_OBJECT, safety_tier=ERPAdapterSafetyTier.SANDBOX_WRITE, supports_execution=False, field_read_allowlist=_CUSTOM_READ_FIELDS, field_write_allowlist=["status"]),
    _cap("odoo_placeholder", ERPAdapterType.ODOO_PLACEHOLDER, "Odoo Placeholder Adapter", ERPAdapterOperationType.READ_OBJECT, ERPObjectType.PARTNER, safety_tier=ERPAdapterSafetyTier.READ_ONLY, field_read_allowlist=_COMMON_READ_FIELDS),
    _cap("odoo_placeholder", ERPAdapterType.ODOO_PLACEHOLDER, "Odoo Placeholder Adapter", ERPAdapterOperationType.READ_OBJECT, ERPObjectType.PRODUCT, safety_tier=ERPAdapterSafetyTier.READ_ONLY, field_read_allowlist=_PRODUCT_READ_FIELDS),
    _cap("odoo_placeholder", ERPAdapterType.ODOO_PLACEHOLDER, "Odoo Placeholder Adapter", ERPAdapterOperationType.READ_OBJECT, ERPObjectType.SALE_ORDER, safety_tier=ERPAdapterSafetyTier.READ_ONLY, field_read_allowlist=_SALE_ORDER_READ_FIELDS),
    _cap("odoo_placeholder", ERPAdapterType.ODOO_PLACEHOLDER, "Odoo Placeholder Adapter", ERPAdapterOperationType.SEARCH_OBJECTS, ERPObjectType.PARTNER, safety_tier=ERPAdapterSafetyTier.READ_ONLY, field_read_allowlist=_COMMON_READ_FIELDS),
    _cap("odoo_placeholder", ERPAdapterType.ODOO_PLACEHOLDER, "Odoo Placeholder Adapter", ERPAdapterOperationType.SEARCH_OBJECTS, ERPObjectType.PRODUCT, safety_tier=ERPAdapterSafetyTier.READ_ONLY, field_read_allowlist=_PRODUCT_READ_FIELDS),
    _cap("odoo_placeholder", ERPAdapterType.ODOO_PLACEHOLDER, "Odoo Placeholder Adapter", ERPAdapterOperationType.SEARCH_OBJECTS, ERPObjectType.SALE_ORDER, safety_tier=ERPAdapterSafetyTier.READ_ONLY, field_read_allowlist=_SALE_ORDER_READ_FIELDS),
    _cap("odoo_placeholder", ERPAdapterType.ODOO_PLACEHOLDER, "Odoo Placeholder Adapter", ERPAdapterOperationType.INSPECT_SCHEMA, ERPObjectType.CUSTOM_OBJECT, safety_tier=ERPAdapterSafetyTier.READ_ONLY, supports_schema_inspection=True, field_read_allowlist=_CUSTOM_READ_FIELDS),
    _cap("odoo_placeholder", ERPAdapterType.ODOO_PLACEHOLDER, "Odoo Placeholder Adapter", ERPAdapterOperationType.INSPECT_PERMISSIONS, ERPObjectType.CUSTOM_OBJECT, safety_tier=ERPAdapterSafetyTier.READ_ONLY, supports_permission_inspection=True, field_read_allowlist=_CUSTOM_READ_FIELDS),
    _cap("odoo_placeholder", ERPAdapterType.ODOO_PLACEHOLDER, "Odoo Placeholder Adapter", ERPAdapterOperationType.PREVIEW_WRITE, ERPObjectType.SALE_ORDER, safety_tier=ERPAdapterSafetyTier.PREVIEW_ONLY, supports_preview=True, field_read_allowlist=_SALE_ORDER_READ_FIELDS, field_write_allowlist=["state"]),
    _cap("odoo_placeholder", ERPAdapterType.ODOO_PLACEHOLDER, "Odoo Placeholder Adapter", ERPAdapterOperationType.PREVIEW_WRITE, ERPObjectType.INVOICE, safety_tier=ERPAdapterSafetyTier.PREVIEW_ONLY, supports_preview=True, field_read_allowlist=_INVOICE_READ_FIELDS, field_write_allowlist=["state"]),
    _cap("holded_placeholder", ERPAdapterType.HOLDED_PLACEHOLDER, "Holded Placeholder Adapter", ERPAdapterOperationType.READ_OBJECT, ERPObjectType.PARTNER, safety_tier=ERPAdapterSafetyTier.READ_ONLY, field_read_allowlist=_COMMON_READ_FIELDS),
    _cap("holded_placeholder", ERPAdapterType.HOLDED_PLACEHOLDER, "Holded Placeholder Adapter", ERPAdapterOperationType.READ_OBJECT, ERPObjectType.PRODUCT, safety_tier=ERPAdapterSafetyTier.READ_ONLY, field_read_allowlist=_PRODUCT_READ_FIELDS),
    _cap("holded_placeholder", ERPAdapterType.HOLDED_PLACEHOLDER, "Holded Placeholder Adapter", ERPAdapterOperationType.READ_OBJECT, ERPObjectType.INVOICE, safety_tier=ERPAdapterSafetyTier.READ_ONLY, field_read_allowlist=_INVOICE_READ_FIELDS),
    _cap("holded_placeholder", ERPAdapterType.HOLDED_PLACEHOLDER, "Holded Placeholder Adapter", ERPAdapterOperationType.SEARCH_OBJECTS, ERPObjectType.PARTNER, safety_tier=ERPAdapterSafetyTier.READ_ONLY, field_read_allowlist=_COMMON_READ_FIELDS),
    _cap("holded_placeholder", ERPAdapterType.HOLDED_PLACEHOLDER, "Holded Placeholder Adapter", ERPAdapterOperationType.SEARCH_OBJECTS, ERPObjectType.INVOICE, safety_tier=ERPAdapterSafetyTier.READ_ONLY, field_read_allowlist=_INVOICE_READ_FIELDS),
    _cap("holded_placeholder", ERPAdapterType.HOLDED_PLACEHOLDER, "Holded Placeholder Adapter", ERPAdapterOperationType.PREVIEW_WRITE, ERPObjectType.INVOICE, safety_tier=ERPAdapterSafetyTier.PREVIEW_ONLY, supports_preview=True, field_read_allowlist=_INVOICE_READ_FIELDS, field_write_allowlist=["state"]),
    _cap("sap_placeholder", ERPAdapterType.SAP_PLACEHOLDER, "SAP Placeholder Adapter", ERPAdapterOperationType.READ_OBJECT, ERPObjectType.PARTNER, safety_tier=ERPAdapterSafetyTier.READ_ONLY, field_read_allowlist=_COMMON_READ_FIELDS),
    _cap("sap_placeholder", ERPAdapterType.SAP_PLACEHOLDER, "SAP Placeholder Adapter", ERPAdapterOperationType.READ_OBJECT, ERPObjectType.PRODUCT, safety_tier=ERPAdapterSafetyTier.READ_ONLY, field_read_allowlist=_PRODUCT_READ_FIELDS),
    _cap("sap_placeholder", ERPAdapterType.SAP_PLACEHOLDER, "SAP Placeholder Adapter", ERPAdapterOperationType.READ_OBJECT, ERPObjectType.STOCK_ITEM, safety_tier=ERPAdapterSafetyTier.READ_ONLY, field_read_allowlist=["name", "sku", "quantity"]),
    _cap("sap_placeholder", ERPAdapterType.SAP_PLACEHOLDER, "SAP Placeholder Adapter", ERPAdapterOperationType.SEARCH_OBJECTS, ERPObjectType.PARTNER, safety_tier=ERPAdapterSafetyTier.READ_ONLY, field_read_allowlist=_COMMON_READ_FIELDS),
    _cap("sap_placeholder", ERPAdapterType.SAP_PLACEHOLDER, "SAP Placeholder Adapter", ERPAdapterOperationType.SEARCH_OBJECTS, ERPObjectType.PRODUCT, safety_tier=ERPAdapterSafetyTier.READ_ONLY, field_read_allowlist=_PRODUCT_READ_FIELDS),
    _cap("sap_placeholder", ERPAdapterType.SAP_PLACEHOLDER, "SAP Placeholder Adapter", ERPAdapterOperationType.INSPECT_SCHEMA, ERPObjectType.CUSTOM_OBJECT, safety_tier=ERPAdapterSafetyTier.READ_ONLY, supports_schema_inspection=True, field_read_allowlist=_CUSTOM_READ_FIELDS),
    _cap("sap_placeholder", ERPAdapterType.SAP_PLACEHOLDER, "SAP Placeholder Adapter", ERPAdapterOperationType.INSPECT_PERMISSIONS, ERPObjectType.CUSTOM_OBJECT, safety_tier=ERPAdapterSafetyTier.READ_ONLY, supports_permission_inspection=True, field_read_allowlist=_CUSTOM_READ_FIELDS),
    _cap("sap_placeholder", ERPAdapterType.SAP_PLACEHOLDER, "SAP Placeholder Adapter", ERPAdapterOperationType.PREVIEW_WRITE, ERPObjectType.PURCHASE_ORDER, safety_tier=ERPAdapterSafetyTier.PREVIEW_ONLY, supports_preview=True, field_read_allowlist=["reference", "status"], field_write_allowlist=["status"]),
    _cap("dynamics_placeholder", ERPAdapterType.DYNAMICS_PLACEHOLDER, "Dynamics Placeholder Adapter", ERPAdapterOperationType.READ_OBJECT, ERPObjectType.PARTNER, safety_tier=ERPAdapterSafetyTier.READ_ONLY, field_read_allowlist=_COMMON_READ_FIELDS),
    _cap("dynamics_placeholder", ERPAdapterType.DYNAMICS_PLACEHOLDER, "Dynamics Placeholder Adapter", ERPAdapterOperationType.READ_OBJECT, ERPObjectType.SALE_ORDER, safety_tier=ERPAdapterSafetyTier.READ_ONLY, field_read_allowlist=_SALE_ORDER_READ_FIELDS),
    _cap("dynamics_placeholder", ERPAdapterType.DYNAMICS_PLACEHOLDER, "Dynamics Placeholder Adapter", ERPAdapterOperationType.SEARCH_OBJECTS, ERPObjectType.PARTNER, safety_tier=ERPAdapterSafetyTier.READ_ONLY, field_read_allowlist=_COMMON_READ_FIELDS),
    _cap("dynamics_placeholder", ERPAdapterType.DYNAMICS_PLACEHOLDER, "Dynamics Placeholder Adapter", ERPAdapterOperationType.SEARCH_OBJECTS, ERPObjectType.SALE_ORDER, safety_tier=ERPAdapterSafetyTier.READ_ONLY, field_read_allowlist=_SALE_ORDER_READ_FIELDS),
    _cap("dynamics_placeholder", ERPAdapterType.DYNAMICS_PLACEHOLDER, "Dynamics Placeholder Adapter", ERPAdapterOperationType.INSPECT_SCHEMA, ERPObjectType.CUSTOM_OBJECT, safety_tier=ERPAdapterSafetyTier.READ_ONLY, supports_schema_inspection=True, field_read_allowlist=_CUSTOM_READ_FIELDS),
    _cap("dynamics_placeholder", ERPAdapterType.DYNAMICS_PLACEHOLDER, "Dynamics Placeholder Adapter", ERPAdapterOperationType.PREVIEW_WRITE, ERPObjectType.SALE_ORDER, safety_tier=ERPAdapterSafetyTier.PREVIEW_ONLY, supports_preview=True, field_read_allowlist=_SALE_ORDER_READ_FIELDS, field_write_allowlist=["state"]),
    _cap("netsuite_placeholder", ERPAdapterType.NETSUITE_PLACEHOLDER, "NetSuite Placeholder Adapter", ERPAdapterOperationType.READ_OBJECT, ERPObjectType.PARTNER, safety_tier=ERPAdapterSafetyTier.READ_ONLY, field_read_allowlist=_COMMON_READ_FIELDS),
    _cap("netsuite_placeholder", ERPAdapterType.NETSUITE_PLACEHOLDER, "NetSuite Placeholder Adapter", ERPAdapterOperationType.READ_OBJECT, ERPObjectType.INVOICE, safety_tier=ERPAdapterSafetyTier.READ_ONLY, field_read_allowlist=_INVOICE_READ_FIELDS),
    _cap("netsuite_placeholder", ERPAdapterType.NETSUITE_PLACEHOLDER, "NetSuite Placeholder Adapter", ERPAdapterOperationType.SEARCH_OBJECTS, ERPObjectType.PARTNER, safety_tier=ERPAdapterSafetyTier.READ_ONLY, field_read_allowlist=_COMMON_READ_FIELDS),
    _cap("netsuite_placeholder", ERPAdapterType.NETSUITE_PLACEHOLDER, "NetSuite Placeholder Adapter", ERPAdapterOperationType.SEARCH_OBJECTS, ERPObjectType.INVOICE, safety_tier=ERPAdapterSafetyTier.READ_ONLY, field_read_allowlist=_INVOICE_READ_FIELDS),
    _cap("netsuite_placeholder", ERPAdapterType.NETSUITE_PLACEHOLDER, "NetSuite Placeholder Adapter", ERPAdapterOperationType.PREVIEW_WRITE, ERPObjectType.INVOICE, safety_tier=ERPAdapterSafetyTier.PREVIEW_ONLY, supports_preview=True, field_read_allowlist=_INVOICE_READ_FIELDS, field_write_allowlist=["state"]),
    _cap("custom_rest_placeholder", ERPAdapterType.CUSTOM_REST_PLACEHOLDER, "Custom REST Placeholder Adapter", ERPAdapterOperationType.READ_OBJECT, ERPObjectType.CUSTOM_OBJECT, safety_tier=ERPAdapterSafetyTier.READ_ONLY, field_read_allowlist=_CUSTOM_READ_FIELDS),
    _cap("custom_rest_placeholder", ERPAdapterType.CUSTOM_REST_PLACEHOLDER, "Custom REST Placeholder Adapter", ERPAdapterOperationType.SEARCH_OBJECTS, ERPObjectType.CUSTOM_OBJECT, safety_tier=ERPAdapterSafetyTier.READ_ONLY, field_read_allowlist=_CUSTOM_READ_FIELDS),
    _cap("custom_rest_placeholder", ERPAdapterType.CUSTOM_REST_PLACEHOLDER, "Custom REST Placeholder Adapter", ERPAdapterOperationType.INSPECT_SCHEMA, ERPObjectType.CUSTOM_OBJECT, safety_tier=ERPAdapterSafetyTier.READ_ONLY, supports_schema_inspection=True, field_read_allowlist=_CUSTOM_READ_FIELDS),
    _cap("custom_rest_placeholder", ERPAdapterType.CUSTOM_REST_PLACEHOLDER, "Custom REST Placeholder Adapter", ERPAdapterOperationType.PREVIEW_WRITE, ERPObjectType.CUSTOM_OBJECT, safety_tier=ERPAdapterSafetyTier.PREVIEW_ONLY, supports_preview=True, field_read_allowlist=_CUSTOM_READ_FIELDS, field_write_allowlist=["status"]),
]


def list_erp_adapter_identities() -> list[ERPAdapterIdentity]:
    return list(_ADAPTER_IDENTITIES)


def list_erp_adapter_capabilities(adapter_id: str) -> list[ERPAdapterCapability]:
    return [cap for cap in _CAPABILITIES if cap.adapter_id == adapter_id]


def list_all_erp_adapter_capabilities() -> list[ERPAdapterCapability]:
    return list(_CAPABILITIES)


def find_erp_adapter_capability(
    adapter_id: str,
    operation_type: ERPAdapterOperationType,
    object_type: ERPObjectType,
) -> ERPAdapterCapability | None:
    for capability in _CAPABILITIES:
        if (
            capability.adapter_id == adapter_id
            and capability.operation_type == operation_type
            and capability.object_type == object_type
        ):
            return capability
    return None


def _identity_by_id(adapter_id: str) -> ERPAdapterIdentity | None:
    for identity in _ADAPTER_IDENTITIES:
        if identity.adapter_id == adapter_id:
            return identity
    return None


def check_erp_adapter_capability(request: ERPAdapterCapabilityCheckRequest) -> ERPAdapterCapabilityCheckResult:
    identity = _identity_by_id(request.adapter_id)
    if identity is None:
        return ERPAdapterCapabilityCheckResult(
            adapter_id=request.adapter_id,
            adapter_type=ERPAdapterType.CUSTOM_REST_PLACEHOLDER,
            adapter_display_name=request.adapter_id,
            operation_type=request.operation_type,
            object_type=request.object_type,
            supported=False,
            safety_tier=ERPAdapterSafetyTier.FORBIDDEN,
            requires_credentials=False,
            requires_confirmed_token=False,
            supports_preview=False,
            supports_execution=False,
            supports_schema_inspection=False,
            supports_permission_inspection=False,
            field_read_allowlist=[],
            field_write_allowlist=[],
            blocking_reasons=["adapter_not_found"],
            safety_flags=default_safety_flags(),
        )

    capability = find_erp_adapter_capability(request.adapter_id, request.operation_type, request.object_type)
    if capability is None:
        return ERPAdapterCapabilityCheckResult(
            adapter_id=identity.adapter_id,
            adapter_type=identity.adapter_type,
            adapter_display_name=identity.display_name,
            operation_type=request.operation_type,
            object_type=request.object_type,
            supported=False,
            safety_tier=ERPAdapterSafetyTier.FORBIDDEN,
            requires_credentials=False,
            requires_confirmed_token=False,
            supports_preview=False,
            supports_execution=False,
            supports_schema_inspection=False,
            supports_permission_inspection=False,
            field_read_allowlist=[],
            field_write_allowlist=[],
            blocking_reasons=["capability_not_supported"],
            safety_flags=default_safety_flags(),
        )

    blocking_reasons = list(capability.blocking_reasons)
    supported = capability.supported
    allowlist = set(capability.field_read_allowlist) | set(capability.field_write_allowlist)
    for field in request.requested_fields:
        if field not in allowlist:
            supported = False
            blocking_reasons.append(f"requested_field_not_supported:{field}")

    return ERPAdapterCapabilityCheckResult(
        adapter_id=capability.adapter_id,
        adapter_type=capability.adapter_type,
        adapter_display_name=capability.adapter_display_name,
        operation_type=capability.operation_type,
        object_type=capability.object_type,
        supported=supported,
        safety_tier=capability.safety_tier,
        requires_credentials=capability.requires_credentials,
        requires_confirmed_token=capability.requires_confirmed_token,
        supports_preview=capability.supports_preview,
        supports_execution=False,
        supports_schema_inspection=capability.supports_schema_inspection,
        supports_permission_inspection=capability.supports_permission_inspection,
        field_read_allowlist=list(capability.field_read_allowlist),
        field_write_allowlist=list(capability.field_write_allowlist),
        blocking_reasons=blocking_reasons,
        safety_flags=default_safety_flags(),
    )
