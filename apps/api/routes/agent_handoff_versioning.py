from __future__ import annotations

from fastapi import APIRouter, HTTPException

from apps.api.schemas.agent_handoff_versioning import (
    CandidatePreviewStepSchema,
    EligibilityIssueSchema,
    HandoffCandidatePreviewResponse,
    HandoffCandidateReadinessResponse,
    HandoffCandidateResponse,
    HandoffEvidenceAttachmentResponse,
    HandoffVersionAuditEntrySchema,
    HandoffVersionAuditResponse,
    HandoffVersionEligibilityResponse,
    SourceHandoffResponse,
)
from erpguard.db.repositories import (
    get_agent_draft_handoff_packet_by_id,
)
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.agent_handoff_candidate_builder import create_candidate_version
from erpguard.product.agent_handoff_candidate_preview import preview_candidate_version
from erpguard.product.agent_handoff_candidate_readiness import check_candidate_readiness
from erpguard.product.agent_handoff_evidence_attachment import attach_evidence_to_candidate
from erpguard.product.agent_handoff_version_audit import get_version_audit
from erpguard.product.agent_handoff_version_eligibility import check_handoff_version_eligibility

router = APIRouter(
    prefix="/v1/agent-builder/advisory",
    tags=["agent-handoff-versioning"],
)


def _get_packet_or_404(packet_id: str, db):
    pkt = get_agent_draft_handoff_packet_by_id(db, packet_id)
    if pkt is None:
        raise HTTPException(status_code=404, detail=f"Handoff packet '{packet_id}' not found.")
    return pkt


@router.get("/handoff-packets/{packet_id}/version-eligibility",
            response_model=HandoffVersionEligibilityResponse)
def get_version_eligibility(packet_id: str):
    init_db()
    db = SessionLocal()
    try:
        _get_packet_or_404(packet_id, db)
        result = check_handoff_version_eligibility(packet_id, db)
        return HandoffVersionEligibilityResponse(
            packet_id=result.packet_id,
            eligible=result.eligible,
            candidate_exists=result.candidate_exists,
            packet_status=result.packet_status,
            readiness_score=result.readiness_score,
            issues=[EligibilityIssueSchema(code=i.code, message=i.message) for i in result.issues],
            can_execute=result.can_execute,
            can_approve=result.can_approve,
            is_advisory_only=result.is_advisory_only,
        )
    finally:
        db.close()


@router.post("/handoff-packets/{packet_id}/candidate-preview",
             response_model=HandoffCandidatePreviewResponse)
def post_candidate_preview(packet_id: str):
    init_db()
    db = SessionLocal()
    try:
        _get_packet_or_404(packet_id, db)
        result = preview_candidate_version(packet_id, db)
        return HandoffCandidatePreviewResponse(
            packet_id=result.packet_id,
            draft_id=result.draft_id,
            proposal_id=result.proposal_id,
            preview_skill_id=result.preview_skill_id,
            preview_version_name=result.preview_version_name,
            steps=[CandidatePreviewStepSchema(step_index=s.step_index, step_id=s.step_id,
                                               step_type=s.step_type, description=s.description)
                   for s in result.steps],
            guard_names=result.guard_names,
            guard_display=result.guard_display,
            evidence_summary=result.evidence_summary,
            readiness_score=result.readiness_score,
            would_be_status=result.would_be_status,
            candidate_exists=result.candidate_exists,
            existing_version_id=result.existing_version_id,
            can_execute=result.can_execute,
            can_approve=result.can_approve,
            is_advisory_only=result.is_advisory_only,
            blocking_reason=result.blocking_reason,
        )
    finally:
        db.close()


@router.post("/handoff-packets/{packet_id}/create-candidate-version",
             response_model=HandoffCandidateResponse)
