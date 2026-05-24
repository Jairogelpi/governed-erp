from __future__ import annotations

import json

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from erpguard.db.repositories import (
    get_agent_proposal_draft_link_by_draft,
    get_automation_draft,
    create_agent_draft_bridge_event,
)

_SAFETY_NOTE = (
    "Compile plan is advisory only. No Skill records were created. "
    "Requires human review, validation, and approval before any activation."
)


class CompileBridgePlanStep(BaseModel):
    step_id: str
    description: str
    status: str = "plan_only"


class DraftCompileBridgeResult(BaseModel):
    draft_id: str
    proposal_id: str | None = None
    plan_generated: bool
    plan_steps: list[CompileBridgePlanStep] = Field(default_factory=list)
    estimated_inputs: list[str] = Field(default_factory=list)
    estimated_outputs: list[str] = Field(default_factory=list)
    compile_blocked: bool = False
    blocking_reason: str | None = None
    can_execute: bool = False
    is_advisory_only: bool = True
    safety_note: str = _SAFETY_NOTE


def generate_compile_plan(draft_id: str, session: Session) -> DraftCompileBridgeResult:
    draft = get_automation_draft(session, draft_id)
    if draft is None:
        return DraftCompileBridgeResult(
            draft_id=draft_id,
            plan_generated=False,
            compile_blocked=True,
            blocking_reason="draft_not_found",
        )

    link = get_agent_proposal_draft_link_by_draft(session, draft_id)
    proposal_id = link.proposal_id if link else None

    if draft.write_actions:
        create_agent_draft_bridge_event(
            session, draft_id, proposal_id or draft_id, "compile_plan", "blocked",
            json.dumps({"reason": "write_actions_enabled"}),
        )
        return DraftCompileBridgeResult(
            draft_id=draft_id,
            proposal_id=proposal_id,
            plan_generated=False,
            compile_blocked=True,
            blocking_reason="write_actions_enabled — compile blocked; draft must have write_actions=False",
        )

    if draft.runtime_mode != "dry_run_only":
        create_agent_draft_bridge_event(
            session, draft_id, proposal_id or draft_id, "compile_plan", "blocked",
            json.dumps({"reason": "invalid_runtime_mode"}),
        )
        return DraftCompileBridgeResult(
            draft_id=draft_id,
            proposal_id=proposal_id,
            plan_generated=False,
            compile_blocked=True,
            blocking_reason=f"invalid_runtime_mode — got '{draft.runtime_mode}', expected 'dry_run_only'",
        )

    try:
        package = json.loads(draft.draft_json)
    except (json.JSONDecodeError, ValueError):
        return DraftCompileBridgeResult(
            draft_id=draft_id,
            proposal_id=proposal_id,
            plan_generated=False,
            compile_blocked=True,
            blocking_reason="invalid_draft_json",
        )

    workflow = package.get("workflow", {})
    raw_steps = workflow.get("steps", [])
    entity_mappings = package.get("entity_mappings", [])
    clarification_questions = package.get("clarification_questions", [])

    plan_steps: list[CompileBridgePlanStep] = [
        CompileBridgePlanStep(
            step_id="compile_plan_01",
            description="Validate draft safety constraints (dry_run_only, write_actions=False, advisory guards)",
            status="plan_only",
        ),
        CompileBridgePlanStep(
            step_id="compile_plan_02",
            description="Generate input/output schema from entity mappings and clarification answers",
            status="plan_only",
        ),
        CompileBridgePlanStep(
            step_id="compile_plan_03",
            description=f"Build {len(raw_steps)} workflow step(s) into deterministic skill package",
            status="plan_only",
        ),
        CompileBridgePlanStep(
            step_id="compile_plan_04",
            description="Attach mandatory guards (no_generic_writes, no_r3_r4_writes, requires_human_review)",
            status="plan_only",
        ),
        CompileBridgePlanStep(
            step_id="compile_plan_05",
            description="Package dry-run proof evidence and test cases — no live ERP calls",
            status="plan_only",
        ),
        CompileBridgePlanStep(
            step_id="compile_plan_06",
            description="Mark compiled skill as pending_human_approval — cannot activate without explicit sign-off",
            status="plan_only",
        ),
    ]

    estimated_inputs = [
        m.get("erp_field", m.get("proposed_field", "unknown_field"))
        for m in entity_mappings
        if isinstance(m, dict)
    ] or ["connection_id", "context"]

    estimated_outputs = ["status", "recommendation", "dry_run_summary"]

    if clarification_questions:
        estimated_outputs.append("clarification_notes")

    create_agent_draft_bridge_event(
        session, draft_id, proposal_id or draft_id, "compile_plan", "passed",
        json.dumps({
            "plan_steps": len(plan_steps),
            "estimated_inputs": len(estimated_inputs),
            "estimated_outputs": len(estimated_outputs),
        }),
    )

    return DraftCompileBridgeResult(
        draft_id=draft_id,
        proposal_id=proposal_id,
        plan_generated=True,
        plan_steps=plan_steps,
        estimated_inputs=estimated_inputs,
        estimated_outputs=estimated_outputs,
        compile_blocked=False,
        can_execute=False,
        is_advisory_only=True,
        safety_note=_SAFETY_NOTE,
    )
