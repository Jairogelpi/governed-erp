from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.schemas.recordings import (
    RecordingCreateRequest,
    RecordingCreateResponse,
    RecordingCompileSkillRequest,
    RecordingCompileSkillResponse,
    RecordingDetailResponse,
    RecordingEventRequest,
    RecordingEventResponse,
    RecordingFinishResponse,
    RecordingSummaryResponse,
)
from erpguard.compiler.recording_to_skill import compile_recording_to_skill_package
from erpguard.db.repositories import (
    add_recording_event,
    create_recording_session,
    create_skill,
    create_skill_version,
    finish_recording_session,
    get_recording_session,
    list_recording_events,
    list_recording_sessions,
)
from erpguard.db.session import SessionLocal, init_db


router = APIRouter(prefix="/v1", tags=["recordings"])


@router.post("/recordings", response_model=RecordingCreateResponse)
def create_recording_endpoint(request: RecordingCreateRequest):
    init_db()
    session = SessionLocal()
    try:
        recording = create_recording_session(
            session=session,
            name=request.name,
            description=request.description,
            erp_type=request.erp_type,
            target_base_url=request.target_base_url,
            created_by_actor_json=request.actor.model_dump_json(),
        )
        return {
            "recording_id": recording.id,
            "name": recording.name,
            "status": recording.status,
            "erp_type": recording.erp_type,
            "target_base_url": recording.target_base_url,
        }
    finally:
        session.close()


@router.get("/recordings", response_model=list[RecordingSummaryResponse])
def list_recordings_endpoint():
    init_db()
    session = SessionLocal()
    try:
        recordings = list_recording_sessions(session)
        response = []
        for recording in recordings:
            events = list_recording_events(session, recording.id)
            response.append(
                {
                    "recording_id": recording.id,
                    "name": recording.name,
                    "description": recording.description,
                    "status": recording.status,
                    "erp_type": recording.erp_type,
                    "target_base_url": recording.target_base_url,
                    "created_by_actor_json": json.loads(recording.created_by_actor_json),
                    "created_at": recording.created_at.isoformat(),
                    "updated_at": recording.updated_at.isoformat(),
                    "event_count": len(events),
                }
            )
        return response
    finally:
        session.close()


@router.get("/recordings/{recording_id}", response_model=RecordingDetailResponse)
def get_recording_endpoint(recording_id: str):
    init_db()
    session = SessionLocal()
    try:
        recording = get_recording_session(session, recording_id)
        if recording is None:
            return JSONResponse(
                status_code=404,
                content={
                    "error": {
                        "code": "recording_not_found",
                        "message": f"Recording '{recording_id}' not found.",
                        "details": {"recording_id": recording_id},
                    }
                },
            )
        events = list_recording_events(session, recording_id)
        return _serialize_recording(recording, events)
    finally:
        session.close()


@router.post("/recordings/{recording_id}/events", response_model=RecordingEventResponse)
def add_recording_event_endpoint(recording_id: str, request: RecordingEventRequest):
    init_db()
    session = SessionLocal()
    try:
        recording = get_recording_session(session, recording_id)
        if recording is None:
            return JSONResponse(
                status_code=404,
                content={
                    "error": {
                        "code": "recording_not_found",
                        "message": f"Recording '{recording_id}' not found.",
                        "details": {"recording_id": recording_id},
                    }
                },
            )
        event = add_recording_event(
            session=session,
            recording_session_id=recording.id,
            event_type=request.event_type,
            url=request.url,
            page_title=request.page_title,
            element_role=request.element_role,
            element_text=request.element_text,
            element_label=request.element_label,
            selector=request.selector,
            input_value=request.input_value,
            before_text_snapshot=request.before_text_snapshot,
            after_text_snapshot=request.after_text_snapshot,
            screenshot_path=request.screenshot_path,
            metadata_json=json.dumps(request.metadata_json, default=str),
        )
        return _serialize_event(recording.id, event)
    finally:
        session.close()


