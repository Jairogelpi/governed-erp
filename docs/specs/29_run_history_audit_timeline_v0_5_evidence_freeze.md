# 29 Run History / Audit Timeline v0.5 Evidence Freeze

**Status:** Evidence and documentation freeze
**Date:** May 19, 2026
**Baseline commit:** `ee2b63b feat: add run history audit timeline v0.5`
**Evidence artifact:** `docs/demo/run_history_audit_timeline_v0_5_success_response.json`

## Purpose

This document freezes the Run History / Audit Timeline v0.5 evidence state after the read-only execution-history endpoints and `/demo` integration were added.

This block is documentation and evidence only. It does not expand runtime scope, ERP coverage, automation capability, or UI architecture.

## Exact Run History / Audit Timeline v0.5 State

Run History / Audit Timeline v0.5 is a read-only audit layer over the existing Skill Registry execution records.

It includes:

- `GET /v1/skills/{skill_id}/runs`;
- `GET /v1/skills/{skill_id}/runs/{skill_run_id}/timeline`;
- read-only projections over `SkillRun` and `SkillRunStep`;
- latest run summary fields with allow/block decisions and token savings;
- ordered timeline rows for the runtime steps;
- `/demo` rendering of the run history and audit timeline section after the compiled skill is run.

## Problem Solved Compared To Skill Inspector v0.4

Skill Inspector v0.4 explains what was compiled.

Run History / Audit Timeline v0.5 explains what happened when that compiled skill ran.

That matters because the compiled skill can be safe in structure, but the user still needs auditable runtime evidence: which runs occurred, which decision each run made, and which steps executed in order.

This milestone closes the evidence loop from compile -> inspect -> run -> audit timeline.

## Run History Endpoint

The endpoint is:

```http
GET /v1/skills/{skill_id}/runs
```

It loads the skill row and then projects the stored `SkillRun` rows for that skill.

If the skill is missing, the endpoint returns a controlled `skill_not_found` response.

### Run List Response Contract

The response shape is:

```json
{
  "skill_id": "skill_...",
  "runs": [
    {
      "skill_run_id": "skill_run_...",
      "skill_version_id": "skill_version_...",
      "status": "success|failed|running",
      "decision": "allow|block|null",
      "created_at": "...",
      "finished_at": "...",
      "input": {"inputs": {"order_reference": "SO-VALID"}},
      "output_summary": {
        "order_reference": "SO-VALID",
        "issues_count": 0,
        "policy_id": "formula_guard"
      },
      "estimated_tokens_saved": 2000
    }
  ]
}
```

## Timeline Endpoint

The endpoint is:

```http
GET /v1/skills/{skill_id}/runs/{skill_run_id}/timeline
```

It loads the skill row, then the specific `SkillRun`, then the ordered `SkillRunStep` rows for that run.

If the skill is missing, the endpoint returns a controlled `skill_not_found` response.

If the run is missing or does not belong to the skill, the endpoint returns a controlled `skill_run_not_found` response.

### Timeline Response Contract

The response shape is:

```json
{
  "skill_id": "skill_...",
  "skill_run_id": "skill_run_...",
  "status": "success",
  "decision": "allow",
  "timeline": [
    {"step_id": "load_skill", "step_type": "load", "status": "passed"},
    {"step_id": "load_order", "step_type": "load", "status": "passed"},
    {"step_id": "formula_guard", "step_type": "guard", "status": "passed|blocked|failed"},
    {"step_id": "produce_result", "step_type": "result", "status": "passed"}
  ],
  "proof": {
    "has_guard_step": true,
    "has_result_step": true,
    "decision_is_auditable": true,
    "llm_replay_not_required": true
  }
}
```

## Visible Fields

The run list must surface:

- `skill_run_id`;
- `skill_version_id`;
- `status`;
- `decision`;
- `created_at`;
- `finished_at`;
- `input`;
- `output_summary`;
- `estimated_tokens_saved`.

The timeline must surface:

- `skill_id`;
- `skill_run_id`;
- `status`;
- `decision`;
- ordered `timeline` step rows;
- `proof`.

