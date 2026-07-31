"""Spec 92 Sec 7.2/7.5 -- explicit allowed-transition graphs.

The DB listener (`erpguard/db/model_packages/recommendations.py`) only
guards content-immutability and terminal-status exit; this module is what
actually validates *which* transition is legal, mirroring the split Phase
19 established (`SkillPackage`'s module docstring: "service owns the
graph, listener owns terminal-state").
"""

from __future__ import annotations

RECOMMENDATION_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"submitted", "rejected"},
    "submitted": {"approved", "rejected", "expired"},
    "approved": {"converted", "expired"},
    "converted": set(),
    "rejected": set(),
    "expired": set(),
}

ACTION_DRAFT_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"awaiting_inputs", "validated", "invalidated"},
    "awaiting_inputs": {"validated", "invalidated"},
    "validated": {"ready_for_run", "invalidated"},
    "ready_for_run": {"converted", "invalidated"},
    "converted": set(),
    "invalidated": set(),
}


class InvalidTransition(ValueError):
    pass


def require_transition(graph: dict[str, set[str]], *, current: str, target: str) -> None:
    allowed = graph.get(current, set())
    if target not in allowed:
        raise InvalidTransition(f"cannot_transition_from:{current}:to:{target}")
