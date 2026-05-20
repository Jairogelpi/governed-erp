from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.schemas.write_readiness import (
    WriteImpactPreviewResponse,
    WriteReadinessAssessmentResponse,
    WriteReadinessCertificationResponse,
    WriteReadinessSummaryResponse,
    WriteRollbackPlanResponse,
)
from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.write_impact_preview import WriteImpactPreviewService
from erpguard.product.write_readiness_assessment import WriteReadinessAssessmentService
from erpguard.product.write_readiness_certification import WriteReadinessCertificationService
from erpguard.product.write_rollback_plan import WriteRollbackPlanService

router = APIRouter(prefix="/v1/product", tags=["write-readiness"])


@router.post("/skills/{skill_id}/write-readiness-assessment", response_model=WriteReadinessAssessmentResponse)
def run_write_readiness_assessment(skill_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            result = WriteReadinessAssessmentService(session).run(skill_id)
        except ObjectNotFoundError as exc:
            return _not_found("skill_not_found", str(exc))
        return _assessment_to_dict(result)
    finally:
        session.close()


@router.get("/skills/{skill_id}/write-readiness-assessment", response_model=WriteReadinessAssessmentResponse)
def get_write_readiness_assessment(skill_id: str):
    init_db()
    session = SessionLocal()
    try:
        from erpguard.db.repositories import get_latest_write_readiness_assessment_for_skill
        row = get_latest_write_readiness_assessment_for_skill(session, skill_id)
        if row is None:
            return _not_found("assessment_not_found", f"No assessment found for skill '{skill_id}'.")
        result = WriteReadinessAssessmentService(session).get(row.id)
        return _assessment_to_dict(result)
    finally:
        session.close()


@router.post("/write-readiness-assessments/{assessment_id}/impact-preview", response_model=WriteImpactPreviewResponse)
def generate_impact_preview(assessment_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            result = WriteImpactPreviewService(session).generate(assessment_id)
        except ObjectNotFoundError as exc:
            return _not_found("assessment_not_found", str(exc))
        return result.model_dump()
    finally:
        session.close()


@router.get("/skills/{skill_id}/write-impact-preview", response_model=WriteImpactPreviewResponse)
def get_write_impact_preview(skill_id: str):
    init_db()
    session = SessionLocal()
    try:
        result = WriteImpactPreviewService(session).get_latest(skill_id)
        if result is None:
            return _not_found("impact_preview_not_found", f"No impact preview found for skill '{skill_id}'.")
        return result.model_dump()
    finally:
        session.close()


@router.post("/write-readiness-assessments/{assessment_id}/rollback-plan", response_model=WriteRollbackPlanResponse)
def draft_rollback_plan(assessment_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            result = WriteRollbackPlanService(session).draft(assessment_id)
        except ObjectNotFoundError as exc:
            return _not_found("assessment_not_found", str(exc))
        return result.model_dump()
    finally:
        session.close()


@router.get("/skills/{skill_id}/write-rollback-plan", response_model=WriteRollbackPlanResponse)
def get_write_rollback_plan(skill_id: str):
    init_db()
    session = SessionLocal()
    try:
        result = WriteRollbackPlanService(session).get_latest(skill_id)
        if result is None:
            return _not_found("rollback_plan_not_found", f"No rollback plan found for skill '{skill_id}'.")
        return result.model_dump()
    finally:
        session.close()


@router.post("/skills/{skill_id}/write-readiness-certification", response_model=WriteReadinessCertificationResponse)
def certify_write_readiness(skill_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            result = WriteReadinessCertificationService(session).certify(skill_id)
        except ObjectNotFoundError as exc:
            return _not_found("prerequisite_not_found", str(exc))
        return result.model_dump()
    finally:
        session.close()


@router.get("/skills/{skill_id}/write-readiness-summary", response_model=WriteReadinessSummaryResponse)
def get_write_readiness_summary(skill_id: str):
    init_db()
    session = SessionLocal()
    try:
        result = WriteReadinessCertificationService(session).summary(skill_id)
        return result.model_dump()
    finally:
        session.close()


def _not_found(code: str, message: str):
    return JSONResponse(status_code=404, content={"error": {"code": code, "message": message}})


def _assessment_to_dict(model) -> dict:
    d = model.model_dump()
    d["write_candidates"] = [c if isinstance(c, dict) else c.model_dump() for c in (model.write_candidates or [])]
    d["risk_matrix"] = [e if isinstance(e, dict) else e.model_dump() for e in (model.risk_matrix or [])]
    d["permission_preview"] = model.permission_preview.model_dump() if model.permission_preview else None
    return d