@router.post("/recordings/{recording_id}/finish", response_model=RecordingFinishResponse)
def finish_recording_endpoint(recording_id: str):
    init_db()
    session = SessionLocal()
    try:
        recording = finish_recording_session(session, recording_id)
        if recording is None:
            return JSONResponse(
                status_code=404,
                content={
                    "error": {
                        "code": "recording_not_found",
                        "message": f"Recording '{recording_id}' not found.",
                        "details": {"recording_id": recording_id},
                    }
                },
            )
        return {"recording_id": recording.id, "status": recording.status}
    finally:
        session.close()


@router.post("/recordings/{recording_id}/compile-skill", response_model=RecordingCompileSkillResponse)
def compile_recording_skill_endpoint(recording_id: str, request: RecordingCompileSkillRequest):
    init_db()
    session = SessionLocal()
    try:
        recording = get_recording_session(session, recording_id)
        if recording is None:
            return JSONResponse(
                status_code=404,
                content={
                    "error": {
                        "code": "recording_not_found",
                        "message": f"Recording '{recording_id}' not found.",
                        "details": {"recording_id": recording_id},
                    }
                },
            )
        if recording.status != "finished":
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": "recording_not_finished",
                        "message": f"Recording '{recording_id}' must be finished before compilation.",
                        "details": {"recording_id": recording_id, "status": recording.status},
                    }
                },
            )

        events = list_recording_events(session, recording_id)
        if not events:
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": "recording_has_no_events",
                        "message": f"Recording '{recording_id}' has no events to compile.",
                        "details": {"recording_id": recording_id},
                    }
                },
            )

        try:
            skill_package = compile_recording_to_skill_package(recording, events)
        except ValueError as exc:
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": "unsupported_recording_flow",
                        "message": str(exc),
                        "details": {"recording_id": recording_id},
                    }
                },
            )

        skill = create_skill(session, request.name, request.description)
        version = create_skill_version(
            session=session,
            skill_id=skill.id,
            version="1.0.0",
            skill_package_json=json.dumps(skill_package, default=str),
            runtime_type=request.runtime_type,
            llm_required_for_repeated_runs=bool(skill_package.get("llm_required_for_repeated_runs", False)),
        )
        return {
            "recording_id": recording.id,
            "skill_id": skill.id,
            "version_id": version.id,
            "name": skill.name,
            "runtime_type": version.runtime_type,
            "llm_required_for_repeated_runs": version.llm_required_for_repeated_runs,
            "skill_package": skill_package,
        }
    finally:
        session.close()


def _serialize_recording(recording, events) -> dict:
    return {
        "recording_id": recording.id,
        "name": recording.name,
        "description": recording.description,
        "status": recording.status,
        "erp_type": recording.erp_type,
        "target_base_url": recording.target_base_url,
        "created_by_actor_json": json.loads(recording.created_by_actor_json),
        "created_at": recording.created_at.isoformat(),
        "updated_at": recording.updated_at.isoformat(),
        "event_count": len(events),
        "events": [
            {
                "event_id": event.id,
                "recording_id": event.recording_session_id,
                "event_index": event.event_index,
                "event_type": event.event_type,
                "url": event.url,
                "page_title": event.page_title,
                "element_role": event.element_role,
                "element_text": event.element_text,
                "element_label": event.element_label,
                "selector": event.selector,
                "input_value": event.input_value,
                "before_text_snapshot": event.before_text_snapshot,
                "after_text_snapshot": event.after_text_snapshot,
                "screenshot_path": event.screenshot_path,
                "metadata_json": json.loads(event.metadata_json) if event.metadata_json else {},
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ],
    }


def _serialize_event(recording_id: str, event) -> dict:
    return {
        "event_id": event.id,
        "recording_id": recording_id,
        "event_index": event.event_index,
        "event_type": event.event_type,
        "url": event.url,
        "page_title": event.page_title,
        "element_role": event.element_role,
        "element_text": event.element_text,
        "element_label": event.element_label,
        "selector": event.selector,
        "input_value": event.input_value,
        "before_text_snapshot": event.before_text_snapshot,
        "after_text_snapshot": event.after_text_snapshot,
        "screenshot_path": event.screenshot_path,
        "metadata_json": json.loads(event.metadata_json) if event.metadata_json else {},
        "created_at": event.created_at.isoformat(),
    }