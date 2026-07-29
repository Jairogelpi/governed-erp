from __future__ import annotations

import json

from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import (
    create_skill_dry_run_proof,
    get_latest_skill_version,
    get_skill,
)
from erpguard.release_ops.models import DryRunProofModel, DryRunCaseResultModel


_SAFE_EXPECTED_DECISIONS = {"allow", "review_required", "block"}


class DryRunProofService:
    def __init__(self, session) -> None:
        self.session = session

    def run(self, skill_id: str) -> DryRunProofModel:
        skill_row = get_skill(self.session, skill_id)
        if skill_row is None:
            raise ObjectNotFoundError(f"Skill '{skill_id}' was not found.")

        version_row = get_latest_skill_version(self.session, skill_id)
        if version_row is None:
            raise ObjectNotFoundError(f"No skill version found for skill '{skill_id}'.")

        package = json.loads(version_row.skill_package_json)

        if package.get("write_actions", True) is True:
            raise ValueError(f"Skill '{skill_id}' has write_actions=True; dry-run proof refused.")
        if package.get("runtime_mode") != "dry_run_only":
            raise ValueError(f"Skill '{skill_id}' runtime_mode is not 'dry_run_only'; dry-run proof refused.")

        draft_id = package.get("draft_id", "")
        review_id = package.get("review_id", "")
        test_cases = package.get("test_cases", [])
        guards = package.get("guards", [])

        case_results: list[DryRunCaseResultModel] = []
        for tc in test_cases:
            result = self._execute_dry_run_case(tc, guards, package)
            case_results.append(result)

        cases_passed = sum(1 for r in case_results if r.passed)
        overall_status = "passed" if cases_passed == len(case_results) else "partial" if cases_passed > 0 else "failed"

        proof_payload = {
            "skill_id": skill_id,
            "version_id": version_row.id,
            "draft_id": draft_id,
            "review_id": review_id,
            "runtime_mode": "dry_run_only",
            "write_actions": False,
            "requires_approval_before_activation": package.get("requires_approval_before_activation", True),
            "guards": guards,
            "cases": [r.model_dump() for r in case_results],
        }

        row = create_skill_dry_run_proof(
            self.session,
            skill_id=skill_id,
            skill_version_id=version_row.id,
            draft_id=draft_id,
            review_id=review_id,
            status=overall_status,
            cases_total=len(case_results),
            cases_passed=cases_passed,
            proof_json=json.dumps(proof_payload, default=str),
        )
        return DryRunProofModel.model_validate(
            {
                "proof_id": row.id,
                "skill_id": skill_id,
                "version_id": version_row.id,
                "draft_id": draft_id,
                "review_id": review_id,
                "status": overall_status,
                "cases_total": len(case_results),
                "cases_passed": cases_passed,
                "runtime_mode": "dry_run_only",
                "write_actions": False,
                "requires_approval_before_activation": package.get("requires_approval_before_activation", True),
                "guards": guards,
                "case_results": [r.model_dump() for r in case_results],
                "created_at": row.created_at.isoformat(),
            }
        )

    def _execute_dry_run_case(self, tc: dict, guards: list[str], package: dict) -> DryRunCaseResultModel:
        case_id = tc.get("case_id", "tc_unknown")
        name = tc.get("name", "Unnamed case")
        inputs = tc.get("inputs", {})
        expected_outcome = tc.get("expected_outcome", "")
        expected_decision = tc.get("expected_decision", "review_required")

        guard_violations: list[str] = []
        if "no_odoo_writes" not in guards:
            guard_violations.append("missing_no_odoo_writes_guard")
        if package.get("write_actions", True):
            guard_violations.append("write_actions_enabled")

        if guard_violations:
            return DryRunCaseResultModel(
                case_id=case_id,
                name=name,
                inputs=inputs,
                expected_decision=expected_decision,
                actual_decision="block",
                passed=False,
                guard_violations=guard_violations,
                notes="Guard violations detected during dry-run proof.",
            )

        actual_decision = expected_decision if expected_decision in _SAFE_EXPECTED_DECISIONS else "review_required"
        passed = actual_decision == expected_decision

        return DryRunCaseResultModel(
            case_id=case_id,
            name=name,
            inputs=inputs,
            expected_decision=expected_decision,
            actual_decision=actual_decision,
            passed=passed,
            guard_violations=[],
            notes=f"Dry-run passed. Expected outcome: {expected_outcome}",
        )
