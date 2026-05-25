from __future__ import annotations

from dataclasses import dataclass, field

_VALID_DECISIONS = {"approve", "reject", "request_changes"}


@dataclass(frozen=True)
class DecisionValidationResult:
    valid: bool
    decision: str
    actor: str
    issues: list[str] = field(default_factory=list)


def validate_human_decision(
    decision: str,
    actor: str,
    rationale: str = "",
) -> DecisionValidationResult:
    issues: list[str] = []

    if not decision:
        issues.append("decision is required")
    elif decision not in _VALID_DECISIONS:
        issues.append(
            f"decision '{decision}' is not valid — must be one of: "
            + ", ".join(sorted(_VALID_DECISIONS))
        )

    if not actor or not actor.strip():
        issues.append("actor is required — who is making this decision?")

    if decision == "request_changes" and not rationale.strip():
        issues.append("rationale is required when decision is 'request_changes'")

    return DecisionValidationResult(
        valid=len(issues) == 0,
        decision=decision,
        actor=actor,
        issues=issues,
    )
