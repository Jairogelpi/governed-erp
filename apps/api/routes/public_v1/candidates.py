from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.dependencies.identity import get_db, require_role
from apps.api.schemas.candidates import CandidateCreateRequest, CandidateResponse
from erpguard.domain.identity.auth import Principal
from erpguard.domain.processes.candidates import (
    CandidateEvidenceNotFound,
    CandidateNotFound,
    CandidateService,
    CandidateValidationError,
)


router = APIRouter(prefix="/v1/process-candidates", tags=["process-candidates"])


@router.post("", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
def create_candidate(
    request: CandidateCreateRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("admin")),
) -> CandidateResponse:
    try:
        row = CandidateService(db).create_draft(
            tenant_id=principal.tenant_id,
            process_key=request.process_key,
            base_version=request.base_version,
            candidate_version=request.candidate_version,
            changes=request.changes,
            evidence_refs=request.evidence_refs,
            created_by=principal.user_id,
            proposal=request.structured_proposal,
        )
    except CandidateEvidenceNotFound as exc:
        raise HTTPException(status_code=404, detail="candidate_evidence_not_found") from exc
    except CandidateValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _response(row)


@router.post("/{candidate_id}/submit", response_model=CandidateResponse)
def submit_candidate(
    candidate_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("admin")),
) -> CandidateResponse:
    try:
        return _response(
            CandidateService(db).submit(
                tenant_id=principal.tenant_id,
                candidate_id=candidate_id,
            )
        )
    except CandidateNotFound as exc:
        raise HTTPException(status_code=404, detail="candidate_not_found") from exc
    except CandidateValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{candidate_id}", response_model=CandidateResponse)
def get_candidate(
    candidate_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("viewer")),
) -> CandidateResponse:
    try:
        return _response(
            CandidateService(db).get(
                tenant_id=principal.tenant_id,
                candidate_id=candidate_id,
            )
        )
    except CandidateNotFound as exc:
        raise HTTPException(status_code=404, detail="candidate_not_found") from exc


def _response(row) -> CandidateResponse:
    proposal = json.loads(row.proposal_json)
    return CandidateResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        process_key=row.process_key,
        base_version=row.base_version,
        candidate_version=row.candidate_version,
        status=row.status,
        changes=json.loads(row.patch_json),
        evidence_refs=json.loads(row.evidence_json),
        structured_proposal=proposal or None,
        base_definition_digest=row.base_definition_digest,
        patch_digest=row.patch_digest,
        candidate_definition=json.loads(row.candidate_definition_json),
        candidate_definition_digest=row.candidate_definition_digest,
        validation_status=row.validation_status,
        created_by=row.created_by,
        submitted_at=row.submitted_at.isoformat() if row.submitted_at else None,
    )
