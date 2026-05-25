from __future__ import annotations

import json
from dataclasses import dataclass, field

from erpguard.db.repositories import (
    create_agent_candidate_activation_request_event,
    get_agent_candidate_activation_request_by_version,
    get_latest_agent_candidate_decision,
    get_ui_skill_version_record,
)


@dataclass(frozen=True)
class FinalGateCheck:
    check: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class FinalActivationGateResult:
    version_id: str
    skill_id: str
    gate_passed: bool
    activation_allowed: bool  # always False — requires a future dedicated flow
    checks: list[FinalGateCheck] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    request_id: str = ""
    request_status: str = ""
    can_execute: bool = False
    can_approve: bool = False
    is_advisory_only: bool = True
    blocking_reason: str = ""


def evaluate_final_activation_gate(
    version_id: str, session
) -> FinalActivationGateResult:
    """Evaluate the final activation gate — reads only, never activates."""
    version_row = get_ui_skill_version_record(session, version_id)
    if version_row is None:
        return FinalActivationGateResult(
            version_id=version_id,
            skill_id="",
            gate_passed=False,
            activation_allowed=False,
            blocking_reasons=["Version not found"],
            blocking_reason="version_not_found",
        )

    latest_decision = get_latest_agent_candidate_decision(session, version_id)
    activation_req = get_agent_candidate_activation_request_by_version(session, version_id)

    checks: list[FinalGateCheck] = []
    blocking_reasons: list[str] = []

    is_candidate = version_row.status == "candidate"
    checks.append(FinalGateCheck(
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
    checks.append(FinalGateCheck(
        check="approved_decision_exists",
        passed=has_approve,
        detail=f"latest_decision={latest_decision.decision if latest_decision else 'none'}",
    ))
    if not has_approve:
        blocking_reasons.append(
            "No approved decision — submit an approval decision first"
        )

    has_request = activation_req is not None
    checks.append(FinalGateCheck(
        check="activation_request_exists",
        passed=has_request,
        detail=f"request_id={activation_req.id if activation_req else 'none'}",
    ))
    if not has_request:
        blocking_reasons.append(
            "No explicit activation request — POST activation-request first"
        )

    runtime_safe = version_row.runtime_type in ("agent_advisory", "deterministic_ui")
    checks.append(FinalGateCheck(
        check="runtime_type_safe",
        passed=runtime_safe,
        detail=f"runtime_type={version_row.runtime_type}",
    ))
    if not runtime_safe:
        blocking_reasons.append(
            f"runtime_type '{version_row.runtime_type}' not in approved list"
        )

    # activation_allowed is always False — requires a dedicated future activation flow
    checks.append(FinalGateCheck(
        check="activation_requires_separate_explicit_step",
        passed=True,
        detail="Final gate evaluates only — actual activation requires a dedicated future flow",
    ))

    gate_passed = len(blocking_reasons) == 0
    activation_allowed = False  # ALWAYS

    create_agent_candidate_activation_request_event(
        session, version_id, "final_activation_gate_evaluated",
        "passed" if gate_passed else "failed",
        json.dumps({
            "gate_passed": gate_passed,
            "activation_allowed": activation_allowed,
            "check_count": len(checks),
            "blocking_reasons": blocking_reasons,
        }),
    )

    return FinalActivationGateResult(
        version_id=version_id,
        skill_id=version_row.skill_id,
        gate_passed=gate_passed,
        activation_allowed=activation_allowed,
        checks=checks,
        blocking_reasons=blocking_reasons,
        request_id=activation_req.id if activation_req else "",
        request_status=activation_req.request_status if activation_req else "",
    )
