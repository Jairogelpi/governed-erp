from __future__ import annotations

from erpguard.product.execution_policy import ExecutionPolicyService, PolicyCheckResult


class ExecutionGateService:
    """Thin wrapper around ExecutionPolicyService used as the execution gate check."""

    def __init__(self, session) -> None:
        self.session = session

    def check(self, skill_id: str, skill_version_id: str, inputs: dict) -> PolicyCheckResult:
        policy = ExecutionPolicyService(self.session)
        return policy.check(skill_id, skill_version_id, inputs)
