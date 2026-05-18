from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.schemas.skills import SkillCreateRequest, SkillCreateResponse, SkillDetailResponse, SkillSummaryResponse
from erpguard.db.repositories import (
    create_skill,
    create_skill_version,
    get_latest_skill_version,
    get_skill,
    list_skills,
)
from erpguard.db.session import SessionLocal, init_db


router = APIRouter(prefix="/v1", tags=["skills"])


@router.post("/skills", response_model=SkillCreateResponse)
def create_skill_endpoint(request: SkillCreateRequest):
    init_db()
    session = SessionLocal()
    try:
        skill = create_skill(session, request.name, request.description)
        version = create_skill_version(
            session=session,
            skill_id=skill.id,
            version="1.0.0",
            skill_package_json=json.dumps(request.skill_package, default=str),
            runtime_type=request.runtime_type,
            llm_required_for_repeated_runs=request.llm_required_for_repeated_runs,
        )
        return {
            "skill_id": skill.id,
            "version_id": version.id,
            "name": skill.name,
            "status": skill.status,
            "runtime_type": version.runtime_type,
            "llm_required_for_repeated_runs": version.llm_required_for_repeated_runs,
        }
    finally:
        session.close()


@router.get("/skills", response_model=list[SkillSummaryResponse])
def list_skills_endpoint():
    init_db()
    session = SessionLocal()
    try:
        skills = list_skills(session)
        response = []
        for skill in skills:
            latest_version = get_latest_skill_version(session, skill.id)
            response.append(
                {
                    "skill_id": skill.id,
                    "name": skill.name,
                    "description": skill.description,
                    "status": skill.status,
                    "created_at": skill.created_at.isoformat(),
                    "updated_at": skill.updated_at.isoformat(),
                    "latest_version_id": latest_version.id if latest_version else None,
                    "runtime_type": latest_version.runtime_type if latest_version else None,
                    "llm_required_for_repeated_runs": (
                        latest_version.llm_required_for_repeated_runs if latest_version else None
                    ),
                }
            )
        return response
    finally:
        session.close()


@router.get("/skills/{skill_id}", response_model=SkillDetailResponse)
def get_skill_endpoint(skill_id: str):
    init_db()
    session = SessionLocal()
    try:
        skill = get_skill(session, skill_id)
        if skill is None:
            return JSONResponse(
                status_code=404,
                content={
                    "error": {
                        "code": "skill_not_found",
                        "message": f"Skill '{skill_id}' not found.",
                        "details": {"skill_id": skill_id},
                    }
                },
            )
        latest_version = get_latest_skill_version(session, skill.id)
        return {
            "skill_id": skill.id,
            "name": skill.name,
            "description": skill.description,
            "status": skill.status,
            "created_at": skill.created_at.isoformat(),
            "updated_at": skill.updated_at.isoformat(),
            "latest_version_id": latest_version.id if latest_version else None,
            "runtime_type": latest_version.runtime_type if latest_version else None,
            "llm_required_for_repeated_runs": latest_version.llm_required_for_repeated_runs if latest_version else None,
            "skill_package": json.loads(latest_version.skill_package_json) if latest_version else {},
            "version": latest_version.version if latest_version else None,
            "version_created_at": latest_version.created_at.isoformat() if latest_version else None,
        }
    finally:
        session.close()