from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from erpguard.canonical.enums import CanonicalAction, PreflightDecision, RiskLevel
from erpguard.policies.results import PolicyEvaluationResult, PolicyIssue, PolicyWarning


class PreflightResult(BaseModel):
    model_config = ConfigDict(use_enum_values=False)

    id: str = Field(default_factory=lambda: f"pf_{uuid4().hex}")
    actor: dict[str, Any]
    canonical_action: CanonicalAction
    target_id: str
    decision: PreflightDecision
    risk_level: RiskLevel
    summary: str
    issues: list[PolicyIssue] = Field(default_factory=list)
    warnings: list[PolicyWarning] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)
    policy_id: str
    policy_version: str
    policy_result: PolicyEvaluationResult | None = None


PreflightIssue = PolicyIssue
