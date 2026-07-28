from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.schemas.skill_compilation import (
    CompiledSkillResponse,
    DraftReviewResponse,
    DraftValidationResultResponse,
    DryRunProofResponse,
)
from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import (
    get_latest_skill_version,
    get_skill,
    list_draft_reviews,
)
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.draft_review import DraftReviewService
from erpguard.product.draft_validator import DraftValidatorService
from erpguard.product.dry_run_proof import DryRunProofService
from erpguard.product.skill_package_builder import SkillPackageBuilder

router = APIRouter(prefix="/v1/product", tags=["skill-compilation"])


@router.get("/automation-drafts/{draft_id}/review", response_model=DraftReviewResponse)
def get_draft_review(draft_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            review = DraftReviewService(session).get_or_create(draft_id)
        except ObjectNotFoundError as exc:
            return _not_found("draft_not_found", str(exc))
        return review.model_dump()
    finally:
        session.close()


@router.post("/automation-drafts/{draft_id}/validate", response_model=DraftValidationResultResponse)
def validate_draft(draft_id: str):
    init_db()
    session = SessionLocal()
    try:
        result = DraftValidatorService(session).validate(draft_id)
        return result.to_dict()
    finally:
        session.close()


@router.post("/automation-drafts/{draft_id}/compile-skill", response_model=CompiledSkillResponse)
def compile_draft_to_skill(draft_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            review = DraftReviewService(session).get_or_create(draft_id)
        except ObjectNotFoundError as exc:
            return _not_found("draft_not_found", str(exc))

        validation = DraftValidatorService(session).validate(draft_id)
        if not validation.passed:
            return JSONResponse(
                status_code=422,
                content={
                    "error": {
                        "code": "draft_validation_failed",
                        "message": "Draft did not pass safety validation.",
                        "details": {"issues": [i.__dict__ for i in validation.issues]},
                    }
                },
            )

        try:
            compiled = SkillPackageBuilder(session).build(review.review_id)
        except (ObjectNotFoundError, ValueError) as exc:
            return _controlled_error("skill_compilation_error", str(exc), status_code=503)

        return compiled.model_dump()
    finally:
        session.close()


@router.get("/automation-drafts/{draft_id}/compiled-skill", response_model=CompiledSkillResponse)
def get_compiled_skill_for_draft(draft_id: str):
    init_db()
    session = SessionLocal()
    try:
        reviews = list_draft_reviews(session, draft_id)
        compiled_review = next((r for r in reviews if r.status == "compiled" and r.skill_id), None)
        if compiled_review is None:
            return _not_found("compiled_skill_not_found", f"No compiled skill found for draft '{draft_id}'.")
        assert compiled_review.skill_id is not None  # filtered by `r.skill_id` truthy above

        skill_row = get_skill(session, compiled_review.skill_id)
        if skill_row is None:
            return _not_found("skill_not_found", f"Skill '{compiled_review.skill_id}' not found.")

        version_row = get_latest_skill_version(session, compiled_review.skill_id)
        if version_row is None:
            return _not_found("skill_version_not_found", f"No version found for skill '{compiled_review.skill_id}'.")

        package = json.loads(version_row.skill_package_json)
        return {
            "skill_id": skill_row.id,
            "version_id": version_row.id,
            "draft_id": draft_id,
            "review_id": compiled_review.id,
            "opportunity_id": package.get("opportunity_id", ""),
            "connection_id": package.get("connection_id", ""),
            "name": skill_row.name,
            "description": skill_row.description,
            "runtime_mode": package.get("runtime_mode", "dry_run_only"),
            "write_actions": package.get("write_actions", False),
            "requires_approval_before_activation": package.get("requires_approval_before_activation", True),
            "guards": package.get("guards", []),
            "input_schema": package.get("input_schema", []),
            "output_schema": package.get("output_schema", []),
            "test_cases": package.get("test_cases", []),
            "created_at": version_row.created_at.isoformat(),
        }
    finally:
        session.close()


@router.post("/skills/{skill_id}/dry-run-proof", response_model=DryRunProofResponse)
def run_dry_run_proof(skill_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            proof = DryRunProofService(session).run(skill_id)
        except ObjectNotFoundError as exc:
            return _not_found("skill_not_found", str(exc))
        except ValueError as exc:
            return _controlled_error("dry_run_proof_refused", str(exc), status_code=422)
        return proof.model_dump()
    finally:
        session.close()


def _not_found(code: str, message: str):
    return JSONResponse(status_code=404, content={"error": {"code": code, "message": message}})


def _controlled_error(code: str, message: str, status_code: int = 400):
    return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message}})