## Proof Flags

The timeline `proof` block communicates the important runtime evidence facts:

- `has_guard_step` says whether a guard step is present;
- `has_result_step` says whether the result step is present;
- `decision_is_auditable` says the runtime decision can be traced through the timeline;
- `llm_replay_not_required` says deterministic replay did not require LLM assistance.

## Relationship To SkillRun And SkillRunStep

Run History / Audit Timeline reuses the existing `SkillRun` and `SkillRunStep` persistence models.

It does not create a new table.

The run list is a projection of `SkillRun` records for a skill.
The timeline is an ordered projection of the `SkillRunStep` rows for a specific run.

## Relationship To ERPGuard Formula Guard

The execution history centers on the Formula Guard decision path.

The `formula_guard` step is the auditable decision point that turns the compiled skill into a visible allow/block proof.

The run history shows:

- the deterministic order input;
- the Formula Guard decision;
- the resulting allow/block outcome;
- the token savings from deterministic replay.

## Using Run History From `/demo`

Start the API:

```bash
uvicorn apps.api.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/demo
```

Use the controlled Human Recording flow to create, compile, inspect, and run the skill. After the proof run, `/demo` calls the run history and timeline endpoints and renders:

- the latest runs for the skill;
- the valid run decision;
- the invalid run decision;
- a preview of one audit timeline;
- the ordered step ids `load_skill`, `load_order`, `formula_guard`, and `produce_result`.

The same panel stays vanilla HTML and JavaScript.

## Tests Performed

Run History / Audit Timeline v0.5 added and preserved tests for:

- listing runs returning the executions of a skill;
- the run list including allow and block after executing twice;
- the timeline returning ordered steps;
- the timeline including `formula_guard`;
- the timeline proof including `has_guard_step = true`;
- the timeline proof including `decision_is_auditable = true`;
- missing skill returning a controlled error;
- missing run returning a controlled error;
- `/demo` containing `Run History / Audit Timeline v0.5`;
- health route;
- existing inspect, readiness, compile, and run behavior.

## Exact Pytest Result

The verification command is:

```bash
python -m pytest
```

Result for this evidence freeze:

```text
155 passed, 9 skipped
```

## Known Skips

The skipped tests are browser-dependent paths in this shell because Chromium/Playwright browser runtime availability is not active for the plain `python -m pytest` run.

The evidence artifact uses FastAPI `TestClient`; it does not require launching Chromium.

## Limitations

Run History / Audit Timeline v0.5 is intentionally narrow:

- it only exposes the controlled Fake ERP formula review replay path;
- it depends on the existing `SkillRun` and `SkillRunStep` records;
- it does not infer arbitrary user intent;
- it does not repair unknown run histories;
- it does not automate real ERP writes.

## No-Goals

This milestone did not add:

- real Odoo UI automation;
- MCP;
- LLM-based inspection or replay;
- browser extension capture;
- unrestricted/free recording;
- marketplace behavior;
- frontend framework;
- new run-history tables;
- real ERP write actions;
- architecture redesign.

It also did not change or break `POST /v1/demo/full-record-to-skill-flow`, `GET /v1/recordings/{recording_id}/readiness`, `GET /v1/skills/{skill_id}/inspect`, `GET /v1/skills/{skill_id}/runs`, `GET /v1/skills/{skill_id}/runs/{skill_run_id}/timeline`, `POST /v1/recordings/{recording_id}/compile-skill`, or `POST /v1/skills/{skill_id}/run`.

## Negative Evidence

The evidence artifact captures controlled negative responses for:

- `GET /v1/skills/missing-skill/runs` -> `skill_not_found`;
- `GET /v1/skills/{skill_id}/runs/missing-run/timeline` -> `skill_run_not_found`.

## Recommended Next Block

The next block should remain controlled and evidence-first.

Recommended next step:

```text
v0.6 Approval Gate / Safe Action Plan
```

That block could simulate a critical action plan, require approval before execution, and continue avoiding LLM, MCP, browser extension, real Odoo, free recording, marketplace, or real ERP write actions.
