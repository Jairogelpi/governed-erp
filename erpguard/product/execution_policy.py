from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class PolicyViolation:
    code: str
    message: str
    blocking: bool = True


@dataclass
class PolicyCheckResult:
    passed: bool
    violations: list[PolicyViolation] = field(default_factory=list)
    can_execute_real_writes: bool = False
    real_erp_writes_enabled: bool = False

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "can_execute_real_writes": False,
            "real_erp_writes_enabled": False,
            "violations": [{"code": v.code, "message": v.message, "blocking": v.blocking} for v in self.violations],
        }


_ALLOW_REAL_ODOO_WRITES = False
_FORBIDDEN_REAL_METHODS = {"create", "write", "unlink", "copy", "action_confirm", "action_done", "button_confirm", "button_validate"}


class ExecutionPolicyService:
    def __init__(self, session) -> None:
        self.session = session

    def check(self, skill_id: str, skill_version_id: str, inputs: dict) -> PolicyCheckResult:
        from erpguard.db.repositories import (
            get_latest_approval_request_for_skill,
            get_latest_gate_evaluation,
            get_latest_skill_version,
            get_skill,
            list_approval_decisions_for_skill,
        )

        violations: list[PolicyViolation] = []

        if _ALLOW_REAL_ODOO_WRITES:
            violations.append(PolicyViolation(
                code="real_writes_enabled",
                message="ALLOW_REAL_ODOO_WRITES=true is not permitted in this governance tier.",
            ))

        skill_row = get_skill(self.session, skill_id)
        if skill_row is None:
            return PolicyCheckResult(passed=False, violations=[PolicyViolation(code="skill_not_found", message=f"Skill '{skill_id}' not found.")])

        version_row = get_latest_skill_version(self.session, skill_id)
        if version_row is None:
            violations.append(PolicyViolation(code="no_skill_version", message="No skill version found."))
        else:
            try:
                pkg = json.loads(version_row.skill_package_json)
            except Exception:
                pkg = {}
            if pkg.get("write_actions", True) is True:
                violations.append(PolicyViolation(code="write_actions_enabled", message="Skill write_actions must be False."))
            if pkg.get("runtime_mode") != "dry_run_only":
                violations.append(PolicyViolation(code="runtime_mode_invalid", message="Skill runtime_mode must be dry_run_only."))
            if "no_odoo_writes" not in pkg.get("guards", []):
                violations.append(PolicyViolation(code="missing_no_odoo_writes_guard", message="Skill is missing no_odoo_writes guard."))
            if pkg.get("requires_approval_before_activation", True):
                approval_req = get_latest_approval_request_for_skill(self.session, skill_id)
                if approval_req is None:
                    violations.append(PolicyViolation(code="no_approval_request", message="Skill requires an approval request before execution."))
                else:
                    decisions = list_approval_decisions_for_skill(self.session, skill_id)
                    approved = next((d for d in decisions if d.decision == "approve"), None)
                    if approved is None:
                        violations.append(PolicyViolation(code="not_approved", message="Skill has not been approved. Submit an approval decision first."))
                gate = get_latest_gate_evaluation(self.session, skill_id)
                if gate is None or not gate.can_activate:
                    violations.append(PolicyViolation(code="activation_gate_not_open", message="Skill activation gate has not been opened. Run the gate first."))

        return PolicyCheckResult(passed=len(violations) == 0, violations=violations)
