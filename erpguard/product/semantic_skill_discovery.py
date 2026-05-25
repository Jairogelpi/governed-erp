from __future__ import annotations

import json
from dataclasses import dataclass, field

from erpguard.db.repositories import list_all_ui_skill_version_records
from erpguard.product.skill_similarity_engine import _tokenize


@dataclass(frozen=True)
class SkillSearchHit:
    version_id: str
    skill_id: str
    name: str
    status: str
    is_active: bool
    runtime_type: str
    relevance_score: float
    match_reason: str
    guard_names: list[str] = field(default_factory=list)
    step_count: int = 0


@dataclass(frozen=True)
class DiscoverySearchResult:
    query: str
    results: list[SkillSearchHit] = field(default_factory=list)
    total_found: int = 0
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


def _score_version(row, query_tokens: set[str]) -> tuple[float, str]:
    if not query_tokens:
        return 0.5, "no_query"
    name_tokens = _tokenize(row.name)
    name_hits = len(query_tokens & name_tokens)
    guard_names: list[str] = json.loads(row.guard_names_json or "[]")
    guard_text = " ".join(guard_names)
    guard_tokens = _tokenize(guard_text)
    guard_hits = len(query_tokens & guard_tokens)
    try:
        steps = json.loads(row.steps_json or "[]")
    except Exception:
        steps = []
    step_descs = " ".join(s.get("description", "") + " " + s.get("type", "") for s in steps if isinstance(s, dict))
    step_tokens = _tokenize(step_descs)
    step_hits = len(query_tokens & step_tokens)
    score = (name_hits * 3 + guard_hits * 2 + step_hits) / (len(query_tokens) * 3 or 1)
    score = min(score, 1.0)
    if name_hits:
        reason = f"name_match({name_hits})"
    elif guard_hits:
        reason = f"guard_match({guard_hits})"
    elif step_hits:
        reason = f"step_match({step_hits})"
    else:
        reason = "no_match"
    return score, reason


def search_skills(
    query: str,
    session,
    *,
    status_filter: str | None = None,
    runtime_type_filter: str | None = None,
    active_only: bool = False,
    limit: int = 20,
) -> DiscoverySearchResult:
    """Keyword-based deterministic skill search — reads only, never executes."""
    rows = list_all_ui_skill_version_records(
        session,
        status_filter=status_filter,
        runtime_type_filter=runtime_type_filter,
        active_only=active_only,
        limit=500,
    )
    query_tokens = _tokenize(query)
    hits: list[SkillSearchHit] = []
    for row in rows:
        score, reason = _score_version(row, query_tokens)
        if score > 0 or not query_tokens:
            guard_names = json.loads(row.guard_names_json or "[]")
            try:
                steps = json.loads(row.steps_json or "[]")
            except Exception:
                steps = []
            hits.append(SkillSearchHit(
                version_id=row.id,
                skill_id=row.skill_id,
                name=row.name,
                status=row.status,
                is_active=row.is_active,
                runtime_type=row.runtime_type,
                relevance_score=round(score, 3),
                match_reason=reason,
                guard_names=guard_names,
                step_count=len(steps),
            ))
    hits.sort(key=lambda h: h.relevance_score, reverse=True)
    hits = hits[:limit]
    return DiscoverySearchResult(
        query=query,
        results=hits,
        total_found=len(hits),
    )
