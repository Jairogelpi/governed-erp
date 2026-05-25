from __future__ import annotations

import json
from dataclasses import dataclass, field

from erpguard.db.repositories import (
    get_ui_skill_version_record,
    list_all_ui_skill_version_records,
    list_agent_skill_run_preview_events_for_version,
)
from erpguard.product.skill_similarity_engine import _jaccard, _extract_step_types, _tokenize


@dataclass(frozen=True)
class ReuseSuggestion:
    version_id: str
    skill_id: str
    name: str
    reuse_rationale: str
    similarity_score: float
    is_active: bool
    governance_complete: bool
    next_step: str


@dataclass(frozen=True)
class ReuseSuggestionsResult:
    query: str
    suggestions: list[ReuseSuggestion] = field(default_factory=list)
    total_found: int = 0
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


def _is_governance_complete(row, session) -> bool:
    if not row.is_active:
        return False
    preview_events = list_agent_skill_run_preview_events_for_version(session, row.id)
    return any(e.step == "run_preview_completed" for e in preview_events)


def _score_reuse(row, query_tokens: set[str], ref_guards: set[str], ref_step_types: set[str]) -> float:
    cand_guards = set(json.loads(row.guard_names_json or "[]"))
    cand_step_types = _extract_step_types(row.steps_json)
    guard_sim = _jaccard(ref_guards, cand_guards)
    step_sim = _jaccard(ref_step_types, cand_step_types)
    name_tokens = _tokenize(row.name)
    name_hits = len(query_tokens & name_tokens) / (len(query_tokens) or 1)
    return round(guard_sim * 0.4 + step_sim * 0.3 + name_hits * 0.3, 3)


def get_reuse_suggestions(
    session,
    *,
    query: str = "",
    version_id: str | None = None,
    limit: int = 10,
) -> ReuseSuggestionsResult:
    """Find active skills that could be reused — reads only, never executes."""
    query_tokens = _tokenize(query)
    ref_guards: set[str] = set()
    ref_step_types: set[str] = set()

    if version_id:
        ref = get_ui_skill_version_record(session, version_id)
        if ref is not None:
            ref_guards = set(json.loads(ref.guard_names_json or "[]"))
            ref_step_types = _extract_step_types(ref.steps_json)
            if not query_tokens:
                query_tokens = _tokenize(ref.name)

    active_rows = list_all_ui_skill_version_records(session, active_only=True, limit=500)
    suggestions: list[ReuseSuggestion] = []
    for row in active_rows:
        if version_id and row.id == version_id:
            continue
        score = _score_reuse(row, query_tokens, ref_guards, ref_step_types)
        if score == 0.0:
            continue
        gov_complete = _is_governance_complete(row, session)
        if gov_complete:
            rationale = "Fully governed active skill with matching scope — ready for reuse."
            next_step = "Review its lifecycle summary, then adapt input parameters."
        else:
            rationale = "Active skill with matching scope — governance preview not yet run."
            next_step = "Run preview first, then evaluate reuse suitability."
        suggestions.append(ReuseSuggestion(
            version_id=row.id,
            skill_id=row.skill_id,
            name=row.name,
            reuse_rationale=rationale,
            similarity_score=score,
            is_active=row.is_active,
            governance_complete=gov_complete,
            next_step=next_step,
        ))
    suggestions.sort(key=lambda s: s.similarity_score, reverse=True)
    suggestions = suggestions[:limit]
    return ReuseSuggestionsResult(
        query=query,
        suggestions=suggestions,
        total_found=len(suggestions),
    )
