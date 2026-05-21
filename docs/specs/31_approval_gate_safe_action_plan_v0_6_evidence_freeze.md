# 31 Approval Gate / Safe Action Plan v0.6 Evidence Freeze

**Status:** Evidence and documentation freeze
**Date:** May 19, 2026
**Baseline commit:** `c9b4f75 feat: add approval gate safe action plan v0.6`
**Evidence artifact:** `docs/demo/approval_gate_safe_action_plan_v0_6_success_response.json`

## Purpose

This document freezes the Approval Gate / Safe Action Plan v0.6 evidence state after the dry-run critical-action planning endpoint and its `/demo` integration were added.

This block is documentation and evidence only. It does not expand runtime scope, ERP coverage, approval orchestration, or UI architecture.

## Exact Approval Gate / Safe Action Plan v0.6 State

Approval Gate / Safe Action Plan v0.6 is a dry-run planning layer over the compiled skill that already exists in the Skill Registry.

It includes:

- `POST /v1/skills/{skill_id}/plan-action`;
- central reuse of the risk engine semantic for `confirm_sales_order`;
- Formula Guard preview before approval;
- approval-required status for the critical action;
- a plan with ordered steps;
- proof that no real ERP execution occurs;
- `/demo` rendering of the approval gate section after compile and inspect.

## Problem Solved Compared To Run History / Audit Timeline v0.5

Run History / Audit Timeline v0.5 explains what happened after a skill already ran.

Approval Gate / Safe Action Plan v0.6 explains what must happen before a critical action is allowed to run.

That matters because the system now has a pre-execution safety barrier for the critical sales-order confirmation path.

## Safe Plan Endpoint

The endpoint is:

```http
POST /v1/skills/{skill_id}/plan-action
```

The request used in this freeze is:

```json
{
  "inputs": {
    "order_reference": "SO-VALID"
  },
  "requested_action": "confirm_sales_order"
}
```

### Safe Plan Response Contract

The response shape is:

```json
{
  "skill_id": "skill_...",
  "requested_action": "confirm_sales_order",
  "approval_required": true,
  "risk_level": "R3",
  "status": "approval_required",
  "plan": {
    "summary": "Plan critical action confirm_sales_order on SalesOrder with Formula Guard preview and human approval before execution.",
    "steps": [
      {"id": "load_skill", "type": "load", "description": "..."},
      {"id": "load_order", "type": "load", "description": "..."},
      {"id": "run_formula_guard", "type": "guard", "description": "..."},
      {"id": "request_human_approval", "type": "approval", "description": "..."},
      {"id": "blocked_before_real_execution", "type": "safety_stop", "description": "..."}
    ]
  },
  "guard_preview": {
    "decision": "allow|block",
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

## Visible Fields

The safe plan must surface:

- `skill_id`;
- `requested_action`;
- `approval_required`;
- `risk_level`;
- `status`;
- `plan.summary`;
- ordered plan steps;
- `guard_preview`;
- `proof`.

## Proof Flags

The proof block communicates the important runtime safety facts:

- `critical_action_detected` says the plan recognized the critical sales-order confirmation path;
- `approval_required` says human approval is required;
- `guard_checked_before_approval` says Formula Guard is previewed before approval;
- `real_erp_write_blocked` says the endpoint stopped before any ERP write;
- `no_real_execution` says no real confirm operation was executed.

## Relationship To Risk Engine

The safe plan reuses the existing risk engine semantics.

`confirm_sales_order` remains an R3 canonical action and therefore requires approval.

The freeze confirms the endpoint does not duplicate risk logic or introduce a parallel approval policy.

## Relationship To ERPGuard Formula Guard

The plan previews Formula Guard before the approval step.

For `SO-VALID`, the preview decision is `allow` with zero issues.
For `SO-FORMULA-MISMATCH`, the preview decision is `block` with one issue.

The plan never executes Formula Guard against a real ERP write path.

## Relationship To SkillRun And SkillRunStep

This block does not require a new approval table.

The dry-run planning endpoint does not create a `SkillRun` or `SkillRunStep` record.

The evidence freeze confirms that planning remains separate from actual run history.

## Using Approval Gate From `/demo`

Start the API:

```bash
uvicorn apps.api.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/demo
```

After compile and inspect, the `/demo` page renders an Approval Gate / Safe Action Plan v0.6 panel and can generate a safe plan for `confirm_sales_order`.

The same panel stays vanilla HTML and JavaScript.

## Tests Performed

Approval Gate / Safe Action Plan v0.6 added and preserved tests for:

- `SO-VALID` returning `approval_required = true`;
- `SO-VALID` returning `guard_preview.decision = allow`;
- `SO-FORMULA-MISMATCH` returning `guard_preview.decision = block`;
- proof that `real_erp_write_blocked = true`;
- proof that no skill runs are created by the planning endpoint;
- controlled error for an unsupported action;
- controlled error for a missing skill;
- `/demo` containing `Approval Gate / Safe Action Plan v0.6`;
- health route;
- inspect, readiness, and run history/timeline behavior remaining intact.

## Exact Pytest Result

The verification command is:

```bash
python -m pytest
```

Result for this evidence freeze:

```text
159 passed, 9 skipped
```

## Known Skips

The skipped tests are browser-dependent paths in this shell because Chromium/Playwright browser runtime availability is not active for the plain `python -m pytest` run.

The evidence artifact uses FastAPI `TestClient`; it does not require launching Chromium.

## Limitations

Approval Gate / Safe Action Plan v0.6 is intentionally narrow:

- it only covers the critical `confirm_sales_order` planning path;
- it previews Formula Guard but does not execute a real ERP write;
- it does not introduce approval persistence;
- it does not infer arbitrary user intent;
- it does not repair unknown plans;
- it does not automate real ERP writes.

## No-Goals

This milestone did not add:

- real Odoo UI automation;
- MCP;
- LLM-based planning;
- browser extension capture;
- unrestricted/free recording;
- marketplace behavior;
- frontend framework;
- new approval tables;
- real ERP write actions;
- real `confirm_sales_order` execution;
- approval orchestration beyond a single dry-run plan.

It also did not change or break `POST /v1/demo/full-record-to-skill-flow`, `GET /v1/recordings/{recording_id}/readiness`, `GET /v1/skills/{skill_id}/inspect`, `GET /v1/skills/{skill_id}/plan-action`, `GET /v1/skills/{skill_id}/runs`, `GET /v1/skills/{skill_id}/runs/{skill_run_id}/timeline`, `POST /v1/recordings/{recording_id}/compile-skill`, or `POST /v1/skills/{skill_id}/run`.

## Negative Evidence

The evidence artifact captures controlled negative responses for:

- `POST /v1/skills/{skill_id}/plan-action` with `requested_action = inspect_access_rules` -> `unsupported_action`;
- `POST /v1/skills/missing-skill/plan-action` -> `skill_not_found`.

## Recommended Next Block

The next block should remain controlled and evidence-first.

Recommended next step:

```text
v0.7 Approval Decision Simulation
```

That block could simulate the human approval decision itself while still avoiding LLM, MCP, browser extension, real Odoo, free recording, marketplace, frontend framework, or real ERP write actions.
