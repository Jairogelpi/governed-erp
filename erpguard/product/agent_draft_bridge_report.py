from __future__ import annotations

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from erpguard.db.repositories import (
    get_agent_proposal_draft_link_by_draft,
    get_automation_draft,
    list_agent_draft_bridge_events_for_draft,
)
from erpguard.product.agent_draft_bridge_eligibility import check_bridge_eligibility
from erpguard.product.agent_draft_clarification_gate import check_clarification_gate


class BridgeStepStatus(BaseModel):
    step: str
    status: str
    detail: str | None = None


class DraftBridgeReport(BaseModel):
    draft_id: str
    proposal_id: str | None = None
    overall_status: str
    steps: list[BridgeStepStatus] = Field(default_factory=list)
    can_execute: bool = False
    is_advisory_only: bool = True
    next_action: str


def get_bridge_report(draft_id: str, session: Session) -> DraftBridgeReport:
    draft = get_automation_draft(session, draft_id)
    if draft is None:
        return DraftBridgeReport(
            draft_id=draft_id,
            overall_status="blocked",
            steps=[BridgeStepStatus(step="draft_lookup", status="failed", detail="Draft not found")],
            next_action="Create a valid agent advisory draft first",
        )

    link = get_agent_proposal_draft_link_by_draft(session, draft_id)
    proposal_id = link.proposal_id if link else None

    eligibility = check_bridge_eligibility(draft_id, session)
    if not eligibility.eligible:
        return DraftBridgeReport(
            draft_id=draft_id,
            proposal_id=proposal_id,
            overall_status="blocked",
            steps=[
                BridgeStepStatus(
                    step="eligibility",
                    status="failed",
                    detail="; ".join(i.message for i in eligibility.issues),
                )
            ],
            next_action="Resolve eligibility issues before bridging",
        )

    gate = check_clarification_gate(draft_id, session)

    events = list_agent_draft_bridge_events_for_draft(session, draft_id)
    event_map: dict[str, str] = {}
    event_detail_map: dict[str, str] = {}
    for ev in events:
        event_map[ev.step] = ev.status
        event_detail_map[ev.step] = ev.detail_json

    steps: list[BridgeStepStatus] = [
        BridgeStepStatus(step="eligibility", status="passed"),
        BridgeStepStatus(
            step="clarification_gate",
            status="passed" if gate.gate_passed else "blocked",
            detail="; ".join(gate.blocking_reasons) if gate.blocking_reasons else None,
        ),
    ]

    for step_name in ("review", "validation", "compile_plan"):
        if step_name in event_map:
            steps.append(BridgeStepStatus(
                step=step_name,
                status=event_map[step_name],
            ))
        else:
            steps.append(BridgeStepStatus(step=step_name, status="not_started"))

    failed = [s for s in steps if s.status in ("failed", "blocked")]
    not_started = [s for s in steps if s.status == "not_started"]
    all_passed = all(s.status == "passed" for s in steps)

    if failed:
        overall_status = "blocked"
        next_action = f"Resolve step(s): {', '.join(s.step for s in failed)}"
    elif not_started:
        overall_status = "incomplete"
        next_action = f"Run bridge step(s): {', '.join(s.step for s in not_started)}"
    else:
        overall_status = "complete"
        next_action = "All bridge steps passed — submit for human review and approval"

    return DraftBridgeReport(
        draft_id=draft_id,
        proposal_id=proposal_id,
        overall_status=overall_status,
        steps=steps,
        can_execute=False,
        is_advisory_only=True,
        next_action=next_action,
    )
