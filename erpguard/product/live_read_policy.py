from __future__ import annotations

import json

from erpguard.db.repositories import (
    get_latest_gate_evaluation,
    get_latest_skill_version,
    get_skill,
)
from erpguard.product.models import LiveReadPolicyResult, LiveReadPolicyViolation

_ALLOW_REAL_ODOO_READS = True
_ALLOW_LIVE_READ_EVIDENCE = True
_ALLOW_REAL_ODOO_WRITES = False


class LiveReadPolicyService:
    def __init__(self, session) -> None:
        self.session = session

    def check(self, skill_id: str) -> LiveReadPolicyResult:
        violations: list[LiveReadPolicyViolation] = []

        if _ALLOW_REAL_ODOO_WRITES:
            violations.append(LiveReadPolicyViolation(
                code="real_writes_enabled",
                message="ALLOW_REAL_ODOO_WRITES=true is not permitted.",
            ))

        skill_row = get_skill(self.session, skill_id)
        if skill_row is None:
            return LiveReadPolicyResult(
                passed=False,
                violations=[LiveReadPolicyViolation(code="skill_not_found", message=f"Skill '{skill_id}' not found.")],
            )

        version_row = get_latest_skill_version(self.session, skill_id)
        if version_row is None:
            violations.append(LiveReadPolicyViolation(code="no_skill_version", message="No skill version found."))
        else:
            try:
                pkg = json.loads(version_row.skill_package_json)
            except Exception:
                pkg = {}

            if pkg.get("write_actions", True) is True:
                violations.append(LiveReadPolicyViolation(
                    code="write_actions_enabled",
                    message="Skill write_actions must be False for live read.",
                ))
            if pkg.get("runtime_mode") != "dry_run_only":
                violations.append(LiveReadPolicyViolation(
                    code="runtime_mode_invalid",
                    message="Skill runtime_mode must be dry_run_only.",
                ))
            if "no_odoo_writes" not in pkg.get("guards", []):
                violations.append(LiveReadPolicyViolation(
                    code="missing_no_odoo_writes_guard",
                    message="Skill is missing no_odoo_writes guard.",
                ))
            if not pkg.get("connection_id"):
                violations.append(LiveReadPolicyViolation(
                    code="missing_connection_context",
                    message="Skill package has no connection_id — cannot resolve Odoo connection.",
                ))

        gate = get_latest_gate_evaluation(self.session, skill_id)
        if gate is None or not gate.can_activate:
            violations.append(LiveReadPolicyViolation(
                code="activation_gate_not_open",
                message="Skill activation gate has not been opened. Run the activation gate first.",
            ))

        return LiveReadPolicyResult(
            passed=len(violations) == 0,
            allow_real_odoo_reads=_ALLOW_REAL_ODOO_READS,
            allow_live_read_evidence=_ALLOW_LIVE_READ_EVIDENCE,
            can_execute_real_writes=False,
            real_erp_writes_enabled=False,
            violations=violations,
        )
