from __future__ import annotations

import json

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from erpguard.db.repositories import (
    get_agent_proposal_draft_link_by_draft,
    get_automation_draft,
    list_agent_draft_bridge_events_for_draft,
    list_agent_draft_handoff_events_for_draft,
    create_agent_draft_handoff_event,
)
from erpguard.product.agent_clarification_completeness import compute_clarification_completeness


class EvidenceItem(BaseModel):
    item_id: str
    source: str
    label: str
    status: str
    detail: str = ""


class DraftProofEvidenceResult(BaseModel):
    draft_id: str
    proposal_id: str | None = None
    evidence_items: list[EvidenceItem] = Field(default_factory=list)
    evidence_count: int = 0
    bridge_steps_passed: int = 0
    bridge_steps_total: int = 0
    clarification_questions_pct: int = 0
    clarification_mappings_pct: int = 0
    proof_plan_generated: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True
    blocking_reason: str | None = None


def get_proof_evidence(draft_id: str, session: Session) -> DraftProofEvidenceResult:
    draft = get_automation_draft(session, draft_id)
    if draft is None:
        return DraftProofEvidenceResult(
            draft_id=draft_id,
            blocking_reason="draft_not_found",
        )

    link = get_agent_proposal_draft_link_by_draft(session, draft_id)
    proposal_id = link.proposal_id if link else None

    items: list[EvidenceItem] = []

    items.append(EvidenceItem(
        item_id="ev_draft",
        source="automation_draft",
        label="Draft safety flags",
        status="passed" if (not draft.write_actions and draft.runtime_mode == "dry_run_only") else "failed",
        detail=f"runtime_mode={draft.runtime_mode}, write_actions={draft.write_actions}",
    ))

    if link is not None:
        items.append(EvidenceItem(
            item_id="ev_link",
            source="agent_proposal_draft_link",
            label="Proposal-draft link",
            status="passed",
            detail=f"proposal_id={proposal_id}",
        ))
    else:
        items.append(EvidenceItem(
            item_id="ev_link",
            source="agent_proposal_draft_link",
            label="Proposal-draft link",
            status="missing",
            detail="No link found",
        ))

    bridge_events = list_agent_draft_bridge_events_for_draft(session, draft_id)
    bridge_step_set = {"review", "validation", "compile_plan"}
    bridge_passed: set[str] = set()
    for ev in bridge_events:
        if ev.step in bridge_step_set and ev.status == "passed":
            bridge_passed.add(ev.step)
            items.append(EvidenceItem(
                item_id=f"ev_bridge_{ev.step}",
                source="bridge_pipeline",
                label=f"Bridge step: {ev.step}",
                status="passed",
                detail=ev.detail_json,
            ))

    for step in bridge_step_set - bridge_passed:
        items.append(EvidenceItem(
            item_id=f"ev_bridge_{step}",
            source="bridge_pipeline",
            label=f"Bridge step: {step}",
            status="not_run",
            detail="",
        ))

    if proposal_id:
        completeness = compute_clarification_completeness(proposal_id, session)
        items.append(EvidenceItem(
            item_id="ev_clarif",
            source="clarification_completeness",
            label="Clarification completeness",
            status="passed" if completeness.overall_complete else "incomplete",
            detail=f"questions={completeness.questions_pct}%, mappings={completeness.mappings_pct}%",
        ))
        q_pct = completeness.questions_pct
        m_pct = completeness.mappings_pct
    else:
        q_pct, m_pct = 0, 0

    handoff_events = list_agent_draft_handoff_events_for_draft(session, draft_id)
    proof_plan_generated = any(
        ev.step == "proof_plan" and ev.status == "passed" for ev in handoff_events
    )
    items.append(EvidenceItem(
        item_id="ev_proof_plan",
        source="handoff_pipeline",
        label="Dry-run proof plan",
        status="passed" if proof_plan_generated else "not_run",
        detail="",
    ))

    create_agent_draft_handoff_event(
        session, draft_id, proposal_id or draft_id, "evidence", "assembled",
        json.dumps({"items": len(items), "bridge_passed": len(bridge_passed)}),
    )

    return DraftProofEvidenceResult(
        draft_id=draft_id,
        proposal_id=proposal_id,
        evidence_items=items,
        evidence_count=len(items),
        bridge_steps_passed=len(bridge_passed),
        bridge_steps_total=len(bridge_step_set),
        clarification_questions_pct=q_pct,
        clarification_mappings_pct=m_pct,
        proof_plan_generated=proof_plan_generated,
        can_execute=False,
        is_advisory_only=True,
    )
