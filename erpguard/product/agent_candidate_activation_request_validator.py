from __future__ import annotations

from dataclasses import dataclass, field

from erpguard.db.repositories import (
    get_latest_agent_candidate_decision,
    get_ui_skill_version_record,
    list_agent_candidate_decision_events_for_version,
)


@dataclass(frozen=True)
class EligibilityCheck:
    check: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class ActivationRequestValidationResult:
    version_id: str
    skill_id: str
    eligible: bool
    checks: list[EligibilityCheck] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    can_execute: bool = False
    can_approve: bool = False
    is_advisory_only: bool = True


def validate_activation_request_eligibility(
    version_id: str, session
) -> ActivationRequestValidationResult:
    """Validate that a version is eligible for an explicit activation request."""
    version_row = get_ui_skill_version_record(session, version_id)
    if version_row is None:
        return ActivationRequestValidationResult(
            version_id=version_id,
            skill_id="",
            eligible=False,
            blocking_reasons=["Version not found"],
        )

    latest_decision = get_latest_agent_candidate_decision(session, version_id)
    events = list_agent_candidate_decision_events_for_version(session, version_id)
    gate_evaluated = any(e.step == "activation_gate_evaluated" for e in events)

    checks: list[EligibilityCheck] = []
    blocking_reasons: list[str] = []

    is_candidate = version_row.status == "candidate"
    checks.append(EligibilityCheck(
        check="version_is_candidate",
        passed=is_candidate,
        detail=f"status={version_row.status}",
    ))
    if not is_candidate:
        blocking_reasons.append(f"Version status is '{version_row.status}' — expected 'candidate'")

    has_approve = (
        latest_decision is not None and latest_decision.decision == "approve"
    )
    checks.append(EligibilityCheck(
        check="approved_decision_exists",
        passed=has_approve,
        detail=f"latest_decision={latest_decision.decision if latest_decision else 'none'}",
    ))
    if not has_approve:
        blocking_reasons.append(
            "Latest decision is not 'approve' — submit an approval decision first"
        )

    checks.append(EligibilityCheck(
        check="activation_gate_evaluated",
        passed=gate_evaluated,
        detail="gate_evaluated=True" if gate_evaluated else "gate_evaluated=False",
    ))
    if not gate_evaluated:
        blocking_reasons.append(
            "Activation gate has not been evaluated — call activation-gate first"
        )

    runtime_safe = version_row.runtime_type in ("agent_advisory", "deterministic_ui")
    checks.append(EligibilityCheck(
        check="runtime_type_safe",
        passed=runtime_safe,
        detail=f"runtime_type={version_row.runtime_type}",
    ))
    if not runtime_safe:
        blocking_reasons.append(
            f"runtime_type '{version_row.runtime_type}' is not in approved list"
        )

    checks.append(EligibilityCheck(
        check="request_is_advisory_only",
        passed=True,
        detail="Activation request creates a pending artifact only — no automatic execution",
    ))

    return ActivationRequestValidationResult(
        version_id=version_id,
        skill_id=version_row.skill_id,
        eligible=len(blocking_reasons) == 0,
        checks=checks,
        blocking_reasons=blocking_reasons,
    )
