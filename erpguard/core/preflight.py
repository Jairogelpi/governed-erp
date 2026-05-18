from typing import Any

from erpguard.adapters.base import ERPAdapter
from erpguard.canonical.enums import CanonicalAction, PreflightDecision, RiskLevel
from erpguard.core.errors import ERPGuardError
from erpguard.core.risk_engine import approval_required_for_risk, canonical_object_for_action
from erpguard.core.results import PreflightResult
from erpguard.policies.engine import FORMULA_GUARD_POLICY_VERSION, PolicyEngine
from erpguard.policies.results import PolicyIssue

PREFLIGHT_CREATED = "PREFLIGHT_CREATED"
PREFLIGHT_DECIDED = "PREFLIGHT_DECIDED"
PREFLIGHT_FAILED = "PREFLIGHT_FAILED"


def run_preflight(
    adapter: ERPAdapter,
    actor: dict[str, Any],
    canonical_action: CanonicalAction,
    target_id: str,
    policy_id: str = "formula_guard",
    action: dict[str, Any] | None = None,
    options: dict[str, Any] | None = None,
) -> PreflightResult:
    canonical_object = canonical_object_for_action(canonical_action)
    action_payload = action or {
        "canonical_action": canonical_action.value,
        "canonical_object": canonical_object,
        "target_id": target_id,
    }
    try:
        sales_order = adapter.get_sales_order(target_id)
        policy_result = PolicyEngine().evaluate(policy_id, sales_order, canonical_action=canonical_action)
        approval_required = policy_result.decision is PreflightDecision.REQUIRE_APPROVAL
        predicted_impact = _predicted_impact(canonical_action, options or {})
        return PreflightResult(
            actor=actor,
            action=action_payload,
            canonical_action=canonical_action,
            canonical_object=canonical_object,
            target_id=target_id,
            decision=policy_result.decision,
            risk_level=policy_result.risk_level,
            summary=policy_result.summary,
            issues=policy_result.issues,
            warnings=policy_result.warnings,
            predicted_impact=predicted_impact,
            approval_required=approval_required,
            evidence={
                "adapter": {"erp_type": adapter.get_erp_type().value},
                "target": {
                    "id": sales_order.id,
                    "native_id": sales_order.native_id,
                    "reference": sales_order.reference,
                },
                "policy": {
                    "policy_id": policy_result.policy_id,
                    "policy_version": policy_result.policy_version,
                },
                "risk": {
                    "risk_level": policy_result.risk_level.value,
                    "approval_required": approval_required,
                    "risk_requires_approval": approval_required_for_risk(policy_result.risk_level),
                },
                "predicted_impact": predicted_impact,
                "policy_evidence": policy_result.evidence,
            },
            policy_id=policy_result.policy_id,
            policy_version=policy_result.policy_version,
            policy_result=policy_result,
        )
    except ERPGuardError as exc:
        return _failed_preflight(actor, canonical_action, target_id, policy_id, str(exc), action_payload)


def _failed_preflight(
    actor: dict[str, Any],
    canonical_action: CanonicalAction,
    target_id: str,
    policy_id: str,
    message: str,
    action: dict[str, Any] | None = None,
) -> PreflightResult:
    canonical_object = canonical_object_for_action(canonical_action)
    return PreflightResult(
        actor=actor,
        action=action
        or {
            "canonical_action": canonical_action.value,
            "canonical_object": canonical_object,
            "target_id": target_id,
        },
        canonical_action=canonical_action,
        canonical_object=canonical_object,
        target_id=target_id,
        decision=PreflightDecision.BLOCK,
        risk_level=RiskLevel.R3,
        summary=f"Preflight failed closed for target '{target_id}': {message}",
        issues=[
            PolicyIssue(
                code="preflight_target_load_failed",
                message=message,
                evidence={"target_id": target_id, "error": message},
            )
        ],
        warnings=[],
        predicted_impact={},
        approval_required=False,
        evidence={
            "target": {"id": target_id},
            "policy": {
                "policy_id": policy_id,
                "policy_version": FORMULA_GUARD_POLICY_VERSION if policy_id == "formula_guard" else "unknown",
            },
            "failure": {"message": message},
        },
        policy_id=policy_id,
        policy_version=FORMULA_GUARD_POLICY_VERSION if policy_id == "formula_guard" else "unknown",
        policy_result=None,
    )


def _predicted_impact(canonical_action: CanonicalAction, options: dict[str, Any]) -> dict[str, Any]:
    if canonical_action is not CanonicalAction.CONFIRM_SALES_ORDER:
        return {}
    if options.get("simulate") is False:
        return {"simulation_status": "not_requested"}
    return {
        "simulation_status": "not_implemented",
        "simulation_level": "static_preflight_only",
    }
