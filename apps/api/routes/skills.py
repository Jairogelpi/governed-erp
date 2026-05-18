from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.schemas.skills import (
    SkillCreateRequest,
    SkillCreateResponse,
    SkillDetailResponse,
    SkillRunDetailResponse,
    SkillRunRequest,
    SkillRunResponse,
    SkillRunStepResponse,
    SkillUIRunRequest,
    SkillUIRunResponse,
    SkillSummaryResponse,
)
from erpguard.adapters.fake import FakeERPAdapter
from erpguard.canonical.enums import CanonicalAction
from erpguard.core.errors import ObjectNotFoundError
from erpguard.demo.full_flow import run_deterministic_skill_for_order_reference
from erpguard.db.repositories import (
    create_skill,
    create_skill_run,
    create_skill_run_step,
    create_skill_version,
    finish_skill_run,
    get_latest_skill_version,
    get_skill,
    get_skill_run,
    list_skills,
    list_skill_run_steps,
)
from erpguard.db.session import SessionLocal, init_db
from erpguard.policies.engine import PolicyEngine
from erpguard.runtime.browser_runtime import BrowserRuntimeUnavailableError, is_playwright_browser_available, run_fake_erp_formula_skill_ui


router = APIRouter(prefix="/v1", tags=["skills"])
_TOKEN_ECONOMICS = {
    "creation_token_cost_estimate": 2000,
    "repeated_execution_token_cost": 0,
    "estimated_tokens_saved": 2000,
}


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


@router.get("/skills/{skill_id}/inspect")
def inspect_skill_endpoint(skill_id: str):
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
        if latest_version is None:
            return JSONResponse(
                status_code=404,
                content={
                    "error": {
                        "code": "skill_version_not_found",
                        "message": f"Skill '{skill_id}' has no registered version.",
                        "details": {"skill_id": skill_id},
                    }
                },
            )

        skill_package = json.loads(latest_version.skill_package_json)
        guards = skill_package.get("guards", [])
        workflow_steps = skill_package.get("workflow", [])
        return {
            "skill_id": skill.id,
            "name": skill.name,
            "version_id": latest_version.id,
            "runtime_type": latest_version.runtime_type,
            "llm_required_for_repeated_runs": latest_version.llm_required_for_repeated_runs,
            "inputs": skill_package.get("inputs", {}),
            "guards": guards,
            "workflow_steps": workflow_steps,
            "compiled_from_recording_id": skill_package.get("compiled_from_recording_id"),
            "safety_summary": {
                "has_guards": bool(guards),
                "guard_count": len(guards),
                "has_write_actions": _has_write_actions(workflow_steps),
                "requires_llm_for_replay": bool(latest_version.llm_required_for_repeated_runs),
            },
        }
    finally:
        session.close()


@router.post("/skills/{skill_id}/run", response_model=SkillRunResponse)
def run_skill_endpoint(skill_id: str, request: SkillRunRequest):
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

        skill_version = get_latest_skill_version(session, skill.id)
        if skill_version is None:
            return JSONResponse(
                status_code=404,
                content={
                    "error": {
                        "code": "skill_version_not_found",
                        "message": f"Skill '{skill_id}' has no registered version.",
                        "details": {"skill_id": skill_id},
                    }
                },
            )

        inputs = request.inputs.model_dump(mode="json")
        order_reference = inputs["order_reference"]

        run_result = run_deterministic_skill_for_order_reference(session=session, skill_id=skill.id, order_reference=order_reference)
        run = get_skill_run(session, run_result.skill_run_id)
        output = run.output_json and json.loads(run.output_json) or {}
        return _run_response(run, skill.id, output)
    finally:
        session.close()


@router.get("/skills/{skill_id}/runs/{skill_run_id}", response_model=SkillRunDetailResponse)
def get_skill_run_endpoint(skill_id: str, skill_run_id: str):
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
        run = get_skill_run(session, skill_run_id)
        if run is None or run.skill_id != skill_id:
            return JSONResponse(
                status_code=404,
                content={
                    "error": {
                        "code": "skill_run_not_found",
                        "message": f"Skill run '{skill_run_id}' not found for skill '{skill_id}'.",
                        "details": {"skill_id": skill_id, "skill_run_id": skill_run_id},
                    }
                },
            )

        steps = list_skill_run_steps(session, skill_run_id)
        output = json.loads(run.output_json) if run.output_json else {}
        return {
            "skill_run_id": run.id,
            "skill_id": run.skill_id,
            "skill_version_id": run.skill_version_id,
            "status": run.status,
            "decision": run.decision or output.get("policy_id", ""),
            "output": output,
            "token_economics": _TOKEN_ECONOMICS,
            "input": json.loads(run.input_json) if run.input_json else None,
            "error_text": run.error_text,
            "created_at": run.created_at.isoformat(),
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "steps": [
                {
                    "id": step.id,
                    "step_id": step.step_id,
                    "step_type": step.step_type,
                    "status": step.status,
                    "input_json": json.loads(step.input_json) if step.input_json else None,
                    "output_json": json.loads(step.output_json) if step.output_json else None,
                    "error_text": step.error_text,
                    "created_at": step.created_at.isoformat(),
                }
                for step in steps
            ],
        }
    finally:
        session.close()


