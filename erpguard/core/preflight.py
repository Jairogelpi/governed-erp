from typing import Any

from erpguard.adapters.base import ERPAdapter
from erpguard.canonical.enums import CanonicalAction, PreflightDecision, RiskLevel
from erpguard.core.errors import ERPGuardError
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
) -> PreflightResult:
    try:
        sales_order = adapter.get_sales_order(target_id)
        policy_result = PolicyEngine().evaluate(policy_id, sales_order)
        return PreflightResult(
            actor=actor,
            canonical_action=canonical_action,
            target_id=target_id,
            decision=policy_result.decision,
            risk_level=policy_result.risk_level,
            summary=policy_result.summary,
            issues=policy_result.issues,
            warnings=policy_result.warnings,
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
                "policy_evidence": policy_result.evidence,
            },
            policy_id=policy_result.policy_id,
            policy_version=policy_result.policy_version,
            policy_result=policy_result,
        )
    except ERPGuardError as exc:
        return _failed_preflight(actor, canonical_action, target_id, policy_id, str(exc))


def _failed_preflight(
    actor: dict[str, Any],
    canonical_action: CanonicalAction,
    target_id: str,
    policy_id: str,
    message: str,
) -> PreflightResult:
    return PreflightResult(
        actor=actor,
        canonical_action=canonical_action,
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
