from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from erpguard.db.repositories import create_operator_console_query
from erpguard.product.operator_console_intent_classifier import classify_intent
from erpguard.product.operator_console_query_router import route_intent
from erpguard.product.operator_console_response_formatter import _follow_ups, format_response


@dataclass(frozen=True)
class ConsoleQueryResult:
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
    follow_up_suggestions: list[str] = field(default_factory=list)
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


def run_console_query(
    query: str,
    session_id: str,
    db_session,
    *,
    version_id: str | None = None,
) -> ConsoleQueryResult:
    """Process a natural-language operator query — reads only, never executes."""
    classification = classify_intent(query)
    routed = route_intent(
        classification.intent,
        query,
        db_session,
        version_id=version_id,
    )
    response_message = format_response(classification.intent, routed)
    follow_ups = _follow_ups(classification.intent, routed.version_id_used or version_id)

    record = create_operator_console_query(
        db_session,
        session_id=session_id,
        query_text=query,
        detected_intent=classification.intent,
        intent_confidence=classification.confidence,
        version_id_context=routed.version_id_used or version_id,
        response_summary=response_message[:500],
        result_type=routed.result_type,
    )

    return ConsoleQueryResult(
        query=query,
        session_id=session_id,
        query_id=record.id,
        detected_intent=classification.intent,
        intent_confidence=classification.confidence,
        matched_keywords=classification.matched_keywords,
        response_message=response_message,
        result_type=routed.result_type,
        results=routed.data,
        version_id_context=routed.version_id_used or version_id,
        follow_up_suggestions=follow_ups,
    )
