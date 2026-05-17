from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from erpguard.canonical.enums import PreflightDecision, RiskLevel


class PolicyResultModel(BaseModel):
    model_config = ConfigDict(use_enum_values=False)


class PolicyIssue(PolicyResultModel):
    code: str
    message: str
    line_id: str | None = None
    product_name: str | None = None
    expected_ml: Decimal | None = None
    actual_ml: Decimal | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)


class PolicyWarning(PolicyResultModel):
    code: str
    message: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class PolicyEvaluationResult(PolicyResultModel):
    decision: PreflightDecision
    risk_level: RiskLevel
    summary: str
    issues: list[PolicyIssue] = Field(default_factory=list)
    warnings: list[PolicyWarning] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)
    policy_id: str
    policy_version: str
