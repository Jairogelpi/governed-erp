from __future__ import annotations

import json

from pydantic import BaseModel
from sqlalchemy.orm import Session

from erpguard.db.repositories import (
    create_clarification_audit_event,
    get_agent_proposal_draft_link_by_draft,
    get_automation_draft,
    list_clarification_answers_for_proposal,
    list_mapping_confirmations_for_proposal,
)


class DraftMetadataRefreshResult(BaseModel):
    draft_id: str
    proposal_id: str
    refreshed: bool
    answers_applied: int
    confirmations_applied: int
    runtime_mode: str = "dry_run_only"
    write_actions: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True
    blocking_reason: str | None = None


def refresh_draft_metadata(
    draft_id: str,
    session: Session,
) -> DraftMetadataRefreshResult:
    draft = get_automation_draft(session, draft_id)
    if draft is None:
        return DraftMetadataRefreshResult(
            draft_id=draft_id,
            proposal_id="",
            refreshed=False,
            answers_applied=0,
            confirmations_applied=0,
            blocking_reason="draft_not_found",
        )

    link = get_agent_proposal_draft_link_by_draft(session, draft_id)
    if link is None:
        return DraftMetadataRefreshResult(
            draft_id=draft_id,
            proposal_id="",
            refreshed=False,
            answers_applied=0,
            confirmations_applied=0,
            blocking_reason="no_proposal_link",
        )

    proposal_id = link.proposal_id
    answers = list_clarification_answers_for_proposal(session, proposal_id)
    confirmations = list_mapping_confirmations_for_proposal(session, proposal_id)

    answers_summary = [
        {"question_id": a.question_id, "answer": a.answer_text}
        for a in answers
    ]
    confirmations_summary = [
        {"mapping_key": c.mapping_key, "action": c.action, "reason": c.reason}
        for c in confirmations
    ]

    existing_draft_json = json.loads(draft.draft_json or "{}")
    existing_draft_json["clarification_metadata"] = {
        "answers_applied": len(answers),
        "confirmations_applied": len(confirmations),
        "answers": answers_summary,
        "confirmations": confirmations_summary,
        "runtime_mode": "dry_run_only",
        "write_actions": False,
        "can_execute": False,
        "is_advisory_only": True,
        "requires_human_review": True,
    }
    existing_draft_json["runtime_mode"] = "dry_run_only"
    existing_draft_json["write_actions"] = False
    existing_draft_json["can_execute"] = False

    draft.draft_json = json.dumps(existing_draft_json)
    session.commit()
    session.refresh(draft)

    create_clarification_audit_event(
        session,
        proposal_id=proposal_id,
        event_type="draft_metadata_refreshed",
        detail_json=json.dumps({
            "draft_id": draft_id,
            "answers_applied": len(answers),
            "confirmations_applied": len(confirmations),
        }),
    )

    return DraftMetadataRefreshResult(
        draft_id=draft_id,
        proposal_id=proposal_id,
        refreshed=True,
        answers_applied=len(answers),
        confirmations_applied=len(confirmations),
        runtime_mode="dry_run_only",
        write_actions=False,
        can_execute=False,
        is_advisory_only=True,
    )
