from __future__ import annotations

import json

from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import (
    create_activation_gate_evaluation,
    get_latest_approval_request_for_skill,
    get_latest_dry_run_proof_for_skill,
    get_latest_gate_evaluation,
    get_latest_skill_version,
    get_skill,
    list_approval_decisions_for_skill,
)
from erpguard.product.models import ActivationGateModel, GateCheckModel


class ActivationGateService:
    def __init__(self, session) -> None:
        self.session = session

    def evaluate(self, skill_id: str) -> ActivationGateModel:
        skill_row = get_skill(self.session, skill_id)
        if skill_row is None:
            raise ObjectNotFoundError(f"Skill '{skill_id}' was not found.")

        version_row = get_latest_skill_version(self.session, skill_id)
        approval_req = get_latest_approval_request_for_skill(self.session, skill_id)
        decisions = list_approval_decisions_for_skill(self.session, skill_id)
        proof_row = get_latest_dry_run_proof_for_skill(self.session, skill_id)

        approved_decision = next((d for d in decisions if d.decision == "approve"), None)

        checks: list[GateCheckModel] = [
            GateCheckModel(
                check_id="skill_exists",
                description="Skill record exists in the registry.",
                passed=True,
            ),
            GateCheckModel(
                check_id="has_version",
                description="Skill has at least one compiled version.",
                passed=version_row is not None,
                detail="" if version_row else "No skill version found.",
            ),
            GateCheckModel(
                check_id="runtime_mode_safe",
                description="Skill runtime_mode is dry_run_only.",
                passed=self._is_runtime_safe(version_row),
                detail="" if self._is_runtime_safe(version_row) else "runtime_mode is not dry_run_only.",
            ),
            GateCheckModel(
                check_id="write_actions_false",
                description="Skill write_actions is False.",
                passed=self._write_actions_false(version_row),
                detail="" if self._write_actions_false(version_row) else "write_actions is True.",
            ),
            GateCheckModel(
                check_id="no_odoo_writes_guard",
                description="Skill package includes no_odoo_writes guard.",
                passed=self._has_no_odoo_writes_guard(version_row),
                detail="" if self._has_no_odoo_writes_guard(version_row) else "Missing no_odoo_writes guard.",
            ),
            GateCheckModel(
                check_id="dry_run_proof_passed",
                description="Dry-run proof has been run and all cases passed.",
                passed=proof_row is not None and proof_row.status == "passed",
                detail="" if (proof_row and proof_row.status == "passed") else "No passing dry-run proof found.",
            ),
            GateCheckModel(
                check_id="approval_request_submitted",
                description="An approval request has been submitted.",
                passed=approval_req is not None,
                detail="" if approval_req else "No approval request found.",
            ),
            GateCheckModel(
                check_id="approval_decision_received",
                description="At least one approval decision has been recorded.",
                passed=approved_decision is not None,
                detail="" if approved_decision else "No approve decision found.",
            ),
            GateCheckModel(
                check_id="real_execution_blocked",
                description="can_execute_real_writes is always False (non-negotiable).",
                passed=True,
                detail="Real Odoo execution is permanently blocked at this governance tier.",
            ),
        ]

        all_passed = all(c.passed for c in checks)
        gate_status = "open" if all_passed else "blocked"

        row = create_activation_gate_evaluation(
            self.session,
            skill_id=skill_id,
            gate_status=gate_status,
            can_activate=all_passed,
            checks_json=json.dumps([c.model_dump() for c in checks], default=str),
            approval_request_id=approval_req.id if approval_req else None,
        )
        return ActivationGateModel.model_validate(
            {
                "gate_id": row.id,
                "skill_id": row.skill_id,
                "approval_request_id": row.approval_request_id,
                "gate_status": row.gate_status,
                "can_activate": row.can_activate,
                "can_execute_real_writes": False,
                "approved_for_real_execution": False,
                "checks": [c.model_dump() for c in checks],
                "created_at": row.created_at.isoformat(),
            }
        )

    def _is_runtime_safe(self, version_row) -> bool:
        if version_row is None:
            return False
        try:
            pkg = json.loads(version_row.skill_package_json)
            return pkg.get("runtime_mode") == "dry_run_only"
        except Exception:
            return False

    def _write_actions_false(self, version_row) -> bool:
        if version_row is None:
            return False
        try:
            pkg = json.loads(version_row.skill_package_json)
            return pkg.get("write_actions", True) is False
        except Exception:
            return False

    def _has_no_odoo_writes_guard(self, version_row) -> bool:
        if version_row is None:
            return False
        try:
            pkg = json.loads(version_row.skill_package_json)
            return "no_odoo_writes" in pkg.get("guards", [])
        except Exception:
            return False
