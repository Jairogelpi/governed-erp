from __future__ import annotations

import json

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from erpguard.db.repositories import (
    get_agent_proposal_draft_link_by_draft,
    get_automation_draft,
    create_agent_draft_handoff_event,
)

_SAFETY_NOTE = (
    "Proof plan is advisory only. No ERP connection is opened, "
    "no real dry-run is executed, and no Odoo data is read or written."
)


class ProofScenario(BaseModel):
    scenario_id: str
    name: str
    category: str
    description: str
    expected_outcome: str
    status: str = "plan_only"


class DraftProofPlanResult(BaseModel):
    draft_id: str
    proposal_id: str | None = None
    plan_generated: bool
    scenarios: list[ProofScenario] = Field(default_factory=list)
    scenario_count: int = 0
    input_guard_checks: list[str] = Field(default_factory=list)
    safety_note: str = _SAFETY_NOTE
    proof_is_plan_only: bool = True
    can_execute: bool = False
    is_advisory_only: bool = True
    blocking_reason: str | None = None


def generate_proof_plan(draft_id: str, session: Session) -> DraftProofPlanResult:
    draft = get_automation_draft(session, draft_id)
    if draft is None:
        return DraftProofPlanResult(
            draft_id=draft_id,
            plan_generated=False,
            blocking_reason="draft_not_found",
        )

    link = get_agent_proposal_draft_link_by_draft(session, draft_id)
    proposal_id = link.proposal_id if link else None

    if draft.write_actions:
        _emit(session, draft_id, proposal_id, "blocked", "write_actions_enabled")
        return DraftProofPlanResult(
            draft_id=draft_id,
            proposal_id=proposal_id,
            plan_generated=False,
            blocking_reason="write_actions_enabled — proof plan blocked",
        )

    if draft.runtime_mode != "dry_run_only":
        _emit(session, draft_id, proposal_id, "blocked", "invalid_runtime_mode")
        return DraftProofPlanResult(
            draft_id=draft_id,
            proposal_id=proposal_id,
            plan_generated=False,
            blocking_reason=f"invalid_runtime_mode — got '{draft.runtime_mode}'",
        )

    try:
        package = json.loads(draft.draft_json)
    except (json.JSONDecodeError, ValueError):
        return DraftProofPlanResult(
            draft_id=draft_id,
            proposal_id=proposal_id,
            plan_generated=False,
            blocking_reason="invalid_draft_json",
        )

    workflow = package.get("workflow", {})
    raw_steps = workflow.get("steps", [])
    guards = package.get("guards", {})
    mandatory_guards = guards.get("mandatory_guards", [])
    entity_mappings = package.get("entity_mappings", [])

    scenarios: list[ProofScenario] = []

    scenarios.append(ProofScenario(
        scenario_id="proof_s01",
        name="Input validation — required fields present",
        category="input_validation",
        description="Verify all required input fields are populated before workflow starts",
        expected_outcome="All required fields validated; workflow proceeds",
        status="plan_only",
    ))

    for idx, guard in enumerate(mandatory_guards, start=1):
        guard_id = guard.get("guard_id", f"guard_{idx}")
        scenarios.append(ProofScenario(
            scenario_id=f"proof_g{idx:02d}",
            name=f"Guard enforcement — {guard_id}",
            category="guard_check",
            description=f"Verify '{guard_id}' guard is active and blocks any disallowed path",
            expected_outcome=f"Guard '{guard_id}' passes; no disallowed operations proceed",
            status="plan_only",
        ))

    for idx, step in enumerate(raw_steps, start=1):
        step_id = step.get("id", f"step_{idx}")
        step_desc = step.get("description", "workflow step")
        scenarios.append(ProofScenario(
            scenario_id=f"proof_w{idx:02d}",
            name=f"Workflow step — {step_id}",
            category="workflow_dry_run",
            description=f"Dry-run simulation of step '{step_id}': {step_desc[:120]}",
            expected_outcome="Step completes with dry_run_only flag; no ERP side effects",
            status="plan_only",
        ))

    scenarios.append(ProofScenario(
        scenario_id="proof_out01",
        name="Output schema verification",
        category="output_verification",
        description="Verify output matches declared schema and contains no live ERP references",
        expected_outcome="Output validated against schema; no real ERP IDs or credentials leaked",
        status="plan_only",
    ))

    if entity_mappings:
        scenarios.append(ProofScenario(
            scenario_id="proof_map01",
            name="Entity mapping coverage check",
            category="mapping_verification",
            description=f"Verify {len(entity_mappings)} entity mapping(s) have valid field references",
            expected_outcome="All mapped fields exist in target model schema (fixture-mode check)",
            status="plan_only",
        ))

    input_guard_checks = [g.get("guard_id", "unknown") for g in mandatory_guards] or [
        "no_generic_writes", "dry_run_only", "requires_human_review"
    ]

    _emit(session, draft_id, proposal_id, "passed", "proof_plan_generated",
          json.dumps({"scenarios": len(scenarios)}))

    return DraftProofPlanResult(
        draft_id=draft_id,
        proposal_id=proposal_id,
        plan_generated=True,
        scenarios=scenarios,
        scenario_count=len(scenarios),
        input_guard_checks=input_guard_checks,
        safety_note=_SAFETY_NOTE,
        proof_is_plan_only=True,
        can_execute=False,
        is_advisory_only=True,
    )


def _emit(session: Session, draft_id: str, proposal_id: str | None, status: str, reason: str, detail: str = "{}"):
    create_agent_draft_handoff_event(
        session, draft_id, proposal_id or draft_id, "proof_plan", status,
        detail if detail != "{}" else json.dumps({"reason": reason}),
    )
