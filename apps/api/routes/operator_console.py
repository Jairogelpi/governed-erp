from __future__ import annotations

from fastapi import APIRouter, Query

from apps.api.schemas.operator_console import (
    AskRequest,
    ConsoleHistoryResponse,
    ConsoleQueryRequest,
    ConsoleQueryResponse,
    ConsoleSessionRequest,
    ConsoleSessionResponse,
    GlobalAuditEntry,
    GlobalAuditResponse,
    HistoryEntrySchema,
    IntentsResponse,
    SupportedIntentSchema,
)
from erpguard.db.repositories import list_recent_operator_console_queries
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


# Sprint 41B - spec-compatible alias router
alias_router = APIRouter(
    prefix="/v1/operator-console",
    tags=["operator-console-alias"],
)


@alias_router.post("/ask", response_model=ConsoleQueryResponse)
def alias_ask(body: AskRequest):
    init_db()
    db = SessionLocal()
    try:
        if body.session_id:
            session_id = body.session_id
        else:
            r = start_console_session(body.actor, db)
            session_id = r.session_id
        result = run_console_query(
            body.question,
            session_id,
            db,
            version_id=body.version_id,
        )
        return ConsoleQueryResponse(
            query=result.query,
            session_id=result.session_id,
            query_id=result.query_id,
            detected_intent=result.detected_intent,
            intent_confidence=result.intent_confidence,
            matched_keywords=result.matched_keywords,
            response_message=result.response_message,
            result_type=result.result_type,
            results=result.results,
            version_id_context=result.version_id_context,
            follow_up_suggestions=result.follow_up_suggestions,
        )
    finally:
        db.close()


@alias_router.get("/audit")
def alias_audit(
    session_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    init_db()
    db = SessionLocal()
    try:
        if session_id:
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
        rows = list_recent_operator_console_queries(db, limit=limit)
        return GlobalAuditResponse(
            entries=[
                GlobalAuditEntry(
                    query_id=q.id,
                    session_id=q.session_id,
                    query_text=q.query_text,
                    detected_intent=q.detected_intent,
                    intent_confidence=q.intent_confidence,
                    response_summary=q.response_summary,
                    result_type=q.result_type,
                    version_id_context=q.version_id_context,
                    created_at=q.created_at,
                )
                for q in rows
            ],
            entry_count=len(rows),
            session_id=None,
        )
    finally:
        db.close()
