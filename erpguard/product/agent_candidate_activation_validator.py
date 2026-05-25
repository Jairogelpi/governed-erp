from __future__ import annotations

from dataclasses import dataclass, field

from erpguard.db.repositories import (
    get_agent_candidate_activation_request_by_version,
    get_latest_agent_candidate_decision,
    get_ui_skill_version_record,
    list_agent_candidate_activation_request_events_for_version,
)


@dataclass(frozen=True)
class ActivationCheck:
    check: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class CandidateActivationValidationResult:
    version_id: str
    skill_id: str
    eligible: bool
    checks: list[ActivationCheck] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    can_execute: bool = False
    can_approve: bool = False
    is_advisory_only: bool = True


def validate_candidate_for_activation(
    version_id: str, session
) -> CandidateActivationValidationResult:
    """Validate that a candidate is ready for explicit activation."""
    version_row = get_ui_skill_version_record(session, version_id)
    if version_row is None:
        return CandidateActivationValidationResult(
            version_id=version_id,
            skill_id="",
            eligible=False,
            blocking_reasons=["Version not found"],
        )

    # Already active — idempotent-safe short-circuit
    if version_row.status == "active" and version_row.is_active:
        return CandidateActivationValidationResult(
            version_id=version_id,
            skill_id=version_row.skill_id,
            eligible=True,
            checks=[ActivationCheck(
                check="already_active",
                passed=True,
                detail="Version is already active",
            )],
        )

    latest_decision = get_latest_agent_candidate_decision(session, version_id)
    activation_req = get_agent_candidate_activation_request_by_version(session, version_id)
    req_events = list_agent_candidate_activation_request_events_for_version(session, version_id)
    final_gate_evaluated = any(
        e.step == "final_activation_gate_evaluated" for e in req_events
    )

    checks: list[ActivationCheck] = []
    blocking_reasons: list[str] = []

    is_candidate = version_row.status == "candidate"
    checks.append(ActivationCheck(
        check="version_is_candidate",
        passed=is_candidate,
        detail=f"status={version_row.status}",
    ))
    if not is_candidate:
        blocking_reasons.append(
            f"Version status is '{version_row.status}' — expected 'candidate'"
        )

    has_approve = (
        latest_decision is not None and latest_decision.decision == "approve"
    )
    checks.append(ActivationCheck(
        check="approved_decision_exists",
        passed=has_approve,
        detail=f"latest_decision={latest_decision.decision if latest_decision else 'none'}",
    ))
    if not has_approve:
        blocking_reasons.append(
            "Latest decision is not 'approve' — submit an approval decision first"
        )

    has_request = activation_req is not None
    checks.append(ActivationCheck(
        check="activation_request_exists",
        passed=has_request,
        detail=f"request_id={activation_req.id if activation_req else 'none'}",
    ))
    if not has_request:
        blocking_reasons.append(
            "No explicit activation request — POST activation-request first"
        )

    checks.append(ActivationCheck(
        check="final_gate_evaluated",
        passed=final_gate_evaluated,
        detail="final_gate=True" if final_gate_evaluated else "final_gate=False",
    ))
    if not final_gate_evaluated:
        blocking_reasons.append(
            "Final activation gate has not been evaluated — call activation-request/final-gate first"
        )

    runtime_safe = version_row.runtime_type in ("agent_advisory", "deterministic_ui")
    checks.append(ActivationCheck(
        check="runtime_type_safe",
        passed=runtime_safe,
        detail=f"runtime_type={version_row.runtime_type}",
    ))
    if not runtime_safe:
        blocking_reasons.append(
            f"runtime_type '{version_row.runtime_type}' is not in approved list"
        )

    # Activation ≠ execution — always passes
    checks.append(ActivationCheck(
        check="activation_is_not_execution",
        passed=True,
        detail="Activation marks the version as governed-active — no run is created",
    ))

    return CandidateActivationValidationResult(
        version_id=version_id,
        skill_id=version_row.skill_id,
        eligible=len(blocking_reasons) == 0,
        checks=checks,
        blocking_reasons=blocking_reasons,
    )
