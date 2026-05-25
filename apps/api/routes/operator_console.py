from __future__ import annotations

from fastapi import APIRouter

from apps.api.schemas.operator_console import (
    ConsoleHistoryResponse,
    ConsoleQueryRequest,
    ConsoleQueryResponse,
    ConsoleSessionRequest,
    ConsoleSessionResponse,
    HistoryEntrySchema,
    IntentsResponse,
    SupportedIntentSchema,
)
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.operator_console import run_console_query
from erpguard.product.operator_console_intent_classifier import list_supported_intents
from erpguard.product.operator_console_session import get_session_history, start_console_session

router = APIRouter(
    prefix="/v1/operator/console",
    tags=["operator-console"],
)


@router.get("/intents", response_model=IntentsResponse)
def get_intents():
    intents = list_supported_intents()
    return IntentsResponse(
        intents=[SupportedIntentSchema(**i) for i in intents],
        total=len(intents),
    )


@router.post("/sessions", response_model=ConsoleSessionResponse)
def create_session(body: ConsoleSessionRequest):
    init_db()
    db = SessionLocal()
    try:
        r = start_console_session(body.actor, db)
        return ConsoleSessionResponse(
            session_id=r.session_id,
            actor=r.actor,
            query_count=r.query_count,
            created_at=r.created_at,
        )
    finally:
        db.close()


@router.post("/query", response_model=ConsoleQueryResponse)
def console_query(body: ConsoleQueryRequest):
    init_db()
    db = SessionLocal()
    try:
        r = run_console_query(
            body.query,
            body.session_id,
            db,
            version_id=body.version_id,
        )
        return ConsoleQueryResponse(
            query=r.query,
            session_id=r.session_id,
            query_id=r.query_id,
            detected_intent=r.detected_intent,
            intent_confidence=r.intent_confidence,
            matched_keywords=r.matched_keywords,
            response_message=r.response_message,
            result_type=r.result_type,
            results=r.results,
            version_id_context=r.version_id_context,
            follow_up_suggestions=r.follow_up_suggestions,
        )
    finally:
        db.close()


@router.get("/sessions/{session_id}/history", response_model=ConsoleHistoryResponse)
def session_history(session_id: str):
    init_db()
    db = SessionLocal()
    try:
        r = get_session_history(session_id, db)
        return ConsoleHistoryResponse(
            session_id=r.session_id,
            entries=[
                HistoryEntrySchema(
                    query_id=e.query_id,
                    query_text=e.query_text,
                    detected_intent=e.detected_intent,
                    intent_confidence=e.intent_confidence,
                    response_summary=e.response_summary,
                    result_type=e.result_type,
                    created_at=e.created_at,
                )
                for e in r.entries
            ],
            entry_count=r.entry_count,
        )
    finally:
        db.close()
