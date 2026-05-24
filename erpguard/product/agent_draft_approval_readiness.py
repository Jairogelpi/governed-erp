from __future__ import annotations

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from erpguard.db.repositories import (
    get_agent_proposal_draft_link_by_draft,
    get_automation_draft,
    list_agent_draft_bridge_events_for_draft,
    list_agent_draft_handoff_events_for_draft,
)
from erpguard.product.agent_draft_bridge_eligibility import check_bridge_eligibility
from erpguard.product.agent_draft_clarification_gate import check_clarification_gate


class ReadinessCheckItem(BaseModel):
    check_id: str
    label: str
    passed: bool
    required: bool = True
    detail: str = ""


class ApprovalReadinessResult(BaseModel):
    draft_id: str
    proposal_id: str | None = None
    ready: bool
    overall_score: int
    checklist: list[ReadinessCheckItem] = Field(default_factory=list)
    blocking_items: list[str] = Field(default_factory=list)
    advisory_items: list[str] = Field(default_factory=list)
    can_approve: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True
    approval_note: str = (
        "Approval readiness is advisory. Human reviewer must independently verify "
        "all checklist items before approving."
    )


def check_approval_readiness(draft_id: str, session: Session) -> ApprovalReadinessResult:
    draft = get_automation_draft(session, draft_id)
    if draft is None:
        return ApprovalReadinessResult(
            draft_id=draft_id,
            ready=False,
            overall_score=0,
            blocking_items=["Draft not found"],
        )

    link = get_agent_proposal_draft_link_by_draft(session, draft_id)
    proposal_id = link.proposal_id if link else None

    checklist: list[ReadinessCheckItem] = []

    eligibility = check_bridge_eligibility(draft_id, session)
    checklist.append(ReadinessCheckItem(
        check_id="chk_eligibility",
        label="Draft is an eligible agent advisory draft",
        passed=eligibility.eligible,
        required=True,
        detail="; ".join(i.message for i in eligibility.issues) if not eligibility.eligible else "OK",
    ))

    checklist.append(ReadinessCheckItem(
        check_id="chk_dry_run_only",
        label="Draft runtime_mode=dry_run_only",
        passed=draft.runtime_mode == "dry_run_only",
        required=True,
        detail=f"runtime_mode={draft.runtime_mode}",
    ))

    checklist.append(ReadinessCheckItem(
        check_id="chk_write_actions_false",
        label="Draft write_actions=False",
        passed=not draft.write_actions,
        required=True,
        detail=f"write_actions={draft.write_actions}",
    ))

    gate = check_clarification_gate(draft_id, session)
    checklist.append(ReadinessCheckItem(
        check_id="chk_clarification_gate",
        label="Clarification gate passed",
        passed=gate.gate_passed,
        required=False,
        detail="; ".join(gate.blocking_reasons) if gate.blocking_reasons else f"questions={gate.questions_pct}%, mappings={gate.mappings_pct}%",
    ))

    bridge_events = list_agent_draft_bridge_events_for_draft(session, draft_id)
    bridge_status: dict[str, str] = {}
    for ev in bridge_events:
        bridge_status[ev.step] = ev.status

    for step in ("review", "validation", "compile_plan"):
        status = bridge_status.get(step, "not_run")
        checklist.append(ReadinessCheckItem(
            check_id=f"chk_bridge_{step}",
            label=f"Bridge step passed: {step}",
            passed=status == "passed",
            required=True,
            detail=f"status={status}",
        ))

    handoff_events = list_agent_draft_handoff_events_for_draft(session, draft_id)
    handoff_status: dict[str, str] = {}
    for ev in handoff_events:
        handoff_status[ev.step] = ev.status

    proof_ok = handoff_status.get("proof_plan") == "passed"
    checklist.append(ReadinessCheckItem(
        check_id="chk_proof_plan",
        label="Dry-run proof plan generated",
        passed=proof_ok,
        required=True,
        detail=f"status={handoff_status.get('proof_plan', 'not_run')}",
    ))

    evidence_ok = handoff_status.get("evidence") == "assembled"
    checklist.append(ReadinessCheckItem(
        check_id="chk_evidence",
        label="Proof evidence bundle assembled",
        passed=evidence_ok,
        required=False,
        detail=f"status={handoff_status.get('evidence', 'not_run')}",
    ))

    required_items = [c for c in checklist if c.required]
    passed_required = sum(1 for c in required_items if c.passed)
    total_required = len(required_items)
    overall_score = (passed_required * 100 // total_required) if total_required else 0

    blocking_items = [c.label for c in required_items if not c.passed]
    advisory_items = [c.label for c in checklist if not c.required and not c.passed]

    ready = len(blocking_items) == 0

    return ApprovalReadinessResult(
        draft_id=draft_id,
        proposal_id=proposal_id,
        ready=ready,
        overall_score=overall_score,
        checklist=checklist,
        blocking_items=blocking_items,
        advisory_items=advisory_items,
        can_approve=False,
        can_execute=False,
        is_advisory_only=True,
    )
