from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from erpguard.product.agent_recommendation_engine import get_recommendations
from erpguard.product.governance_gap_explainer import explain_governance_gaps
from erpguard.product.operator_next_step_recommender import recommend_next_steps
from erpguard.product.semantic_skill_discovery import search_skills
from erpguard.product.skill_lifecycle_summary import get_lifecycle_summary
from erpguard.product.skill_reuse_suggester import get_reuse_suggestions
from erpguard.product.skill_similarity_engine import find_similar_skills


@dataclass
class RoutedResult:
    result_type: str
    data: Any
    version_id_used: str | None = None


def route_intent(
    intent: str,
    query: str,
    session,
    *,
    version_id: str | None = None,
) -> RoutedResult:
    """Route a classified intent to the correct Sprint 40 service — reads only."""
    if intent == "list_active_skills":
        r = search_skills("", session, active_only=True, limit=20)
        return RoutedResult(result_type="skill_list", data=r)

    if intent == "find_similar":
        if version_id:
            r = find_similar_skills(version_id, session, limit=10)
            return RoutedResult(result_type="similar_list", data=r, version_id_used=version_id)
        # Fall back to keyword search when no version context
        r = search_skills(query, session, limit=10)
        return RoutedResult(result_type="skill_list", data=r)

    if intent == "governance_gaps":
        if version_id:
            r = explain_governance_gaps(version_id, session)
            return RoutedResult(result_type="gap_list", data=r, version_id_used=version_id)
        # Return generic gap list across all active versions
        active = search_skills("", session, active_only=True, limit=5)
        return RoutedResult(result_type="skill_list", data=active)

    if intent == "preview_ready":
        r = search_skills("", session, active_only=True, limit=20)
        return RoutedResult(result_type="skill_list", data=r)

    if intent == "next_step":
        if version_id:
            r = recommend_next_steps(version_id, session)
            return RoutedResult(result_type="next_steps", data=r, version_id_used=version_id)
        r = get_reuse_suggestions(session, query=query, limit=5)
        return RoutedResult(result_type="reuse_list", data=r)

    if intent == "lifecycle_status":
        if version_id:
            r = get_lifecycle_summary(version_id, session)
            return RoutedResult(result_type="lifecycle_summary", data=r, version_id_used=version_id)
        r = search_skills("", session, limit=10)
        return RoutedResult(result_type="skill_list", data=r)

    if intent == "reuse_suggestions":
        r = get_reuse_suggestions(session, query=query, version_id=version_id, limit=10)
        return RoutedResult(result_type="reuse_list", data=r, version_id_used=version_id)

    # default: search_skills
    r = search_skills(query, session, limit=20)
    return RoutedResult(result_type="skill_list", data=r)