@router.post("/skills/{skill_id}/run-ui", response_model=SkillUIRunResponse)
def run_skill_ui_endpoint(skill_id: str, request: SkillUIRunRequest):
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

        skill_version = get_latest_skill_version(session, skill.id)
        if skill_version is None:
            return JSONResponse(
                status_code=404,
                content={
                    "error": {
                        "code": "skill_version_not_found",
                        "message": f"Skill '{skill_id}' has no registered version.",
                        "details": {"skill_id": skill_id},
                    }
                },
            )

        if not is_playwright_browser_available():
            return JSONResponse(
                status_code=503,
                content={
                    "error": {
                        "code": "browser_runtime_unavailable",
                        "message": "Playwright browser binaries are unavailable.",
                        "details": {"skill_id": skill_id},
                    }
                },
            )

        inputs = request.inputs.model_dump(mode="json")
        order_reference = inputs["order_reference"]

        run = create_skill_run(
            session=session,
            skill_id=skill.id,
            skill_version_id=skill_version.id,
            status="running",
            input_json=json.dumps({"inputs": inputs, "runtime": request.runtime.model_dump(mode="json")}, default=str),
        )

        try:
            browser_result = run_fake_erp_formula_skill_ui(request.runtime.base_url, order_reference)
        except BrowserRuntimeUnavailableError as exc:
            finished = finish_skill_run(
                session=session,
                skill_run_id=run.id,
                status="failed",
                decision="block",
                error_text=str(exc),
                output_json=json.dumps(
                    {
                        "order_reference": order_reference,
                        "policy_id": "formula_guard",
                        "policy_version": "0.1.0",
                        "issues": [],
                    },
                    default=str,
                ),
                estimated_tokens_saved=2000,
            )
            create_skill_run_step(
                session=session,
                skill_run_id=run.id,
                step_id="browser_runtime",
                step_type="runtime",
                status="failed",
                error_text=str(exc),
            )
            return _ui_run_response(finished, skill.id, {"order_reference": order_reference, "policy_id": "formula_guard", "policy_version": "0.1.0", "issues": []}, [], [], [])

        for step in browser_result.steps:
            create_skill_run_step(
                session=session,
                skill_run_id=run.id,
                step_id=step.step_id,
                step_type=step.step_type,
                status=step.status,
                input_json=json.dumps(step.input_json, default=str) if step.input_json is not None else None,
                output_json=json.dumps(step.output_json, default=str) if step.output_json is not None else None,
                error_text=step.error_text,
            )

        finished = finish_skill_run(
            session=session,
            skill_run_id=run.id,
            status=browser_result.status,
            output_json=json.dumps(browser_result.output, default=str),
            decision=browser_result.decision,
            error_text=browser_result.error_text,
            estimated_tokens_saved=browser_result.token_economics["estimated_tokens_saved"],
        )
        return _ui_run_response(
            finished,
            skill.id,
            browser_result.output,
            browser_result.visited_urls,
            browser_result.selectors_used,
            browser_result.steps,
            no_llm_used=browser_result.no_llm_used,
        )
    finally:
        session.close()


def _run_response(run, skill_id: str, output: dict) -> dict:
    return {
        "skill_run_id": run.id,
        "skill_id": skill_id,
        "status": run.status,
        "decision": run.decision,
        "output": output,
        "token_economics": _TOKEN_ECONOMICS,
    }


def _has_write_actions(workflow_steps: list[dict]) -> bool:
    write_action_types = {"write", "create", "update", "delete", "execute", "post", "confirm", "approve"}
    return any(str(step.get("type", "")).casefold() in write_action_types for step in workflow_steps)


def _ui_run_response(run, skill_id: str, output: dict, visited_urls: list[str], selectors_used: list[str], steps, no_llm_used: bool = True) -> dict:
    return {
        "skill_run_id": run.id,
        "skill_id": skill_id,
        "status": run.status,
        "decision": run.decision,
        "output": output,
        "token_economics": _TOKEN_ECONOMICS,
        "visited_urls": visited_urls,
        "selectors_used": selectors_used,
        "steps": [
            {
                "id": f"step_{index + 1}",
                "step_id": step.step_id,
                "step_type": step.step_type,
                "status": step.status,
                "url": step.url,
                "selector": step.selector,
                "input_json": step.input_json,
                "output_json": step.output_json,
                "error_text": step.error_text,
                "created_at": None,
            }
            for index, step in enumerate(steps)
        ],
        "no_llm_used": no_llm_used,
    }
