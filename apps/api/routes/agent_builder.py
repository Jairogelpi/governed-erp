from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.schemas.agent_builder import (
    AgentBuilderPreviewResponse,
    AgentBuilderSaveDraftResponse,
    AgentBuilderSessionResponse,
    AgentBuilderStepLibraryResponse,
    AgentBuilderTimelineResponse,
    AgentBuilderValidationResponse,
    ConfigureGuardsRequest,
    ConfigureInputsRequest,
    ConfigureStepsRequest,
    ConfigureTriggerRequest,
    CreateAgentBuilderSessionRequest,
    SelectConnectorRequest,
    SelectTemplateRequest,
)
from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.agent_builder_draft_exporter import AgentBuilderDraftExporter
from erpguard.product.agent_builder_preview import AgentBuilderPreviewService
from erpguard.product.agent_builder_session import AgentBuilderSessionService
from erpguard.product.agent_builder_state import MANDATORY_GUARDS, AgentBuilderSafety
from erpguard.product.agent_builder_step_library import AgentBuilderStepLibrary


router = APIRouter(prefix="/v1/agent-builder", tags=["agent-builder"])


@router.post("/sessions", response_model=AgentBuilderSessionResponse)
def create_builder_session(request: CreateAgentBuilderSessionRequest):
    init_db()
    session = SessionLocal()
    try:
        return AgentBuilderSessionService(session).create(request.created_by).model_dump()
    finally:
        session.close()


@router.get("/sessions/{session_id}", response_model=AgentBuilderSessionResponse)
def get_builder_session(session_id: str):
    return _with_builder_session(lambda service: service.get(session_id))


@router.post("/sessions/{session_id}/select-template", response_model=AgentBuilderSessionResponse)
def select_template(session_id: str, request: SelectTemplateRequest):
    return _with_builder_session(lambda service: service.select_template(session_id, request.template_id))


@router.post("/sessions/{session_id}/select-connector", response_model=AgentBuilderSessionResponse)
def select_connector(session_id: str, request: SelectConnectorRequest):
    return _with_builder_session(lambda service: service.select_connector(session_id, request.connector_id))


@router.post("/sessions/{session_id}/configure-trigger", response_model=AgentBuilderSessionResponse)
def configure_trigger(session_id: str, request: ConfigureTriggerRequest):
    return _with_builder_session(lambda service: service.configure_trigger(session_id, request.trigger))


@router.post("/sessions/{session_id}/configure-inputs", response_model=AgentBuilderSessionResponse)
def configure_inputs(session_id: str, request: ConfigureInputsRequest):
    return _with_builder_session(lambda service: service.configure_inputs(session_id, request.inputs))


@router.post("/sessions/{session_id}/configure-steps", response_model=AgentBuilderSessionResponse)
def configure_steps(session_id: str, request: ConfigureStepsRequest):
    library = AgentBuilderStepLibrary()
    for item in request.steps:
        step_type = str(item.get("type", "")) if isinstance(item, dict) else str(item)
        if step_type in library.forbidden_step_types() or not library.is_allowed(step_type):
            return JSONResponse(
                status_code=422,
                content={"error": {"code": "forbidden_builder_step", "message": f"Step type '{step_type}' is not allowed."}},
            )
    return _with_builder_session(lambda service: service.configure_steps(session_id, request.steps))


@router.post("/sessions/{session_id}/configure-guards", response_model=AgentBuilderSessionResponse)
def configure_guards(session_id: str, request: ConfigureGuardsRequest):
    return _with_builder_session(lambda service: service.configure_guards(session_id, request.guards))


@router.post("/sessions/{session_id}/check-requirements", response_model=AgentBuilderValidationResponse)
def check_requirements(session_id: str):
    return _with_builder_session(lambda service: service.check_requirements(session_id))


@router.get("/sessions/{session_id}/preview", response_model=AgentBuilderPreviewResponse)
def preview_builder_session(session_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            return AgentBuilderPreviewService(session).preview(session_id).model_dump()
        except ObjectNotFoundError as exc:
            return _not_found(str(exc))
    finally:
        session.close()


@router.post("/sessions/{session_id}/save-draft", response_model=AgentBuilderSaveDraftResponse)
def save_builder_draft(session_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            return AgentBuilderDraftExporter(session).save_draft(session_id).model_dump()
        except ObjectNotFoundError as exc:
            return _not_found(str(exc))
        except ValueError as exc:
            return JSONResponse(status_code=422, content={"error": {"code": str(exc), "message": "Builder session cannot be saved as draft."}})
    finally:
        session.close()


@router.get("/sessions/{session_id}/timeline", response_model=AgentBuilderTimelineResponse)
def builder_timeline(session_id: str):
    return _with_builder_session(lambda service: {"session_id": session_id, "events": [event.model_dump() for event in service.timeline(session_id)]})


@router.get("/step-library", response_model=AgentBuilderStepLibraryResponse)
def step_library():
    library = AgentBuilderStepLibrary()
    return {
        "allowed_steps": [step.model_dump() for step in library.allowed_steps()],
        "forbidden_step_types": library.forbidden_step_types(),
        "mandatory_guards": MANDATORY_GUARDS,
        "safety": AgentBuilderSafety().model_dump(),
    }


def _with_builder_session(callback):
    init_db()
    session = SessionLocal()
    try:
        service = AgentBuilderSessionService(session)
        try:
            result = callback(service)
        except ObjectNotFoundError as exc:
            return _not_found(str(exc))
        return result.model_dump() if hasattr(result, "model_dump") else result
    finally:
        session.close()


def _not_found(message: str):
    return JSONResponse(status_code=404, content={"error": {"code": "builder_session_not_found", "message": message}})
