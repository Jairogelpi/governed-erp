from erpguard.canonical.enums import CanonicalAction, PreflightDecision, RiskLevel
from erpguard.core.risk_engine import (
    allowed_decision_for_risk,
    approval_required_for_risk,
    canonical_object_for_action,
    default_risk_level,
    max_risk_level,
)


def test_confirm_sales_order_defaults_to_r3_sales_order():
    assert default_risk_level(CanonicalAction.CONFIRM_SALES_ORDER) is RiskLevel.R3
    assert canonical_object_for_action(CanonicalAction.CONFIRM_SALES_ORDER) == "SalesOrder"


def test_r3_or_higher_requires_approval():
    assert approval_required_for_risk(RiskLevel.R2) is False
    assert approval_required_for_risk(RiskLevel.R3) is True
    assert allowed_decision_for_risk(RiskLevel.R3) is PreflightDecision.REQUIRE_APPROVAL


def test_max_risk_level_uses_risk_ordering():
    assert max_risk_level(RiskLevel.R0, RiskLevel.R3, RiskLevel.R2) is RiskLevel.R3
