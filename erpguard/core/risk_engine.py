from erpguard.canonical.actions import CANONICAL_ACTIONS
from erpguard.canonical.enums import CanonicalAction, PreflightDecision, RiskLevel


_RISK_RANK: dict[RiskLevel, int] = {
    RiskLevel.R0: 0,
    RiskLevel.R1: 1,
    RiskLevel.R2: 2,
    RiskLevel.R3: 3,
    RiskLevel.R4: 4,
    RiskLevel.R5: 5,
}


def default_risk_level(canonical_action: CanonicalAction) -> RiskLevel:
    return CANONICAL_ACTIONS[canonical_action].default_risk_level


def canonical_object_for_action(canonical_action: CanonicalAction) -> str:
    return CANONICAL_ACTIONS[canonical_action].canonical_object


def is_approval_required_action(canonical_action: CanonicalAction) -> bool:
    return approval_required_for_risk(default_risk_level(canonical_action))


def max_risk_level(*levels: RiskLevel) -> RiskLevel:
    return max(levels, key=lambda level: _RISK_RANK[level])


def approval_required_for_risk(risk_level: RiskLevel) -> bool:
    return _RISK_RANK[risk_level] >= _RISK_RANK[RiskLevel.R3]


def allowed_decision_for_risk(risk_level: RiskLevel) -> PreflightDecision:
    if approval_required_for_risk(risk_level):
        return PreflightDecision.REQUIRE_APPROVAL
    return PreflightDecision.ALLOW
