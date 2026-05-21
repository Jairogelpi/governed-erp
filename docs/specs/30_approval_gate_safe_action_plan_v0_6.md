# 30 Approval Gate / Safe Action Plan v0.6

**Status:** Implementation spec for Approval Gate MVP
**Date:** May 19, 2026
**Baseline commits:** `ee2b63b`, `28eb983`
**Relationship to Run History / Audit Timeline v0.5:** Adds a pre-execution safety plan for the critical action that the audit timeline later proves did not run without approval.

## Purpose

Approval Gate / Safe Action Plan v0.6 lets the user preview a critical action, see the risk level, inspect the guard preview, and require human approval before any real ERP execution is allowed.

The block is a dry-run only. It generates a safe action plan and stops before any ERP write.

## Problem Solved Compared To Run History v0.5

Run History / Audit Timeline v0.5 answers what happened after a skill already ran.

Approval Gate / Safe Action Plan v0.6 answers what must happen before a critical action is allowed to run.

That gives the system a stronger safety boundary: the user can now preview a dangerous action, see that Formula Guard is checked first, and confirm that the real ERP write is still blocked.

## Safe Plan Contract

The endpoint is:

```http
POST /v1/skills/{skill_id}/plan-action
```

Request body:

```json
{
  "inputs": {
    "order_reference": "SO-VALID"
  },
  "requested_action": "confirm_sales_order"
}
```

Response body:

```json
{
  "skill_id": "skill_...",
  "requested_action": "confirm_sales_order",
  "approval_required": true,
  "risk_level": "R3",
  "status": "approval_required",
  "plan": {
    "summary": "...",
    "steps": [
      {"id": "load_skill", "type": "load", "description": "..."},
      {"id": "load_order", "type": "load", "description": "..."},
      {"id": "run_formula_guard", "type": "guard", "description": "..."},
      {"id": "request_human_approval", "type": "approval", "description": "..."},
      {"id": "blocked_before_real_execution", "type": "safety_stop", "description": "..."}
    ]
  },
  "guard_preview": {
    "decision": "allow",
    "issues_count": 0
  },
  "proof": {
    "critical_action_detected": true,
    "approval_required": true,
    "guard_checked_before_approval": true,
    "real_erp_write_blocked": true,
    "no_real_execution": true
  }
}
```

## Approval States

Approval Gate uses a small controlled status set:

- `approval_required` for the planned critical action;
- `approved` for a future human approval state, not implemented yet;
- `rejected` for a future human rejection state, not implemented yet;
- `blocked` when the plan or preview detects a safety issue before approval;
- `dry_run` for the execution mode of this endpoint.

Only the dry-run planning state is implemented in this block.

## Relationship To Risk Engine

The plan uses the existing risk engine semantics for canonical actions.

`confirm_sales_order` remains the critical action and keeps its R3 default risk level.

The endpoint reuses the central risk logic so the safety contract stays aligned with the rest of the system instead of duplicating approval rules in the route.

## Relationship To ERPGuard Formula Guard

The safe plan must preview Formula Guard before any human approval prompt.

The plan does not execute Formula Guard against the ERP. It only previews the guard decision so the user can see whether the order would allow or block the critical action.

That keeps the plan deterministic and audit-friendly while still preventing a real ERP write.

## Relationship To SkillRun And SkillRunStep

This block does not require a new approval table.

It does not create a `SkillRun` or `SkillRunStep` record for the dry-run planning endpoint.

If the implementation later decides to persist planning evidence, it must remain clearly marked as planning-only and must not be confused with a real execution run.

## Using Approval Gate From `/demo`

After a skill is compiled and inspected, `/demo` should show a dedicated Approval Gate / Safe Action Plan v0.6 panel.

The panel should let the operator generate a plan for `confirm_sales_order`, display the approval requirement, show the risk level, preview the guard decision, render the planned steps, and show that no real ERP execution occurs.

The UI must remain vanilla HTML and JavaScript.

## Expected Tests

Tests must prove:

- `plan-action` for `SO-VALID` returns `approval_required = true`;
- `plan-action` for `SO-VALID` returns `guard_preview.decision = allow`;
- `plan-action` for `SO-FORMULA-MISMATCH` returns `guard_preview.decision = block`;
- `plan-action` always returns `proof.real_erp_write_blocked = true`;
- `plan-action` does not create real actions or change ERP state;
- unknown actions return a controlled error;
- a missing skill returns a controlled error;
- `/demo` contains `Approval Gate / Safe Action Plan v0.6`;
- `GET /health` still works;
- inspect, readiness, and run history/timeline continue to pass.

## No-Goals

Approval Gate / Safe Action Plan v0.6 must not add:

- real Odoo UI automation;
- MCP;
- LLM-based planning;
- browser extension capture;
- unrestricted recording;
- marketplace behavior;
- a frontend framework;
- new approval tables;
- real ERP write actions;
- real `confirm_sales_order` execution;
- approval orchestration beyond a single dry-run plan.

The scope remains a controlled preview for a critical sales-order confirmation action.

## Acceptance Criteria

Approval Gate / Safe Action Plan v0.6 is accepted when:

- `POST /v1/skills/{skill_id}/plan-action` returns a readable safe action plan for `confirm_sales_order`;
- the plan reports `approval_required = true` and `risk_level = R3`;
- the plan preview shows Formula Guard before human approval;
- the endpoint never performs a real ERP write;
- `/demo` shows the new approval gate section;
- README and AGENTS are updated;
- `python -m pytest` passes, with browser-dependent skips documented if present;
- no LLM, MCP, browser extension, real Odoo UI, free recorder, marketplace, frontend framework, or real ERP write action is introduced.
