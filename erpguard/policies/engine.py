from erpguard.canonical.enums import PreflightDecision, RiskLevel
from erpguard.canonical.objects import SalesOrder
from erpguard.core.errors import PolicyNotFoundError
from erpguard.invariants.formula import validate_sales_order_formulas
from erpguard.policies.results import PolicyEvaluationResult, PolicyIssue

FORMULA_GUARD_POLICY_ID = "formula_guard"
FORMULA_GUARD_POLICY_VERSION = "0.1.0"


def evaluate_formula_guard_policy(sales_order: SalesOrder) -> PolicyEvaluationResult:
    formula_summary = validate_sales_order_formulas(sales_order)
    evidence = {"formula_summary": formula_summary.model_dump(mode="json")}

    if formula_summary.is_valid:
        return PolicyEvaluationResult(
            decision=PreflightDecision.ALLOW,
            risk_level=RiskLevel.R0,
            summary="Formula validation passed for the sales order.",
            issues=[],
            warnings=[],
            evidence=evidence,
            policy_id=FORMULA_GUARD_POLICY_ID,
            policy_version=FORMULA_GUARD_POLICY_VERSION,
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
        decision=PreflightDecision.BLOCK,
        risk_level=RiskLevel.R3,
        summary=f"Sales order is blocked by Formula Guard with {formula_summary.error_count} issue(s).",
        issues=issues,
        warnings=[],
        evidence=evidence,
        policy_id=FORMULA_GUARD_POLICY_ID,
        policy_version=FORMULA_GUARD_POLICY_VERSION,
    )


class PolicyEngine:
    def evaluate(self, policy_id: str, target: SalesOrder) -> PolicyEvaluationResult:
        if policy_id == FORMULA_GUARD_POLICY_ID:
            return evaluate_formula_guard_policy(target)
        raise PolicyNotFoundError(f"Policy '{policy_id}' is not registered.")
