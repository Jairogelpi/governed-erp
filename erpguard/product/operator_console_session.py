from __future__ import annotations

from dataclasses import dataclass, field

from erpguard.db.repositories import (
    create_operator_console_session,
    get_operator_console_session,
    list_operator_console_queries,
)


@dataclass(frozen=True)
class ConsoleSessionResult:
    session_id: str
    actor: str
    query_count: int
    created_at: object
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


@dataclass(frozen=True)
class ConsoleHistoryEntry:
    query_id: str
    query_text: str
    detected_intent: str
    intent_confidence: float
    response_summary: str
    result_type: str
    created_at: object


@dataclass(frozen=True)
class ConsoleHistoryResult:
    session_id: str
    entries: list[ConsoleHistoryEntry] = field(default_factory=list)
    entry_count: int = 0
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


def start_console_session(actor: str, session) -> ConsoleSessionResult:
    row = create_operator_console_session(session, actor=actor)
    return ConsoleSessionResult(
        session_id=row.id,
        actor=row.actor,
        query_count=0,
        created_at=row.created_at,
    )


def get_session_history(session_id: str, session) -> ConsoleHistoryResult:
    queries = list_operator_console_queries(session, session_id)
    entries = [
        ConsoleHistoryEntry(
            query_id=q.id,
            query_text=q.query_text,
            detected_intent=q.detected_intent,
            intent_confidence=q.intent_confidence,
            response_summary=q.response_summary,
            result_type=q.result_type,
            created_at=q.created_at,
        )
        for q in queries
    ]
    return ConsoleHistoryResult(
        session_id=session_id,
        entries=entries,
        entry_count=len(entries),
    )
