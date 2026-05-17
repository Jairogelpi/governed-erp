from pydantic import BaseModel, Field

from erpguard.canonical.enums import PreflightDecision, RiskLevel


class PolicyAppliesTo(BaseModel):
    canonical_object: str
    canonical_action: str


class PolicyCheck(BaseModel):
    id: str
    type: str
    severity: str
    description: str


class PolicyDefinition(BaseModel):
    policy: str
    version: str
    status: str
    applies_to: PolicyAppliesTo
    description: str
    risk_level_on_fail: RiskLevel
    decision_on_fail: PreflightDecision
    checks: list[PolicyCheck] = Field(min_length=1)
