from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ConsoleSessionRequest(BaseModel):
    actor: str = "operator"


class ConsoleSessionResponse(BaseModel):
    session_id: str
    actor: str
    query_count: int
    created_at: Any
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


class ConsoleQueryRequest(BaseModel):
    query: str
    session_id: str
    version_id: str | None = None


class ConsoleQueryResponse(BaseModel):
    query: str
    session_id: str
    query_id: str
    detected_intent: str
    intent_confidence: float
    matched_keywords: list[str]
    response_message: str
    result_type: str
    results: Any
    version_id_context: str | None
    follow_up_suggestions: list[str]
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


class SupportedIntentSchema(BaseModel):
    intent: str
    description: str


class IntentsResponse(BaseModel):
    intents: list[SupportedIntentSchema]
    total: int
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


class HistoryEntrySchema(BaseModel):
    query_id: str
    query_text: str
    detected_intent: str
    intent_confidence: float
    response_summary: str
    result_type: str
    created_at: Any


class ConsoleHistoryResponse(BaseModel):
    session_id: str
    entries: list[HistoryEntrySchema]
    entry_count: int
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True
