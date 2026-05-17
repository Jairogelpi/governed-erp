from decimal import Decimal

import pytest

from erpguard.adapters.fake import FakeERPAdapter
from erpguard.canonical.enums import PreflightDecision, RiskLevel
from erpguard.canonical.objects import Product, SalesOrder, SalesOrderLine
from erpguard.core.errors import PolicyNotFoundError
from erpguard.policies.engine import PolicyEngine, evaluate_formula_guard_policy


def make_order_with_non_capacity_product() -> SalesOrder:
    return SalesOrder(
        id="so_skip",
        native_id="native_so_skip",
        reference="SO-SKIP",
        total_amount=Decimal("0"),
        lines=[
            SalesOrderLine(
                id="line_service",
                native_id="native_line_service",
                product=Product(
                    id="product_service",
                    native_id="native_product_service",
                    name="Consulting Service",
                    capacity_ml=None,
                ),
                quantity=Decimal("1"),
            )
        ],
    )


def test_valid_formula_returns_allow():
    order = FakeERPAdapter().get_sales_order("so_valid")

    result = evaluate_formula_guard_policy(order)

    assert result.decision is PreflightDecision.ALLOW
    assert result.risk_level is RiskLevel.R0
    assert result.policy_id == "formula_guard"
    assert result.policy_version == "0.1.0"
    assert result.issues == []
    assert "passed" in result.summary
    assert result.evidence["formula_summary"]["is_valid"] is True


def test_invalid_formula_returns_block():
    order = FakeERPAdapter().get_sales_order("so_formula_mismatch")

    result = evaluate_formula_guard_policy(order)

    assert result.decision is PreflightDecision.BLOCK
    assert result.risk_level is RiskLevel.R3
    assert len(result.issues) == 1
    assert "blocked" in result.summary


def test_empty_sales_order_returns_block():
    order = FakeERPAdapter().get_sales_order("so_empty_lines")

    result = evaluate_formula_guard_policy(order)

    assert result.decision is PreflightDecision.BLOCK
    assert result.issues[0].code == "sales_order_has_no_lines"


def test_skipped_non_capacity_product_does_not_block():
    result = evaluate_formula_guard_policy(make_order_with_non_capacity_product())

    assert result.decision is PreflightDecision.ALLOW
    assert result.risk_level is RiskLevel.R0
    assert result.issues == []
    assert result.evidence["formula_summary"]["skipped_lines_count"] == 1


def test_issues_preserve_formula_error_evidence():
    order = FakeERPAdapter().get_sales_order("so_formula_mismatch")

    result = evaluate_formula_guard_policy(order)
    issue = result.issues[0]

    assert issue.code == "formula_ml_per_unit_mismatch"
    assert issue.line_id == "line_formula_mismatch"
    assert issue.product_name == "Mikado 100 ML"
    assert issue.expected_ml == Decimal("100")
    assert issue.actual_ml == Decimal("80")
    assert issue.evidence["line_id"] == "line_formula_mismatch"


def test_policy_engine_supports_formula_guard_only_for_now():
    order = FakeERPAdapter().get_sales_order("so_valid")

    result = PolicyEngine().evaluate("formula_guard", order)

    assert result.decision is PreflightDecision.ALLOW


def test_unknown_policy_id_raises_clear_domain_exception():
    order = FakeERPAdapter().get_sales_order("so_valid")

    with pytest.raises(PolicyNotFoundError) as exc_info:
        PolicyEngine().evaluate("unknown_policy", order)

    assert "unknown_policy" in str(exc_info.value)
