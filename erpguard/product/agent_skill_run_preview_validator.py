from __future__ import annotations

from dataclasses import dataclass, field

from erpguard.db.repositories import (
    get_agent_candidate_activation_request_by_version,
    get_ui_skill_version_record,
)


@dataclass(frozen=True)
class RunPreviewCheck:
    check: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class RunPreviewValidationResult:
    version_id: str
    skill_id: str
    eligible: bool
    checks: list[RunPreviewCheck] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


def validate_run_preview_eligibility(
    version_id: str, session
) -> RunPreviewValidationResult:
    """Validate that an active version is eligible for a manual run preview."""
    version_row = get_ui_skill_version_record(session, version_id)
    if version_row is None:
        return RunPreviewValidationResult(
            version_id=version_id,
            skill_id="",
            eligible=False,
            blocking_reasons=["Version not found"],
        )

    activation_req = get_agent_candidate_activation_request_by_version(session, version_id)

    checks: list[RunPreviewCheck] = []
    blocking_reasons: list[str] = []

    is_active = version_row.status == "active" and version_row.is_active
    checks.append(RunPreviewCheck(
        check="version_is_active",
        passed=is_active,
        detail=f"status={version_row.status}, is_active={version_row.is_active}",
    ))
    if not is_active:
        blocking_reasons.append(
            f"Version is not active (status={version_row.status}) — activate the candidate first"
        )

    from_agent_flow = activation_req is not None
    checks.append(RunPreviewCheck(
        check="from_agent_governance_flow",
        passed=from_agent_flow,
        detail=f"activation_request_id={activation_req.id if activation_req else 'none'}",
    ))
    if not from_agent_flow:
        blocking_reasons.append(
            "No activation request found — version must come from the agent governance flow"
        )

    runtime_safe = version_row.runtime_type in ("agent_advisory", "deterministic_ui")
    checks.append(RunPreviewCheck(
        check="runtime_type_safe",
        passed=runtime_safe,
        detail=f"runtime_type={version_row.runtime_type}",
    ))
    if not runtime_safe:
        blocking_reasons.append(
            f"runtime_type '{version_row.runtime_type}' is not in approved list"
        )

    no_llm = not version_row.llm_required
    checks.append(RunPreviewCheck(
        check="llm_not_required",
        passed=no_llm,
        detail=f"llm_required={version_row.llm_required}",
    ))
    if not no_llm:
        blocking_reasons.append(
            "LLM-required skills cannot enter manual run preview — deterministic only"
        )

    # Preview is always plan-only — never executes
    checks.append(RunPreviewCheck(
        check="preview_is_plan_only",
        passed=True,
        detail="Run preview builds a plan and checks gates — no actions are executed",
    ))

    return RunPreviewValidationResult(
        version_id=version_id,
        skill_id=version_row.skill_id,
        eligible=len(blocking_reasons) == 0,
        checks=checks,
        blocking_reasons=blocking_reasons,
    )
