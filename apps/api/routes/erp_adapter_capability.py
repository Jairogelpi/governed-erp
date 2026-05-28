from __future__ import annotations

from fastapi import APIRouter

from apps.api.schemas.erp_adapter_capability import (
    ERPAdapterCapabilitiesResponse,
    ERPAdapterCapabilityCheckRequestSchema,
    ERPAdapterCapabilityCheckResponse,
    ERPAdapterCapabilitySchema,
    ERPAdapterIdentitySchema,
    ERPAdapterListResponse,
    ERPAdapterSafetyFlagsSchema,
)
from erpguard.product.erp_adapter_capability_registry import (
    ERPAdapterCapabilityCheckRequest,
    check_erp_adapter_capability,
    list_erp_adapter_capabilities,
    list_erp_adapter_identities,
)
from erpguard.product.erp_adapter_contract import ERPAdapterOperationType, ERPObjectType


router = APIRouter(prefix="/v1/operator-console", tags=["erp-adapter-capability"])


@router.get("/erp-adapters", response_model=ERPAdapterListResponse)
def get_erp_adapters():
    identities = list_erp_adapter_identities()
    return ERPAdapterListResponse(
        adapters=[
            ERPAdapterIdentitySchema(
                adapter_id=item.adapter_id,
                adapter_type=item.adapter_type.value,
                display_name=item.display_name,
                vendor_name=item.vendor_name,
                is_placeholder=item.is_placeholder,
                supports_real_connection=item.supports_real_connection,
            )
            for item in identities
        ]
    )


@router.get("/erp-adapters/{adapter_id}/capabilities", response_model=ERPAdapterCapabilitiesResponse)
def get_erp_adapter_capabilities(adapter_id: str):
    capabilities = list_erp_adapter_capabilities(adapter_id)
    if not capabilities:
        return ERPAdapterCapabilitiesResponse(
            adapter_id=adapter_id,
            adapter_found=False,
            capabilities=[],
            blocking_reasons=["adapter_not_found"],
        )
    return ERPAdapterCapabilitiesResponse(
        adapter_id=adapter_id,
        adapter_found=True,
        capabilities=[
            ERPAdapterCapabilitySchema(
                adapter_id=item.adapter_id,
                adapter_type=item.adapter_type.value,
                adapter_display_name=item.adapter_display_name,
                operation_type=item.operation_type.value,
                object_type=item.object_type.value,
                supported=item.supported,
                safety_tier=item.safety_tier.value,
                requires_credentials=item.requires_credentials,
                requires_confirmed_token=item.requires_confirmed_token,
                supports_preview=item.supports_preview,
                supports_execution=item.supports_execution,
                supports_schema_inspection=item.supports_schema_inspection,
                supports_permission_inspection=item.supports_permission_inspection,
                field_read_allowlist=item.field_read_allowlist,
                field_write_allowlist=item.field_write_allowlist,
                blocking_reasons=item.blocking_reasons,
            )
            for item in capabilities
        ],
    )


@router.post("/erp-adapters/capability-check", response_model=ERPAdapterCapabilityCheckResponse)
def post_erp_adapter_capability_check(body: ERPAdapterCapabilityCheckRequestSchema):
    result = check_erp_adapter_capability(
        ERPAdapterCapabilityCheckRequest(
            adapter_id=body.adapter_id,
            operation_type=ERPAdapterOperationType(body.operation_type),
            object_type=ERPObjectType(body.object_type),
            requested_fields=body.requested_fields,
        )
    )
    return ERPAdapterCapabilityCheckResponse(
        adapter_id=result.adapter_id,
        adapter_type=result.adapter_type.value,
        adapter_display_name=result.adapter_display_name,
        operation_type=result.operation_type.value,
        object_type=result.object_type.value,
        supported=result.supported,
        safety_tier=result.safety_tier.value,
        requires_credentials=result.requires_credentials,
        requires_confirmed_token=result.requires_confirmed_token,
        supports_preview=result.supports_preview,
        supports_execution=result.supports_execution,
        supports_schema_inspection=result.supports_schema_inspection,
        supports_permission_inspection=result.supports_permission_inspection,
        field_read_allowlist=result.field_read_allowlist,
        field_write_allowlist=result.field_write_allowlist,
        blocking_reasons=result.blocking_reasons,
        is_advisory_only=result.is_advisory_only,
        will_execute=result.will_execute,
        can_execute=result.can_execute,
        safety_flags=ERPAdapterSafetyFlagsSchema(**result.safety_flags.model_dump(mode="json")),
    )
