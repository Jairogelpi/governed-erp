from __future__ import annotations

import json

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from erpguard.db.repositories import (
    get_advisory_proposal,
    get_agent_proposal_draft_link_by_draft,
    get_automation_draft,
    get_latest_agent_draft_handoff_packet,
    create_agent_draft_handoff_packet,
    create_agent_draft_handoff_event,
    list_agent_draft_bridge_events_for_draft,
    list_agent_draft_handoff_events_for_draft,
)
from erpguard.product.agent_draft_approval_readiness import check_approval_readiness

_APPROVAL_INSTRUCTIONS = (
    "This packet is prepared for human review. "
    "To approve: (1) verify all readiness checklist items, "
    "(2) review the compile plan and proof scenarios, "
    "(3) confirm the draft matches the original intent, "
    "(4) record approval decision in your change-management system. "
    "This system does NOT automatically activate, schedule, or execute anything on approval."
)

_SAFETY_NOTE = (
    "Handoff packet is advisory only. No skill is activated, versioned, scheduled, or executed. "
    "Human approval through an external process is required before any activation."
)


class HandoffSection(BaseModel):
    section_id: str
    title: str
    content: dict


class ApprovalHandoffPacketResult(BaseModel):
    packet_id: str
    draft_id: str
    proposal_id: str | None = None
    status: str = "pending_human_review"
    sections: list[HandoffSection] = Field(default_factory=list)
    readiness_score: int = 0
    ready_for_review: bool = False
    can_approve: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True
    approval_instructions: str = _APPROVAL_INSTRUCTIONS
    safety_note: str = _SAFETY_NOTE
    is_cached: bool = False


def create_approval_handoff_packet(
    draft_id: str, session: Session
) -> ApprovalHandoffPacketResult:
    draft = get_automation_draft(session, draft_id)
    if draft is None:
        return ApprovalHandoffPacketResult(
            packet_id="",
            draft_id=draft_id,
            status="blocked",
            ready_for_review=False,
            approval_instructions="Draft not found — cannot create handoff packet.",
        )

    link = get_agent_proposal_draft_link_by_draft(session, draft_id)
    proposal_id = link.proposal_id if link else None

    existing = get_latest_agent_draft_handoff_packet(session, draft_id)
    if existing is not None:
        try:
            cached = json.loads(existing.packet_json)
            return ApprovalHandoffPacketResult(
                packet_id=existing.id,
                draft_id=draft_id,
                proposal_id=proposal_id,
                status=existing.status,
                sections=[HandoffSection(**s) for s in cached.get("sections", [])],
                readiness_score=cached.get("readiness_score", 0),
                ready_for_review=cached.get("ready_for_review", False),
                is_cached=True,
            )
        except (json.JSONDecodeError, ValueError, KeyError):
            pass

    readiness = check_approval_readiness(draft_id, session)

    try:
        pkg = json.loads(draft.draft_json)
    except (json.JSONDecodeError, ValueError):
        pkg = {}

    proposal = get_advisory_proposal(session, proposal_id) if proposal_id else None

    bridge_events = list_agent_draft_bridge_events_for_draft(session, draft_id)
    handoff_events = list_agent_draft_handoff_events_for_draft(session, draft_id)

    def _bridge_step(step: str) -> dict:
        latest = next((e for e in reversed(bridge_events) if e.step == step), None)
        return {"step": step, "status": latest.status if latest else "not_run"}

    sections: list[HandoffSection] = [
        HandoffSection(
            section_id="sec_proposal",
            title="Original Advisory Proposal",
            content={
                "proposal_id": proposal_id,
                "request_text": proposal.request_text if proposal else "",
                "process_category": proposal.process_category if proposal else "",
                "intent": json.loads(proposal.intent_json) if proposal else {},
            },
        ),
        HandoffSection(
            section_id="sec_draft",
            title="AutomationDraft Details",
            content={
                "draft_id": draft_id,
                "name": draft.name,
                "description": draft.description,
                "status": draft.status,
                "runtime_mode": draft.runtime_mode,
                "write_actions": draft.write_actions,
            },
        ),
        HandoffSection(
            section_id="sec_safety",
            title="Safety Invariants",
            content={
                "runtime_mode": pkg.get("safety", {}).get("runtime_mode", "dry_run_only"),
                "write_actions": pkg.get("safety", {}).get("write_actions", False),
                "can_execute": pkg.get("safety", {}).get("can_execute", False),
                "is_advisory_only": pkg.get("safety", {}).get("is_advisory_only", True),
                "requires_human_review": pkg.get("safety", {}).get("requires_human_review", True),
                "requires_approval": pkg.get("safety", {}).get("requires_approval", True),
            },
        ),
        HandoffSection(
            section_id="sec_bridge",
            title="ERPGuard Bridge Pipeline Results",
            content={
                "review": _bridge_step("review"),
                "validation": _bridge_step("validation"),
                "compile_plan": _bridge_step("compile_plan"),
            },
        ),
        HandoffSection(
            section_id="sec_readiness",
            title="Approval Readiness Checklist",
            content={
                "ready": readiness.ready,
                "overall_score": readiness.overall_score,
                "blocking_items": readiness.blocking_items,
                "advisory_items": readiness.advisory_items,
                "checklist": [c.model_dump() for c in readiness.checklist],
            },
        ),
        HandoffSection(
            section_id="sec_instructions",
            title="Human Reviewer Instructions",
            content={
                "approval_instructions": _APPROVAL_INSTRUCTIONS,
                "safety_note": _SAFETY_NOTE,
                "next_step": "Human reviewer must approve through external change-management process",
            },
        ),
    ]

    packet_data = {
        "sections": [s.model_dump() for s in sections],
        "readiness_score": readiness.overall_score,
        "ready_for_review": readiness.ready,
    }
    packet_row = create_agent_draft_handoff_packet(
        session, draft_id, proposal_id or draft_id, json.dumps(packet_data, default=str)
    )

    create_agent_draft_handoff_event(
        session, draft_id, proposal_id or draft_id, "handoff_packet", "created",
        json.dumps({"packet_id": packet_row.id, "readiness_score": readiness.overall_score}),
    )

    return ApprovalHandoffPacketResult(
        packet_id=packet_row.id,
        draft_id=draft_id,
        proposal_id=proposal_id,
        status="pending_human_review",
        sections=sections,
        readiness_score=readiness.overall_score,
        ready_for_review=readiness.ready,
        can_approve=False,
        can_execute=False,
        is_advisory_only=True,
        is_cached=False,
    )
