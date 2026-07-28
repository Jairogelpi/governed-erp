from __future__ import annotations

import json

from pydantic import BaseModel
from sqlalchemy.orm import Session

from erpguard.db.repositories import (
    get_agent_proposal_draft_link_by_draft,
    get_automation_draft,
    create_agent_draft_bridge_event,
)
from erpguard.product.draft_review import DraftReviewService


class DraftReviewBridgeResult(BaseModel):
    draft_id: str
    proposal_id: str | None = None
    review_id: str | None = None
    bridged: bool
    review_status: str | None = None
    guards_count: int = 0
    test_cases_count: int = 0
    can_execute: bool = False
    is_advisory_only: bool = True
    blocking_reason: str | None = None


def bridge_to_review(draft_id: str, session: Session) -> DraftReviewBridgeResult:
    draft = get_automation_draft(session, draft_id)
    if draft is None:
        return DraftReviewBridgeResult(
            draft_id=draft_id,
            bridged=False,
            blocking_reason="draft_not_found",
        )

    link = get_agent_proposal_draft_link_by_draft(session, draft_id)
    proposal_id = link.proposal_id if link else None

    if link is None:
        create_agent_draft_bridge_event(
            session, draft_id, draft_id, "review", "blocked",
            json.dumps({"reason": "no_proposal_link"}),
        )
        return DraftReviewBridgeResult(
            draft_id=draft_id,
            proposal_id=None,
            bridged=False,
            blocking_reason="no_proposal_link",
        )

    try:
        service = DraftReviewService(session)
        review = service.get_or_create(draft_id)
    except Exception as exc:
        detail = str(exc)[:200]
        create_agent_draft_bridge_event(
            session, draft_id, proposal_id or draft_id, "review", "failed",
            json.dumps({"error": detail}),
        )
        return DraftReviewBridgeResult(
            draft_id=draft_id,
            proposal_id=proposal_id,
            bridged=False,
            blocking_reason=detail,
        )

    guards_count = len(review.guards) if review.guards else 0
    test_cases_count = len(review.test_cases) if review.test_cases else 0

    create_agent_draft_bridge_event(
        session, draft_id, proposal_id or draft_id, "review", "passed",
        json.dumps({
            "review_id": review.review_id,
            "guards_count": guards_count,
            "test_cases_count": test_cases_count,
        }),
    )

    return DraftReviewBridgeResult(
        draft_id=draft_id,
        proposal_id=proposal_id,
        review_id=review.review_id,
        bridged=True,
        review_status=review.status,
        guards_count=guards_count,
        test_cases_count=test_cases_count,
        can_execute=False,
        is_advisory_only=True,
    )
