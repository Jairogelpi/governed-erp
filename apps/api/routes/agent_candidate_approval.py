from __future__ import annotations

from fastapi import APIRouter, HTTPException

from apps.api.schemas.agent_candidate_approval import (
    AgentCandidateApprovalAuditResponse,
    AgentCandidateApprovalBridgeResponse,
    AgentCandidateApprovalPacketResponse,
    AgentCandidateEvidenceCompletenessResponse,
    AgentCandidatePromotionReadinessResponse,
    AgentCandidateRiskSummaryResponse,
    ApprovalAuditEntrySchema,
    BridgeStepSchema,
    EvidenceItemSchema,
)
from erpguard.db.repositories import get_ui_skill_version_record
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.agent_candidate_approval_audit import get_approval_audit
from erpguard.product.agent_candidate_approval_bridge import run_approval_bridge
from erpguard.product.agent_candidate_approval_packet import create_approval_packet
from erpguard.product.agent_candidate_evidence_completeness import check_evidence_completeness
from erpguard.product.agent_candidate_promotion_readiness import check_candidate_promotion_readiness
from erpguard.product.agent_candidate_risk_summary import get_risk_summary

router = APIRouter(
    prefix="/v1/agent-builder/advisory",
    tags=["agent-candidate-approval"],
)


def _get_version_or_404(version_id: str, db):
    row = get_ui_skill_version_record(db, version_id)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Candidate version '{version_id}' not found.",
        )
    return row


@router.get(
    "/candidates/{version_id}/promotion-readiness",
    response_model=AgentCandidatePromotionReadinessResponse,
)
def get_promotion_readiness(version_id: str):
    init_db()
    db = SessionLocal()
    try:
        _get_version_or_404(version_id, db)
        r = check_candidate_promotion_readiness(version_id, db)
        return AgentCandidatePromotionReadinessResponse(
            version_id=r.version_id,
            skill_id=r.skill_id,
            version_status=r.version_status,
            readiness_score=r.readiness_score,
            evidence_attached=r.evidence_attached,
            approval_packet_exists=r.approval_packet_exists,
            ready_for_human_review=r.ready_for_human_review,
            blocking_items=r.blocking_items,
            advisory_items=r.advisory_items,
            can_execute=r.can_execute,
            can_approve=r.can_approve,
            is_advisory_only=r.is_advisory_only,
            blocking_reason=r.blocking_reason,
        )
    finally:
        db.close()


@router.get(
    "/candidates/{version_id}/evidence-completeness",
    response_model=AgentCandidateEvidenceCompletenessResponse,
)
def get_evidence_completeness(version_id: str):
    init_db()
    db = SessionLocal()
    try:
        _get_version_or_404(version_id, db)
        r = check_evidence_completeness(version_id, db)
        return AgentCandidateEvidenceCompletenessResponse(
            version_id=r.version_id,
            skill_id=r.skill_id,
            evidence_attached=r.evidence_attached,
            complete=r.complete,
            items_found=r.items_found,
            items_required=r.items_required,
            items=[
                EvidenceItemSchema(source=i.source, status=i.status,
                                    label=i.label, complete=i.complete)
                for i in r.items
            ],
            missing_sources=r.missing_sources,
            can_execute=r.can_execute,
            is_advisory_only=r.is_advisory_only,
            blocking_reason=r.blocking_reason,
        )
    finally:
        db.close()


@router.get(
    "/candidates/{version_id}/risk-summary",
    response_model=AgentCandidateRiskSummaryResponse,
)
def get_candidate_risk_summary(version_id: str):
    init_db()
    db = SessionLocal()
    try:
        _get_version_or_404(version_id, db)
        r = get_risk_summary(version_id, db)
        return AgentCandidateRiskSummaryResponse(
            version_id=r.version_id,
            skill_id=r.skill_id,
            runtime_type=r.runtime_type,
            runtime_label=r.runtime_label,
            llm_required=r.llm_required,
            guard_names=r.guard_names,
            guard_count=r.guard_count,
            risk_level=r.risk_level,
            risk_flags=r.risk_flags,
            can_execute=r.can_execute,
            is_advisory_only=r.is_advisory_only,
            blocking_reason=r.blocking_reason,
        )
    finally:
        db.close()


@router.post(
    "/candidates/{version_id}/approval-packet",
    response_model=AgentCandidateApprovalPacketResponse,
)
def post_approval_packet(version_id: str):
    init_db()
    db = SessionLocal()
    try:
        _get_version_or_404(version_id, db)
        r = create_approval_packet(version_id, db)
        return AgentCandidateApprovalPacketResponse(
            version_id=r.version_id,
            skill_id=r.skill_id,
            approval_packet_id=r.approval_packet_id,
            status=r.status,
            readiness_score=r.readiness_score,
            evidence_complete=r.evidence_complete,
            risk_level=r.risk_level,
            guard_names=r.guard_names,
            approval_instructions=r.approval_instructions,
            safety_note=r.safety_note,
            is_cached=r.is_cached,
            can_execute=r.can_execute,
            can_approve=r.can_approve,
            is_advisory_only=r.is_advisory_only,
            blocking_reason=r.blocking_reason,
        )
    finally:
        db.close()


@router.post(
    "/candidates/{version_id}/approval-request",
    response_model=AgentCandidateApprovalBridgeResponse,
)
def post_approval_request(version_id: str):
    init_db()
    db = SessionLocal()
    try:
        _get_version_or_404(version_id, db)
        r = run_approval_bridge(version_id, db)
        return AgentCandidateApprovalBridgeResponse(
            version_id=r.version_id,
            skill_id=r.skill_id,
            bridge_complete=r.bridge_complete,
            approval_packet_id=r.approval_packet_id,
            steps=[
                BridgeStepSchema(step=s.step, status=s.status, detail=s.detail)
                for s in r.steps
            ],
            steps_passed=r.steps_passed,
            steps_total=r.steps_total,
            blocking_reason=r.blocking_reason,
            can_execute=r.can_execute,
            can_approve=r.can_approve,
            is_advisory_only=r.is_advisory_only,
        )
    finally:
        db.close()


@router.get(
    "/candidates/{version_id}/approval-audit",
    response_model=AgentCandidateApprovalAuditResponse,
)
def get_candidate_approval_audit(version_id: str):
    init_db()
    db = SessionLocal()
    try:
        _get_version_or_404(version_id, db)
        r = get_approval_audit(version_id, db)
        return AgentCandidateApprovalAuditResponse(
            version_id=r.version_id,
            skill_id=r.skill_id,
            approval_packet_id=r.approval_packet_id,
            event_count=r.event_count,
            events=[
                ApprovalAuditEntrySchema(
                    event_id=e.event_id,
                    version_id=e.version_id,
                    step=e.step,
                    status=e.status,
                    detail=e.detail,
                    created_at=e.created_at,
                )
                for e in r.events
            ],
            can_execute=r.can_execute,
            is_advisory_only=r.is_advisory_only,
        )
    finally:
        db.close()
