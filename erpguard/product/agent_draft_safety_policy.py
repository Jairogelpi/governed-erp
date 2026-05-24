from __future__ import annotations

from pydantic import BaseModel, Field


class SafetyViolation(BaseModel):
    code: str
    message: str


class SafetyPolicyResult(BaseModel):
    passed: bool
    violations: list[SafetyViolation] = Field(default_factory=list)
    runtime_mode: str = "dry_run_only"
    write_actions: bool = False
    requires_human_review: bool = True
    requires_approval: bool = True
    can_execute: bool = False
    enforced_invariants: list[str] = Field(default_factory=list)


_INVARIANTS = [
    "Draft runtime_mode must be dry_run_only",
    "Draft write_actions must be False",
    "Draft must include requires_human_review guard",
    "Draft must include no_generic_writes guard",
    "Draft can_execute must be False",
    "Draft is_advisory_only must be True",
    "No R3/R4 operations allowed",
    "No ERP writes allowed",
    "No browser automation allowed",
    "No MCP tool execution allowed",
]

_MANDATORY_GUARD_IDS = {
    "no_generic_writes", "no_r3_r4_writes",
    "no_raw_tool_execution", "requires_human_review",
}


def enforce_draft_safety(transform_result, proposal: dict) -> SafetyPolicyResult:
    violations: list[SafetyViolation] = []

    if transform_result.runtime_mode != "dry_run_only":
        violations.append(SafetyViolation(
            code="invalid_runtime_mode",
            message=f"runtime_mode must be 'dry_run_only', got '{transform_result.runtime_mode}'.",
        ))

    if transform_result.write_actions is not False:
        violations.append(SafetyViolation(
            code="write_actions_enabled",
            message="write_actions must be False on an advisory draft.",
        ))

    guards = proposal.get("guards", {})
    all_guard_ids = set(guards.get("all_guard_ids", []))
    mandatory_ids = {g.get("guard_id") for g in guards.get("mandatory_guards", [])}
    combined = all_guard_ids | mandatory_ids
    missing = _MANDATORY_GUARD_IDS - combined
    if missing:
        violations.append(SafetyViolation(
            code="missing_mandatory_guards",
            message=f"Mandatory guards missing from draft: {sorted(missing)}.",
        ))

    if proposal.get("can_execute") is True:
        violations.append(SafetyViolation(
            code="can_execute_true",
            message="Source proposal has can_execute=true — cannot promote to draft.",
        ))

    import json as _json
    try:
        draft_content = _json.loads(transform_result.draft_json)
        draft_safety = draft_content.get("safety", {})
        if draft_safety.get("can_execute") is not False:
            violations.append(SafetyViolation(
                code="draft_json_can_execute",
                message="draft_json safety.can_execute must be false.",
            ))
        if draft_safety.get("is_advisory_only") is not True:
            violations.append(SafetyViolation(
                code="draft_json_not_advisory",
                message="draft_json safety.is_advisory_only must be true.",
            ))
    except Exception:
        violations.append(SafetyViolation(
            code="draft_json_parse_error",
            message="draft_json could not be parsed for safety validation.",
        ))

    return SafetyPolicyResult(
        passed=len(violations) == 0,
        violations=violations,
        runtime_mode="dry_run_only",
        write_actions=False,
        requires_human_review=True,
        requires_approval=True,
        can_execute=False,
        enforced_invariants=_INVARIANTS,
    )
