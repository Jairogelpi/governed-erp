from __future__ import annotations

import json
from dataclasses import dataclass, field

from erpguard.db.repositories import get_automation_draft


_FORBIDDEN_ODOO_STEP_PATTERNS = {"action_confirm", "action_done", "button_confirm", "button_validate", ".write(", ".create(", ".unlink(", ".copy("}


@dataclass
class ValidationIssue:
    code: str
    message: str
    severity: str = "blocking"


@dataclass
class ValidationResult:
    draft_id: str
    passed: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "draft_id": self.draft_id,
            "passed": self.passed,
            "issues": [{"code": i.code, "message": i.message, "severity": i.severity} for i in self.issues],
        }


class DraftValidatorService:
    def __init__(self, session) -> None:
        self.session = session

    def validate(self, draft_id: str) -> ValidationResult:
        draft = get_automation_draft(self.session, draft_id)
        issues: list[ValidationIssue] = []

        if draft is None:
            return ValidationResult(
                draft_id=draft_id,
                passed=False,
                issues=[ValidationIssue(code="draft_not_found", message=f"AutomationDraft '{draft_id}' was not found.")],
            )

        if draft.write_actions:
            issues.append(ValidationIssue(
                code="write_actions_enabled",
                message="Draft has write_actions=True. All compiled skills must have write_actions=False.",
            ))

        if draft.runtime_mode != "dry_run_only":
            issues.append(ValidationIssue(
                code="invalid_runtime_mode",
                message=f"Draft runtime_mode is '{draft.runtime_mode}'. Must be 'dry_run_only'.",
            ))

        try:
            package = json.loads(draft.draft_json)
        except (json.JSONDecodeError, ValueError):
            issues.append(ValidationIssue(code="invalid_draft_json", message="Draft package JSON is malformed."))
            return ValidationResult(draft_id=draft_id, passed=False, issues=issues)

        if package.get("write_actions", True):
            issues.append(ValidationIssue(
                code="package_write_actions_enabled",
                message="draft_package.write_actions must be False.",
            ))

        if package.get("runtime_mode") != "dry_run_only":
            issues.append(ValidationIssue(
                code="package_invalid_runtime_mode",
                message=f"draft_package.runtime_mode must be 'dry_run_only', got '{package.get('runtime_mode')}'.",
            ))

        guards = package.get("guards", [])
        if "no_odoo_writes" not in guards:
            issues.append(ValidationIssue(
                code="missing_no_odoo_writes_guard",
                message="Draft package is missing the 'no_odoo_writes' guard.",
            ))

        for step in package.get("steps", []):
            step_desc = step.get("description", "").lower()
            for forbidden in _FORBIDDEN_ODOO_STEP_PATTERNS:
                if forbidden in step_desc:
                    issues.append(ValidationIssue(
                        code="forbidden_odoo_method_in_step",
                        message=f"Step '{step.get('id', '?')}' references forbidden Odoo method '{forbidden}'.",
                    ))

        return ValidationResult(draft_id=draft_id, passed=len(issues) == 0, issues=issues)
