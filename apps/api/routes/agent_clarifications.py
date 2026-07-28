from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.schemas.agent_clarifications import (
    ClarificationAuditResponse,
    ClarificationCompletenessResponse,
    ClarificationQuestionSummarySchema,
    ClarificationStateResponse,
    DraftMetadataRefreshResponse,
    MappingActionRequest,
    MappingActionResponse,
    SubmitAnswersRequest,
    SubmitAnswersResponse,
)
from erpguard.db.repositories import get_advisory_proposal, get_automation_draft
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.agent_clarification_answer import (
    SubmitAnswersRequest as ServiceSubmitRequest,
    QuestionAnswer,
    submit_answers,
)
from erpguard.product.agent_clarification_audit import get_clarification_audit
from erpguard.product.agent_clarification_completeness import compute_clarification_completeness
from erpguard.product.agent_clarification_state import get_clarification_state
from erpguard.product.agent_draft_metadata_refresh import refresh_draft_metadata
from erpguard.product.agent_mapping_confirmation import confirm_mapping, reject_mapping

router = APIRouter(prefix="/v1/agent-builder/advisory", tags=["agent-clarifications"])


def _proposal_not_found(proposal_id: str):
    return JSONResponse(
        status_code=404,
        content={"error": {"code": "proposal_not_found", "message": f"Proposal '{proposal_id}' not found."}},
    )


def _draft_not_found(draft_id: str):
    return JSONResponse(
        status_code=404,
        content={"error": {"code": "draft_not_found", "message": f"Draft '{draft_id}' not found."}},
    )


@router.get("/proposals/{proposal_id}/clarifications", response_model=ClarificationStateResponse)
def get_clarifications(proposal_id: str):
    init_db()
    session = SessionLocal()
    try:
        proposal = get_advisory_proposal(session, proposal_id)
        if proposal is None:
            return _proposal_not_found(proposal_id)
        state = get_clarification_state(proposal_id, session)
        return ClarificationStateResponse(
            proposal_id=state.proposal_id,
            total_questions=state.total_questions,
            answered_count=state.answered_count,
            pending_count=state.pending_count,
            all_answered=state.all_answered,
            questions=[
                ClarificationQuestionSummarySchema(**q.model_dump())
                for q in state.questions
            ],
        )
    finally:
        session.close()


@router.post("/proposals/{proposal_id}/clarifications/answers", response_model=SubmitAnswersResponse)
def submit_clarification_answers(proposal_id: str, request: SubmitAnswersRequest):
    init_db()
    session = SessionLocal()
    try:
        proposal = get_advisory_proposal(session, proposal_id)
        if proposal is None:
            return _proposal_not_found(proposal_id)
        service_req = ServiceSubmitRequest(
            answers=[QuestionAnswer(question_id=a.question_id, answer_text=a.answer_text)
                     for a in request.answers]
        )
        result = submit_answers(proposal_id, service_req, session)
        return SubmitAnswersResponse(**result.model_dump())
    finally:
        session.close()


@router.post("/proposals/{proposal_id}/mappings/{mapping_key}/confirm", response_model=MappingActionResponse)
def confirm_mapping_endpoint(proposal_id: str, mapping_key: str, request: MappingActionRequest = MappingActionRequest()):
    init_db()
    session = SessionLocal()
    try:
        proposal = get_advisory_proposal(session, proposal_id)
        if proposal is None:
            return _proposal_not_found(proposal_id)
        result = confirm_mapping(proposal_id, mapping_key, request.reason, session)
        return MappingActionResponse(**result.model_dump())
    finally:
        session.close()


@router.post("/proposals/{proposal_id}/mappings/{mapping_key}/reject", response_model=MappingActionResponse)
def reject_mapping_endpoint(proposal_id: str, mapping_key: str, request: MappingActionRequest = MappingActionRequest()):
    init_db()
    session = SessionLocal()
    try:
        proposal = get_advisory_proposal(session, proposal_id)
        if proposal is None:
            return _proposal_not_found(proposal_id)
        result = reject_mapping(proposal_id, mapping_key, request.reason, session)
        return MappingActionResponse(**result.model_dump())
    finally:
        session.close()


@router.get("/proposals/{proposal_id}/clarification-status", response_model=ClarificationCompletenessResponse)
def get_clarification_status(proposal_id: str):
    init_db()
    session = SessionLocal()
    try:
        proposal = get_advisory_proposal(session, proposal_id)
        if proposal is None:
            return _proposal_not_found(proposal_id)
        result = compute_clarification_completeness(proposal_id, session)
        return ClarificationCompletenessResponse(**result.model_dump())
    finally:
        session.close()


@router.post("/drafts/{draft_id}/refresh-from-clarifications", response_model=DraftMetadataRefreshResponse)
def refresh_draft_from_clarifications(draft_id: str):
    init_db()
    session = SessionLocal()
    try:
        draft = get_automation_draft(session, draft_id)
        if draft is None:
            return _draft_not_found(draft_id)
        result = refresh_draft_metadata(draft_id, session)
        return DraftMetadataRefreshResponse(**result.model_dump())
    finally:
        session.close()


@router.get("/proposals/{proposal_id}/clarification-audit", response_model=ClarificationAuditResponse)
def get_clarification_audit_endpoint(proposal_id: str):
    init_db()
    session = SessionLocal()
    try:
        proposal = get_advisory_proposal(session, proposal_id)
        if proposal is None:
            return _proposal_not_found(proposal_id)
        result = get_clarification_audit(proposal_id, session)
        return ClarificationAuditResponse(**result.model_dump())
    finally:
        session.close()
