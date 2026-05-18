from erpguard.canonical.enums import CanonicalAction, PreflightDecision
from erpguard.canonical.objects import SalesOrder
from erpguard.core.errors import PolicyNotFoundError
from erpguard.core.risk_engine import allowed_decision_for_risk, default_risk_level, max_risk_level
from erpguard.invariants.formula import validate_sales_order_formulas
from erpguard.policies.loader import load_formula_guard_policy
from erpguard.policies.results import PolicyEvaluationResult, PolicyIssue

FORMULA_GUARD_POLICY_ID = "formula_guard"
FORMULA_GUARD_POLICY_VERSION = "0.1.0"


def evaluate_formula_guard_policy(
    sales_order: SalesOrder,
    canonical_action=CanonicalAction.VALIDATE_FORMULA,
) -> PolicyEvaluationResult:
    policy = load_formula_guard_policy()
    formula_summary = validate_sales_order_formulas(sales_order)
    evidence = {"formula_summary": formula_summary.model_dump(mode="json")}
    action_risk_level = default_risk_level(canonical_action)

    if formula_summary.is_valid:
        decision = allowed_decision_for_risk(action_risk_level)
        summary = "Formula validation passed for the sales order."
        if decision is PreflightDecision.REQUIRE_APPROVAL:
            summary = "Formula validation passed; the requested ERP action requires human approval."
        return PolicyEvaluationResult(
            decision=decision,
            risk_level=action_risk_level,
            summary=summary,
            issues=[],
            warnings=[],
            evidence=evidence,
            policy_id=policy.policy,
            policy_version=policy.version,
        )

    issues = [
        PolicyIssue(
            code=error.code,
            message=error.message,
            line_id=error.line_id,
            product_name=error.product_name,
            expected_ml=error.expected_ml,
            actual_ml=error.actual_ml,
            evidence=error.evidence,
        )
        for error in formula_summary.errors
    ]
    return PolicyEvaluationResult(
        decision=policy.decision_on_fail,
        risk_level=max_risk_level(action_risk_level, policy.risk_level_on_fail),
        summary=f"Sales order is blocked by Formula Guard with {formula_summary.error_count} issue(s).",
        issues=issues,
        warnings=[],
        evidence=evidence,
        policy_id=policy.policy,
        policy_version=policy.version,
    )


class PolicyEngine:
    def evaluate(
        self,
        policy_id: str,
        target: SalesOrder,
        canonical_action=CanonicalAction.VALIDATE_FORMULA,
    ) -> PolicyEvaluationResult:
        if policy_id == FORMULA_GUARD_POLICY_ID:
            return evaluate_formula_guard_policy(target, canonical_action=canonical_action)
        raise PolicyNotFoundError(f"Policy '{policy_id}' is not registered.")
