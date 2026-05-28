from __future__ import annotations

from pydantic import Field

from erpguard.product.erp_adapter_capability_registry import (
    ERPAdapterCapabilityCheckRequest,
    check_erp_adapter_capability,
)
from erpguard.product.erp_adapter_contract import (
    ERPAdapterContractModel,
    ERPAdapterOperationType,
    ERPAdapterSafetyFlags,
    ERPAdapterSafetyTier,
    ERPAdapterType,
    ERPObjectType,
    default_safety_flags,
)


class ERPAdapterPolicyDecision(ERPAdapterContractModel):
    decision: str
    eligible: bool
    can_preview: bool
    can_execute: bool


class ERPAdapterPolicyCheckRequest(ERPAdapterContractModel):
    adapter_id: str
    operation_type: ERPAdapterOperationType
    object_type: ERPObjectType
    requested_fields: list[str] = Field(default_factory=list)
    actor: str | None = None
    has_confirmed_token: bool = False
    has_credentials: bool = False
    phase: str = "block_c_contract_only"


class ERPAdapterPolicyCheckResult(ERPAdapterContractModel):
    eligible: bool
    adapter_id: str
    adapter_type: ERPAdapterType
    adapter_display_name: str
    operation_type: ERPAdapterOperationType
    object_type: ERPObjectType
    safety_tier: ERPAdapterSafetyTier
    capability_supported: bool
    requires_confirmation: bool
    requires_credentials: bool
    can_preview: bool
    can_execute: bool
    policy_phase: str
    blocking_reasons: list[str] = Field(default_factory=list)
    is_advisory_only: bool = True
    will_execute: bool = False
    safety_flags: ERPAdapterSafetyFlags = Field(default_factory=default_safety_flags)


def _blocked(
    *,
    request: ERPAdapterPolicyCheckRequest,
    capability_result,
    blocking_reasons: list[str],
) -> ERPAdapterPolicyCheckResult:
    return ERPAdapterPolicyCheckResult(
        eligible=False,
        adapter_id=capability_result.adapter_id,
        adapter_type=capability_result.adapter_type,
        adapter_display_name=capability_result.adapter_display_name,
        operation_type=request.operation_type,
        object_type=request.object_type,
        safety_tier=capability_result.safety_tier,
        capability_supported=capability_result.supported,
        requires_confirmation=bool(capability_result.requires_confirmed_token)
        or capability_result.safety_tier == ERPAdapterSafetyTier.PREVIEW_ONLY,
        requires_credentials=capability_result.requires_credentials,
        can_preview=False,
        can_execute=False,
        policy_phase=request.phase,
        blocking_reasons=blocking_reasons,
        safety_flags=default_safety_flags(),
    )


def check_erp_adapter_policy(request: ERPAdapterPolicyCheckRequest) -> ERPAdapterPolicyCheckResult:
    capability = check_erp_adapter_capability(
        ERPAdapterCapabilityCheckRequest(
            adapter_id=request.adapter_id,
            operation_type=request.operation_type,
            object_type=request.object_type,
            requested_fields=request.requested_fields,
        )
    )

    blocking_reasons = list(capability.blocking_reasons)
    requires_confirmation = bool(capability.requires_confirmed_token) or (
        capability.safety_tier == ERPAdapterSafetyTier.PREVIEW_ONLY
    )

    if "adapter_not_found" in blocking_reasons:
        return _blocked(request=request, capability_result=capability, blocking_reasons=blocking_reasons)
    if "capability_not_supported" in blocking_reasons:
        return _blocked(request=request, capability_result=capability, blocking_reasons=blocking_reasons)
    if any(reason.startswith("requested_field_not_supported:") for reason in blocking_reasons):
        return _blocked(request=request, capability_result=capability, blocking_reasons=blocking_reasons)
    if capability.requires_credentials and not request.has_credentials:
        return _blocked(
            request=request,
            capability_result=capability,
            blocking_reasons=[*blocking_reasons, "credentials_required"],
        )
    if capability.requires_confirmed_token and not request.has_confirmed_token:
        return _blocked(
            request=request,
            capability_result=capability,
            blocking_reasons=[*blocking_reasons, "confirmed_token_required"],
        )

    if capability.safety_tier == ERPAdapterSafetyTier.READ_ONLY:
        return ERPAdapterPolicyCheckResult(
            eligible=True,
            adapter_id=capability.adapter_id,
            adapter_type=capability.adapter_type,
            adapter_display_name=capability.adapter_display_name,
            operation_type=capability.operation_type,
            object_type=capability.object_type,
            safety_tier=capability.safety_tier,
            capability_supported=capability.supported,
            requires_confirmation=requires_confirmation,
            requires_credentials=capability.requires_credentials,
            can_preview=True,
            can_execute=False,
            policy_phase=request.phase,
            blocking_reasons=[],
            safety_flags=default_safety_flags(),
        )

    if capability.safety_tier == ERPAdapterSafetyTier.PREVIEW_ONLY:
        return ERPAdapterPolicyCheckResult(
            eligible=True,
            adapter_id=capability.adapter_id,
            adapter_type=capability.adapter_type,
            adapter_display_name=capability.adapter_display_name,
            operation_type=capability.operation_type,
            object_type=capability.object_type,
            safety_tier=capability.safety_tier,
            capability_supported=capability.supported,
            requires_confirmation=True,
            requires_credentials=capability.requires_credentials,
            can_preview=True,
            can_execute=False,
            policy_phase=request.phase,
            blocking_reasons=[],
            safety_flags=default_safety_flags(),
        )

    if capability.safety_tier == ERPAdapterSafetyTier.SANDBOX_WRITE:
        if capability.adapter_type == ERPAdapterType.FAKE_ERP:
            return ERPAdapterPolicyCheckResult(
                eligible=True,
                adapter_id=capability.adapter_id,
                adapter_type=capability.adapter_type,
                adapter_display_name=capability.adapter_display_name,
                operation_type=capability.operation_type,
                object_type=capability.object_type,
                safety_tier=capability.safety_tier,
                capability_supported=capability.supported,
                requires_confirmation=requires_confirmation,
                requires_credentials=capability.requires_credentials,
                can_preview=True,
                can_execute=False,
                policy_phase=request.phase,
                blocking_reasons=[],
                safety_flags=default_safety_flags(),
            )
        return _blocked(
            request=request,
            capability_result=capability,
            blocking_reasons=["sandbox_write_not_available_for_adapter"],
        )

    if capability.safety_tier in {
        ERPAdapterSafetyTier.CONTROLLED_WRITE,
        ERPAdapterSafetyTier.HIGH_RISK_WRITE,
        ERPAdapterSafetyTier.FORBIDDEN,
    }:
        reason = {
            ERPAdapterSafetyTier.CONTROLLED_WRITE: "controlled_write_blocked_in_block_c",
            ERPAdapterSafetyTier.HIGH_RISK_WRITE: "high_risk_write_blocked_in_block_c",
            ERPAdapterSafetyTier.FORBIDDEN: "forbidden_operation",
        }[capability.safety_tier]
        return _blocked(
            request=request,
            capability_result=capability,
            blocking_reasons=[*blocking_reasons, reason],
        )

    return _blocked(
        request=request,
        capability_result=capability,
        blocking_reasons=[*blocking_reasons, "policy_decision_unavailable"],
    )
