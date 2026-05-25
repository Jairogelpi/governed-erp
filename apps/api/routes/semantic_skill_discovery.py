from __future__ import annotations

from fastapi import APIRouter

from apps.api.schemas.semantic_skill_discovery import (
    DiscoverySearchRequest,
    DiscoverySearchResponse,
    GovernanceGapSchema,
    GovernanceGapsResponse,
    LifecycleEventSchema,
    LifecycleSummaryResponse,
    RecommendationSchema,
    RecommendationsResponse,
    ReuseSuggestionsRequest,
    ReuseSuggestionsResponse,
    SimilarSkillHitSchema,
    SimilarSkillsRequest,
    SimilarSkillsResponse,
    SkillSearchHitSchema,
)
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.agent_recommendation_engine import get_recommendations
from erpguard.product.governance_gap_explainer import explain_governance_gaps
from erpguard.product.operator_next_step_recommender import recommend_next_steps
from erpguard.product.semantic_skill_discovery import search_skills
from erpguard.product.skill_lifecycle_summary import get_lifecycle_summary
from erpguard.product.skill_reuse_suggester import get_reuse_suggestions
from erpguard.product.skill_similarity_engine import find_similar_skills

router = APIRouter(
    prefix="/v1/agent-builder/discovery",
    tags=["semantic-skill-discovery"],
)


@router.post("/search", response_model=DiscoverySearchResponse)
def discovery_search(body: DiscoverySearchRequest):
    init_db()
    db = SessionLocal()
    try:
        r = search_skills(
            body.query,
            db,
            status_filter=body.status_filter,
            runtime_type_filter=body.runtime_type_filter,
            active_only=body.active_only,
            limit=body.limit,
        )
        return DiscoverySearchResponse(
            query=r.query,
            results=[
                SkillSearchHitSchema(
                    version_id=h.version_id,
                    skill_id=h.skill_id,
                    name=h.name,
                    status=h.status,
                    is_active=h.is_active,
                    runtime_type=h.runtime_type,
                    relevance_score=h.relevance_score,
                    match_reason=h.match_reason,
                    guard_names=h.guard_names,
                    step_count=h.step_count,
                )
                for h in r.results
            ],
            total_found=r.total_found,
        )
    finally:
        db.close()


@router.post("/similar-skills", response_model=SimilarSkillsResponse)
def similar_skills(body: SimilarSkillsRequest):
    init_db()
    db = SessionLocal()
    try:
        r = find_similar_skills(body.version_id, db, limit=body.limit)
        return SimilarSkillsResponse(
            reference_version_id=r.reference_version_id,
            reference_name=r.reference_name,
            similar=[
                SimilarSkillHitSchema(
                    version_id=h.version_id,
                    skill_id=h.skill_id,
                    name=h.name,
                    similarity_score=h.similarity_score,
                    shared_guards=h.shared_guards,
                    shared_step_types=h.shared_step_types,
                    status=h.status,
                    is_active=h.is_active,
                )
                for h in r.similar
            ],
            total_found=r.total_found,
            blocking_reason=r.blocking_reason,
        )
    finally:
        db.close()


@router.get("/skills/{version_id}/lifecycle-summary", response_model=LifecycleSummaryResponse)
def lifecycle_summary(version_id: str):
    init_db()
    db = SessionLocal()
    try:
        r = get_lifecycle_summary(version_id, db)
        return LifecycleSummaryResponse(
            version_id=r.version_id,
            skill_id=r.skill_id,
            name=r.name,
            status=r.status,
            is_active=r.is_active,
            runtime_type=r.runtime_type,
            governance_status=r.governance_status,
            has_human_decision=r.has_human_decision,
            human_decision=r.human_decision,
            has_activation_request=r.has_activation_request,
            has_run_preview=r.has_run_preview,
            llm_required=r.llm_required,
            lifecycle_events=[
                LifecycleEventSchema(
                    event_type=e.event_type,
                    from_status=e.from_status,
                    to_status=e.to_status,
                    actor=e.actor,
                    created_at=e.created_at,
                )
                for e in r.lifecycle_events
            ],
            preview_event_count=r.preview_event_count,
            blocking_reason=r.blocking_reason,
        )
    finally:
        db.close()


@router.get("/skills/{version_id}/governance-gaps", response_model=GovernanceGapsResponse)
def governance_gaps(version_id: str):
    init_db()
    db = SessionLocal()
    try:
        r = explain_governance_gaps(version_id, db)
        return GovernanceGapsResponse(
            version_id=r.version_id,
            skill_id=r.skill_id,
            gaps=[
                GovernanceGapSchema(
                    gap_type=g.gap_type,
                    description=g.description,
                    severity=g.severity,
                    suggested_action=g.suggested_action,
                )
                for g in r.gaps
            ],
            gap_count=r.gap_count,
            is_fully_governed=r.is_fully_governed,
            blocking_reason=r.blocking_reason,
        )
    finally:
        db.close()


@router.get("/skills/{version_id}/recommendations", response_model=RecommendationsResponse)
def recommendations(version_id: str):
    init_db()
    db = SessionLocal()
    try:
        r = get_recommendations(version_id, db)
        return RecommendationsResponse(
            version_id=r.version_id,
            skill_id=r.skill_id,
            recommendations=[
                RecommendationSchema(
                    priority=rec.priority,
                    action=rec.action,
                    description=rec.description,
                    endpoint_hint=rec.endpoint_hint,
                    category=rec.category,
                )
                for rec in r.recommendations
            ],
            governance_complete=r.governance_complete,
            blocking_reason=r.blocking_reason,
        )
    finally:
        db.close()


@router.post("/reuse-suggestions", response_model=ReuseSuggestionsResponse)
def reuse_suggestions(body: ReuseSuggestionsRequest):
    init_db()
    db = SessionLocal()
    try:
        r = get_reuse_suggestions(
            db,
            query=body.query,
            version_id=body.version_id,
            limit=body.limit,
        )
        return ReuseSuggestionsResponse(
            query=r.query,
            suggestions=[
                {
                    "version_id": s.version_id,
                    "skill_id": s.skill_id,
                    "name": s.name,
                    "reuse_rationale": s.reuse_rationale,
                    "similarity_score": s.similarity_score,
                    "is_active": s.is_active,
                    "governance_complete": s.governance_complete,
                    "next_step": s.next_step,
                }
                for s in r.suggestions
            ],
            total_found=r.total_found,
        )
    finally:
        db.close()
