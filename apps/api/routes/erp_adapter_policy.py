from __future__ import annotations

from fastapi import APIRouter

from apps.api.schemas.erp_adapter_policy import (
    ERPAdapterPolicyCheckRequestSchema,
    ERPAdapterPolicyCheckResponse,
    ERPAdapterPolicySafetyFlagsSchema,
)
from erpguard.product.erp_adapter_contract import ERPAdapterOperationType, ERPObjectType
from erpguard.product.erp_adapter_safety_policy import (
    ERPAdapterPolicyCheckRequest,
    check_erp_adapter_policy,
)


router = APIRouter(prefix="/v1/operator-console", tags=["erp-adapter-policy"])


@router.post("/erp-adapters/policy-check", response_model=ERPAdapterPolicyCheckResponse)
def post_erp_adapter_policy_check(body: ERPAdapterPolicyCheckRequestSchema):
    result = check_erp_adapter_policy(
        ERPAdapterPolicyCheckRequest(
            adapter_id=body.adapter_id,
            operation_type=ERPAdapterOperationType(body.operation_type),
            object_type=ERPObjectType(body.object_type),
            requested_fields=body.requested_fields,
            actor=body.actor,
            has_confirmed_token=body.has_confirmed_token,
            has_credentials=body.has_credentials,
            phase=body.phase,
        )
    )
    return ERPAdapterPolicyCheckResponse(
        eligible=result.eligible,
        adapter_id=result.adapter_id,
        adapter_type=result.adapter_type.value,
        adapter_display_name=result.adapter_display_name,
        operation_type=result.operation_type.value,
        object_type=result.object_type.value,
        safety_tier=result.safety_tier.value,
        capability_supported=result.capability_supported,
        requires_confirmation=result.requires_confirmation,
        requires_credentials=result.requires_credentials,
        can_preview=result.can_preview,
        can_execute=result.can_execute,
        policy_phase=result.policy_phase,
        blocking_reasons=result.blocking_reasons,
        is_advisory_only=result.is_advisory_only,
        will_execute=result.will_execute,
        safety_flags=ERPAdapterPolicySafetyFlagsSchema(**result.safety_flags.model_dump(mode="json")),
    )
