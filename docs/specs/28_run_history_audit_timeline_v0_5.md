# 28 Run History / Audit Timeline v0.5

**Status:** Implementation spec for Run History / Audit Timeline MVP
**Date:** May 19, 2026
**Baseline commits:** `28eb983`, `dbd5725`
**Relationship to Skill Inspector v0.4:** Adds execution history and step-level audit evidence for the compiled skill that Skill Inspector exposes.

## Purpose

Run History / Audit Timeline v0.5 lets the user inspect what happened when a compiled skill was executed.

Skill Inspector v0.4 answers "what did we compile?". Run History v0.5 answers "what happened when we ran it?".

This is useful because a compiled skill can be safe in structure but still needs visible execution evidence: when it ran, what decision it made, which steps ran, and whether the guard and result steps are auditable.

## Problem Solved Compared To Skill Inspector v0.4

Skill Inspector v0.4 exposes the skill package and its safety summary before execution.

Run History / Audit Timeline v0.5 exposes the actual runtime evidence after execution: one row per run and one ordered timeline per run.

That closes the evidence loop from recording -> readiness -> compile -> inspect -> run -> audit timeline.

## Endpoint Contract

The server exposes:

```http
GET /v1/skills/{skill_id}/runs
GET /v1/skills/{skill_id}/runs/{skill_run_id}/timeline
```

### Run List Response

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

### Timeline Response

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

- `skill_run_id`
- `skill_version_id`
- `status`
- `decision`
- `created_at`
- `finished_at`
- `input`
- `output_summary`
- `estimated_tokens_saved`

The timeline must surface:

- `skill_id`
- `skill_run_id`
- `status`
- `decision`
- ordered `timeline` step rows
- `proof`

## Relationship To SkillRun And SkillRunStep

Run History / Audit Timeline reuses the existing `SkillRun` and `SkillRunStep` persistence models.

It must not create a new table.

The run list is a projection of `SkillRun` records for a skill.
The timeline is an ordered projection of the `SkillRunStep` rows for a specific run.

## Relationship To ERPGuard Evidence

The run history is evidence because it shows the runtime decision trail:

- the skill version that executed;
- the user input used for the run;
- the guard decision;
- the resulting allow/block decision;
- the ordered step timeline;
- the token savings associated with deterministic replay.

This gives the user auditable proof that the compiled skill can be replayed without LLM use.

## Using Run History From `/demo`

After a compiled skill has been run, `/demo` should show:

- the latest runs for the skill;
- the valid run decision;
- the invalid run decision;
- a preview of at least one run timeline;
- the ordered step ids `load_skill`, `load_order`, `formula_guard`, and `produce_result`.

The UI must remain vanilla HTML and JavaScript.

## Expected Tests

Tests must prove:

- listing runs returns the executions of a skill;
- the run list includes allow and block after executing twice;
- the timeline returns ordered steps;
- the timeline includes `formula_guard`;
- the timeline proof includes `has_guard_step = true`;
- the timeline proof includes `decision_is_auditable = true`;
- a missing skill returns a controlled error;
- a missing run returns a controlled error;
- `/demo` contains `Run History / Audit Timeline v0.5`;
- `GET /health` still works;
- existing inspect, readiness, compile, and run behavior remains intact.

## No-Goals

Run History / Audit Timeline v0.5 must not add:

- real Odoo UI automation;
- MCP;
- LLM-based inspection or replay;
- browser extension capture;
- unrestricted recording of arbitrary websites;
- a new skill database table;
- marketplace behavior;
- a frontend framework;
- real ERP write actions;
- architecture redesign.

The scope remains the controlled Fake ERP formula review skill and its deterministic replay history.

## Acceptance Criteria

Run History / Audit Timeline v0.5 is accepted when:

- `GET /v1/skills/{skill_id}/runs` returns a readable execution summary for the skill;
- `GET /v1/skills/{skill_id}/runs/{skill_run_id}/timeline` returns the ordered audit timeline for a run;
- `/demo` shows the new run history section after the compiled skill is run;
- the UI shows the latest runs and one timeline preview;
- README and AGENTS are updated;
- `python -m pytest` passes, with browser-dependent skips documented if present;
- no LLM, MCP, browser extension, real Odoo UI, free recorder, marketplace, frontend framework, or real ERP write action is introduced.
