from __future__ import annotations

import json
from dataclasses import dataclass, field

from erpguard.db.repositories import get_ui_skill_version_record, list_all_ui_skill_version_records


def _tokenize(text: str) -> set[str]:
    return {w.lower().strip("_-") for w in text.replace("-", " ").replace("_", " ").split() if w}


@dataclass(frozen=True)
class SimilarSkillHit:
    version_id: str
    skill_id: str
    name: str
    similarity_score: float
    shared_guards: list[str] = field(default_factory=list)
    shared_step_types: list[str] = field(default_factory=list)
    status: str = ""
    is_active: bool = False


@dataclass(frozen=True)
class SimilarSkillsResult:
    reference_version_id: str
    reference_name: str
    similar: list[SimilarSkillHit] = field(default_factory=list)
    total_found: int = 0
    blocking_reason: str = ""
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


def _extract_step_types(steps_json: str) -> set[str]:
    try:
        steps = json.loads(steps_json or "[]")
    except Exception:
        return set()
    return {s.get("type", "unknown") for s in steps if isinstance(s, dict)}


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def find_similar_skills(version_id: str, session, *, limit: int = 10) -> SimilarSkillsResult:
    """Find skills similar to the reference — reads only, never executes."""
    ref = get_ui_skill_version_record(session, version_id)
    if ref is None:
        return SimilarSkillsResult(
            reference_version_id=version_id,
            reference_name="",
            blocking_reason="version_not_found",
        )

    ref_guards = set(json.loads(ref.guard_names_json or "[]"))
    ref_step_types = _extract_step_types(ref.steps_json)

    candidates = list_all_ui_skill_version_records(session, limit=500)
    hits: list[SimilarSkillHit] = []
    for row in candidates:
        if row.id == version_id:
            continue
        cand_guards = set(json.loads(row.guard_names_json or "[]"))
        cand_step_types = _extract_step_types(row.steps_json)
        guard_sim = _jaccard(ref_guards, cand_guards)
        step_sim = _jaccard(ref_step_types, cand_step_types)
        score = round((guard_sim * 0.6 + step_sim * 0.4), 3)
        if score == 0.0:
            continue
        hits.append(SimilarSkillHit(
            version_id=row.id,
            skill_id=row.skill_id,
            name=row.name,
            similarity_score=score,
            shared_guards=sorted(ref_guards & cand_guards),
            shared_step_types=sorted(ref_step_types & cand_step_types),
            status=row.status,
            is_active=row.is_active,
        ))
    hits.sort(key=lambda h: h.similarity_score, reverse=True)
    hits = hits[:limit]
    return SimilarSkillsResult(
        reference_version_id=version_id,
        reference_name=ref.name,
        similar=hits,
        total_found=len(hits),
    )
