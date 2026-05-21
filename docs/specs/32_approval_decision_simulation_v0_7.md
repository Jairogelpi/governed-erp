# 32 Approval Decision Simulation v0.7

**Status:** Implementation spec for Approval Decision Simulation MVP
**Date:** May 19, 2026
**Baseline commits:** `b615ad4`, `c9b4f75`
**Relationship to Approval Gate / Safe Action Plan v0.6:** Simulates the human approval decision for the safe plan without executing any ERP write.

## Purpose

Approval Decision Simulation v0.7 lets the user simulate the human approval choice for a previously planned critical action.

The block records an approval decision as evidence only. It does not execute `confirm_sales_order` and does not write to ERP.

## Problem Solved Compared To v0.6

Approval Gate / Safe Action Plan v0.6 answers what the system would do before approval.

Approval Decision Simulation v0.7 answers how the human decision changes the story while still keeping the ERP write blocked.

That adds the missing safety step between planning and real execution: the system can now show approve or reject evidence without turning the decision into a write action.

## Simulated Decision Contract

The endpoint is:

```http
POST /v1/skills/{skill_id}/simulate-approval-decision
```

Request body:

```json
{
  "inputs": {
    "order_reference": "SO-VALID"
  },
  "requested_action": "confirm_sales_order",
  "decision": "approve",
  "approver": {
    "type": "user",
    "id": "demo_approver",
    "display_name": "Demo Approver"
  },
  "reason": "Formula preview is clean."
}
```

Response body:

```json
{
  "skill_id": "skill_...",
  "requested_action": "confirm_sales_order",
  "approval_decision": "approved",
  "approval_required": true,
  "risk_level": "R3",
  "guard_preview": {
    "decision": "allow",
    "issues_count": 0
  },
  "approver": {
    "type": "user",
    "id": "demo_approver",
    "display_name": "Demo Approver"
  },
  "reason": "Formula preview is clean.",
  "status": "approved_but_not_executed",
  "simulated_execution": {
    "would_execute": true,
    "did_execute": false,
    "blocked_reason": "real_erp_write_blocked_by_mvp_scope"
  },
  "proof": {
    "approval_decision_recorded": true,
    "approval_required": true,
    "guard_checked_before_decision": true,
    "real_erp_write_blocked": true,
    "no_real_execution": true,
    "human_decision_simulated": true
  }
}
```

## Approve Vs Reject

The request accepts `approve` or `reject`.

- `approve` with a guard preview of `allow` yields `approved_but_not_executed` and still blocks the real ERP write by MVP scope.
- `approve` with a guard preview of `block` yields a blocked-before-execution status and does not simulate execution.
- `reject` always yields `rejected_before_execution` and does not simulate execution.

## Relationship To Safe Action Plan

The decision simulation builds on the safe plan from v0.6.

It reuses the same critical-action identity, the same approval requirement, the same risk level, and the same Formula Guard preview.

The simulation does not invent a second planning system.

## Relationship To Risk Engine

The simulated decision keeps using the central risk semantics.

`confirm_sales_order` remains an R3 action and therefore approval-required.

The endpoint does not override or duplicate the risk engine.

## Relationship To Formula Guard

Formula Guard is checked before the simulated decision is finalized.

For `SO-VALID`, the preview decision is `allow`.
For `SO-FORMULA-MISMATCH`, the preview decision is `block`.

The simulation only reports the guard state; it does not perform a real ERP write.

## Relationship To SkillRun And SkillRunStep

This block does not require a new approval table.

The simulation endpoint must not create `SkillRun` or `SkillRunStep` rows.

That keeps the approval evidence simulated and separate from actual execution history.

## Using Approval Decision Simulation From `/demo`

After generating a safe plan, `/demo` should show a dedicated Approval Decision Simulation v0.7 panel.

The panel should let the operator simulate approve for `SO-VALID` and simulate reject for `SO-FORMULA-MISMATCH`, then show the simulated response JSON and proof that no real ERP execution occurred.

The UI must remain vanilla HTML and JavaScript.

## Expected Tests

Tests must prove:

- approve `SO-VALID` returns `approved_but_not_executed`;
- approve `SO-VALID` returns `did_execute = false`;
- approve `SO-VALID` returns `blocked_reason = real_erp_write_blocked_by_mvp_scope`;
- approve `SO-FORMULA-MISMATCH` does not execute and returns `blocked_reason = guard_blocked`;
- reject `SO-FORMULA-MISMATCH` returns `rejected_before_execution`;
- reject `SO-FORMULA-MISMATCH` returns `blocked_reason = rejected_by_human`;
- unsupported decision returns a controlled error;
- unsupported action returns a controlled error;
- missing skill returns a controlled error;
- the endpoint does not create `SkillRun` rows;
- `/demo` contains `Approval Decision Simulation v0.7`;
- health still works;
- plan-action tests remain green.

## No-Goals

Approval Decision Simulation v0.7 must not add:

- real Odoo UI automation;
- MCP;
- LLM-based decisioning;
- browser extension capture;
- unrestricted recording;
- marketplace behavior;
- a frontend framework;
- approval persistence tables;
- real ERP write actions;
- real `confirm_sales_order` execution;
- a full approval workflow.

The scope remains a controlled simulation over the critical sales-order confirmation path.

## Acceptance Criteria

Approval Decision Simulation v0.7 is accepted when:

- `POST /v1/skills/{skill_id}/simulate-approval-decision` returns readable approved and rejected evidence;
- the response reports the correct approval decision and simulated execution status;
- the endpoint never performs a real ERP write;
- `/demo` shows the new simulation panel;
- README and AGENTS are updated;
- `python -m pytest` passes, with browser-dependent skips documented if present;
- no LLM, MCP, browser extension, real Odoo UI, free recorder, marketplace, frontend framework, or real ERP write action is introduced.