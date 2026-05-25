from __future__ import annotations

import json
from dataclasses import dataclass, field

from erpguard.db.repositories import (
    create_agent_candidate_decision_event,
    get_latest_agent_candidate_decision,
    get_ui_skill_version_record,
)


@dataclass(frozen=True)
class GateCheck:
    check: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class AgentCandidateActivationGateResult:
    version_id: str
    skill_id: str
    gate_passed: bool
    activation_allowed: bool
    checks: list[GateCheck] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    latest_decision: str | None = None
    # Invariants
    can_execute: bool = False
    can_approve: bool = False
    is_advisory_only: bool = True
    blocking_reason: str = ""


def evaluate_activation_gate(
    version_id: str, session
) -> AgentCandidateActivationGateResult:
    """Evaluate the activation gate — reads only, does NOT activate."""
    version_row = get_ui_skill_version_record(session, version_id)
    if version_row is None:
        return AgentCandidateActivationGateResult(
            version_id=version_id,
            skill_id="",
            gate_passed=False,
            activation_allowed=False,
            blocking_reasons=["Version not found"],
            blocking_reason="version_not_found",
        )

    latest_decision = get_latest_agent_candidate_decision(session, version_id)
    checks: list[GateCheck] = []
    blocking_reasons: list[str] = []

    # Check 1: version must be candidate
    is_candidate = version_row.status == "candidate"
    checks.append(GateCheck(
        check="version_is_candidate",
        passed=is_candidate,
        detail=f"status={version_row.status}",
    ))
    if not is_candidate:
        blocking_reasons.append(f"Version status is '{version_row.status}' — expected 'candidate'")

    # Check 2: a human decision must exist
    has_decision = latest_decision is not None
    checks.append(GateCheck(
        check="human_decision_exists",
        passed=has_decision,
        detail=f"latest_decision={latest_decision.decision if latest_decision else 'none'}",
    ))
    if not has_decision:
        blocking_reasons.append("No human decision recorded — submit a decision first")

    # Check 3: latest decision must be 'approve'
    decision_is_approve = (
        latest_decision is not None and latest_decision.decision == "approve"
    )
    checks.append(GateCheck(
        check="latest_decision_is_approve",
        passed=decision_is_approve,
        detail=f"latest_decision={latest_decision.decision if latest_decision else 'none'}",
    ))
    if not decision_is_approve:
        blocking_reasons.append(
            "Latest decision is not 'approve' — human must approve before activation gate passes"
        )

    # Check 4: runtime_type safety
    runtime_safe = version_row.runtime_type in ("agent_advisory", "deterministic_ui")
    checks.append(GateCheck(
        check="runtime_type_safe",
        passed=runtime_safe,
        detail=f"runtime_type={version_row.runtime_type}",
    ))
    if not runtime_safe:
        blocking_reasons.append(f"runtime_type '{version_row.runtime_type}' is not in approved list")

    # Check 5: activation gate never activates — always requires separate human act
    checks.append(GateCheck(
        check="activation_requires_human_act",
        passed=True,
        detail="Gate evaluation only — activation requires explicit separate human action",
    ))

    gate_passed = len(blocking_reasons) == 0
    # activation_allowed is intentionally False — gate evaluates only, never activates
    activation_allowed = False

    create_agent_candidate_decision_event(
        session, version_id, "activation_gate_evaluated",
        "passed" if gate_passed else "failed",
        json.dumps({
            "gate_passed": gate_passed,
            "activation_allowed": activation_allowed,
            "blocking_reasons": blocking_reasons,
            "check_count": len(checks),
        }),
    )

    return AgentCandidateActivationGateResult(
        version_id=version_id,
        skill_id=version_row.skill_id,
        gate_passed=gate_passed,
        activation_allowed=activation_allowed,
        checks=checks,
        blocking_reasons=blocking_reasons,
        latest_decision=latest_decision.decision if latest_decision else None,
    )
