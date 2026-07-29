"""Skill compiler v2 API (master spec section 18 / 23.6, Phase 14).

The compile route is nested under this repo's real process-candidates
prefix (`/v1/process-candidates`, not the spec's literal `/v1/candidates`
-- see `apps/api/routes/public_v1/candidates.py`), same dual-router
pattern `replays.py` used for its own process-scoped create route. The
get/approve routes are `/v1/skills/{skill_id}/versions/{version_id}` per
spec 23.6 -- checked against `apps/api/routes/public_v1/skills.py`'s
route decorators, no path collision (that legacy router has no
`/versions/` segment anywhere).
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.dependencies.identity import get_db, require_role
from apps.api.schemas.skill_packages import SkillCompileRequest, SkillPackageResponse
from erpguard.domain.identity.auth import Principal
from erpguard.domain.skills.service import (
    CandidateNotCompilable,
    NoAcceptableProof,
    SkillCompilerService,
    SkillPackageNotFound,
    SkillPackageValidationError,
)

candidates_router = APIRouter(prefix="/v1/process-candidates", tags=["skills"])
router = APIRouter(prefix="/v1/skills", tags=["skills"])


@candidates_router.post(
    "/{candidate_id}/compile", response_model=SkillPackageResponse, status_code=status.HTTP_201_CREATED
)
def compile_candidate(
    candidate_id: str,
    request: SkillCompileRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("admin")),
) -> SkillPackageResponse:
    try:
        row = SkillCompilerService(db).compile(
            tenant_id=principal.tenant_id,
            candidate_id=candidate_id,
            connector_id=request.connector_id,
            workflow_steps=[item.model_dump() for item in request.workflow_steps],
        )
    except CandidateNotCompilable as exc:
        detail = str(exc)
        if detail == "candidate_not_found":
            raise HTTPException(status_code=404, detail=detail) from exc
        raise HTTPException(status_code=400, detail=detail) from exc
    except NoAcceptableProof as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SkillPackageValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _response(row)


@router.get("/{skill_id}/versions/{version_id}", response_model=SkillPackageResponse)
def get_skill_package(
    skill_id: str,
    version_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("viewer")),
) -> SkillPackageResponse:
    try:
        row = SkillCompilerService(db).get_skill_package(
            tenant_id=principal.tenant_id, skill_id=skill_id, version=version_id
        )
    except SkillPackageNotFound as exc:
        raise HTTPException(status_code=404, detail="skill_package_not_found") from exc
    return _response(row)


@router.post("/{skill_id}/versions/{version_id}/approve", response_model=SkillPackageResponse)
def approve_skill_package(
    skill_id: str,
    version_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("admin")),
) -> SkillPackageResponse:
    try:
        SkillCompilerService(db).get_skill_package(tenant_id=principal.tenant_id, skill_id=skill_id, version=version_id)
        row = SkillCompilerService(db).approve(tenant_id=principal.tenant_id, skill_id=skill_id)
    except SkillPackageNotFound as exc:
        raise HTTPException(status_code=404, detail="skill_package_not_found") from exc
    except SkillPackageValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _response(row)


def _response(row) -> SkillPackageResponse:
    return SkillPackageResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        candidate_id=row.candidate_id,
        proof_id=row.proof_id,
        process_key=row.process_key,
        candidate_version=row.candidate_version,
        connector_id=row.connector_id,
        status=row.status,
        package=json.loads(row.package_json),
        validation_result=json.loads(row.validation_result_json),
        package_hash=row.package_hash,
        created_at=row.created_at.isoformat(),
        approved_at=row.approved_at.isoformat() if row.approved_at else None,
    )
