from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.schemas.demo import DemoFullFlowRequest, DemoFullFlowResponse
from erpguard.demo.full_flow import execute_full_record_to_skill_flow
from erpguard.recorder.browser_recorder import BrowserRuntimeUnavailableError


router = APIRouter(prefix="/v1", tags=["demo"])


@router.post("/demo/full-record-to-skill-flow", response_model=DemoFullFlowResponse, response_model_exclude_none=True)
def full_record_to_skill_flow_endpoint(request: DemoFullFlowRequest):
    try:
        result = execute_full_record_to_skill_flow(
            base_url=request.base_url,
            record_order_reference=request.record_order_reference,
            valid_order_reference=request.valid_order_reference,
            invalid_order_reference=request.invalid_order_reference,
            actor=request.actor.model_dump(),
        )
    except BrowserRuntimeUnavailableError:
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "browser_runtime_unavailable",
                    "message": "Playwright browser binaries are unavailable.",
                }
            },
        )

    return {
        "status": "success",
        "recording": result.recording,
        "skill": result.skill,
        "runs": {
            "valid": {
                "skill_run_id": result.runs["valid"].skill_run_id,
                "order_reference": result.runs["valid"].order_reference,
                "decision": result.runs["valid"].decision,
            },
            "invalid": {
                "skill_run_id": result.runs["invalid"].skill_run_id,
                "order_reference": result.runs["invalid"].order_reference,
                "decision": result.runs["invalid"].decision,
                "issues_count": result.runs["invalid"].issues_count,
            },
        },
        "token_economics": result.token_economics,
        "proof": result.proof,
    }
