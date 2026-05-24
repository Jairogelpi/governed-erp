from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.schemas.agent_draft_handoff import (
    ApprovalHandoffPacketResponse,
    ApprovalReadinessResponse,
    DraftHandoffAuditResponse,
    DraftProofEvidenceResponse,
    DraftProofPlanResponse,
)
from erpguard.db.repositories import get_automation_draft
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.agent_draft_approval_handoff import create_approval_handoff_packet
from erpguard.product.agent_draft_approval_readiness import check_approval_readiness
from erpguard.product.agent_draft_handoff_audit import get_handoff_audit
from erpguard.product.agent_draft_proof_evidence import get_proof_evidence
from erpguard.product.agent_draft_proof_plan import generate_proof_plan

router = APIRouter(prefix="/v1/agent-builder/advisory", tags=["agent-draft-handoff"])


def _draft_not_found(draft_id: str):
    return JSONResponse(
        status_code=404,
        content={"error": {"code": "draft_not_found", "message": f"Draft '{draft_id}' not found."}},
    )


@router.post("/drafts/{draft_id}/handoff/proof-plan", response_model=DraftProofPlanResponse)
def handoff_proof_plan(draft_id: str):
    init_db()
    session = SessionLocal()
    try:
        draft = get_automation_draft(session, draft_id)
        if draft is None:
            return _draft_not_found(draft_id)
        result = generate_proof_plan(draft_id, session)
        return DraftProofPlanResponse(**result.model_dump())
    finally:
        session.close()


@router.get("/drafts/{draft_id}/handoff/evidence", response_model=DraftProofEvidenceResponse)
def handoff_evidence(draft_id: str):
    init_db()
    session = SessionLocal()
    try:
        draft = get_automation_draft(session, draft_id)
        if draft is None:
            return _draft_not_found(draft_id)
        result = get_proof_evidence(draft_id, session)
        return DraftProofEvidenceResponse(**result.model_dump())
    finally:
        session.close()


@router.get("/drafts/{draft_id}/handoff/readiness", response_model=ApprovalReadinessResponse)
def handoff_readiness(draft_id: str):
    init_db()
    session = SessionLocal()
    try:
        draft = get_automation_draft(session, draft_id)
        if draft is None:
            return _draft_not_found(draft_id)
        result = check_approval_readiness(draft_id, session)
        return ApprovalReadinessResponse(**result.model_dump())
    finally:
        session.close()


@router.post("/drafts/{draft_id}/handoff/packet", response_model=ApprovalHandoffPacketResponse)
def handoff_packet(draft_id: str):
    init_db()
    session = SessionLocal()
    try:
        draft = get_automation_draft(session, draft_id)
        if draft is None:
            return _draft_not_found(draft_id)
        result = create_approval_handoff_packet(draft_id, session)
        return ApprovalHandoffPacketResponse(**result.model_dump())
    finally:
        session.close()


@router.get("/drafts/{draft_id}/handoff/audit", response_model=DraftHandoffAuditResponse)
def handoff_audit(draft_id: str):
    init_db()
    session = SessionLocal()
    try:
        draft = get_automation_draft(session, draft_id)
        if draft is None:
            return _draft_not_found(draft_id)
        result = get_handoff_audit(draft_id, session)
        return DraftHandoffAuditResponse(**result.model_dump())
    finally:
        session.close()
