from __future__ import annotations

from dataclasses import dataclass, field

from erpguard.product.governance_gap_explainer import explain_governance_gaps
from erpguard.product.skill_lifecycle_summary import get_lifecycle_summary


@dataclass
class PrerequisiteState:
    version_exists: bool = False
    has_human_decision: bool = False
    decision_approved: bool = False
    has_activation_request: bool = False
    has_run_preview: bool = False
    is_active: bool = False
    governance_gaps: list[str] = field(default_factory=list)


def inspect_prerequisites(version_id: str | None, session) -> PrerequisiteState:
    """Read-only inspection of a version's governance state. No mutations."""
    if not version_id:
        return PrerequisiteState()

    try:
        summary = get_lifecycle_summary(version_id, session)
        gaps_result = explain_governance_gaps(version_id, session)
    except Exception:
        return PrerequisiteState()

    if getattr(summary, "blocking_reason", None) == "version_not_found":
        return PrerequisiteState()

    gap_types = [g.gap_type for g in gaps_result.gaps if not g.resolved]

    return PrerequisiteState(
        version_exists=True,
        has_human_decision=summary.has_human_decision,
        decision_approved="decision_not_approved" not in gap_types,
        has_activation_request=summary.has_activation_request,
        has_run_preview=summary.has_run_preview,
        is_active="not_activated" not in gap_types,
        governance_gaps=gap_types,
    )