def post_create_candidate_version(packet_id: str):
    init_db()
    db = SessionLocal()
    try:
        _get_packet_or_404(packet_id, db)
        result = create_candidate_version(packet_id, db)
        return HandoffCandidateResponse(
            packet_id=result.packet_id,
            version_id=result.version_id,
            skill_id=result.skill_id,
            version_number=result.version_number,
            status=result.status,
            draft_id=result.draft_id,
            proposal_id=result.proposal_id,
            is_cached=result.is_cached,
            can_execute=result.can_execute,
            can_approve=result.can_approve,
            is_advisory_only=result.is_advisory_only,
            blocking_reason=result.blocking_reason,
        )
    finally:
        db.close()


@router.post("/handoff-packets/{packet_id}/attach-evidence",
             response_model=HandoffEvidenceAttachmentResponse)
def post_attach_evidence(packet_id: str):
    init_db()
    db = SessionLocal()
    try:
        _get_packet_or_404(packet_id, db)
        result = attach_evidence_to_candidate(packet_id, db)
        return HandoffEvidenceAttachmentResponse(
            packet_id=result.packet_id,
            version_id=result.version_id,
            evidence_attached=result.evidence_attached,
            bridge_steps_passed=result.bridge_steps_passed,
            bridge_steps_total=result.bridge_steps_total,
            proof_plan_generated=result.proof_plan_generated,
            readiness_score=result.readiness_score,
            evidence_items=result.evidence_items,
            can_execute=result.can_execute,
            is_advisory_only=result.is_advisory_only,
            blocking_reason=result.blocking_reason,
        )
    finally:
        db.close()


@router.get("/handoff-packets/{packet_id}/candidate-readiness",
            response_model=HandoffCandidateReadinessResponse)
def get_candidate_readiness(packet_id: str):
    init_db()
    db = SessionLocal()
    try:
        _get_packet_or_404(packet_id, db)
        result = check_candidate_readiness(packet_id, db)
        return HandoffCandidateReadinessResponse(
            packet_id=result.packet_id,
            version_id=result.version_id,
            version_status=result.version_status,
            evidence_attached=result.evidence_attached,
            readiness_score=result.readiness_score,
            ready_for_promotion=result.ready_for_promotion,
            blocking_items=result.blocking_items,
            advisory_items=result.advisory_items,
            can_approve=result.can_approve,
            can_execute=result.can_execute,
            is_advisory_only=result.is_advisory_only,
            blocking_reason=result.blocking_reason,
        )
    finally:
        db.close()


@router.get("/handoff-packets/{packet_id}/version-audit",
            response_model=HandoffVersionAuditResponse)
def get_packet_version_audit(packet_id: str):
    init_db()
    db = SessionLocal()
    try:
        _get_packet_or_404(packet_id, db)
        result = get_version_audit(packet_id, db)
        return HandoffVersionAuditResponse(
            packet_id=result.packet_id,
            version_id=result.version_id,
            event_count=result.event_count,
            events=[HandoffVersionAuditEntrySchema(event_id=e.event_id, packet_id=e.packet_id, step=e.step,
                                                    status=e.status, detail=e.detail, created_at=e.created_at)
                    for e in result.events],
            can_execute=result.can_execute,
            is_advisory_only=result.is_advisory_only,
        )
    finally:
        db.close()


@router.get("/versions/{version_id}/source-handoff",
            response_model=SourceHandoffResponse)
def get_source_handoff(version_id: str):
    init_db()
    db = SessionLocal()
    try:
        from erpguard.db.models import AgentHandoffVersionLink
        link = (
            db.query(AgentHandoffVersionLink)
            .filter(AgentHandoffVersionLink.version_id == version_id)
            .first()
        )
        if link is None:
            raise HTTPException(
                status_code=404,
                detail=f"No handoff source found for version '{version_id}'.",
            )
        return SourceHandoffResponse(
            version_id=link.version_id,
            packet_id=link.packet_id,
            draft_id=link.draft_id,
            proposal_id=link.proposal_id,
            skill_id=link.skill_id,
            linked_at=link.created_at.isoformat(),
            can_execute=False,
            is_advisory_only=True,
        )
    finally:
        db.close()
