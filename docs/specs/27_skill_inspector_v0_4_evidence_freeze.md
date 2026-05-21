# 27 Skill Inspector v0.4 Evidence Freeze

**Status:** Evidence and documentation freeze
**Date:** May 19, 2026
**Baseline commit:** `28eb983 feat: add skill inspector v0.4`
**Evidence artifact:** `docs/demo/skill_inspector_v0_4_success_response.json`

## Purpose

This document freezes the Skill Inspector v0.4 evidence state after the read-only inspection endpoint and `/demo` integration were added.

This block is documentation and evidence only. It does not expand runtime scope, ERP coverage, automation capability, or UI architecture.

## Exact Skill Inspector v0.4 State

Skill Inspector v0.4 is a read-only inspection layer over the existing Skill Registry.

It includes:

- `GET /v1/skills/{skill_id}/inspect`;
- read-only loading of the latest `SkillVersion`;
- parsing of `skill_package_json` from the compiled skill package;
- visible `inputs`, `guards`, `workflow_steps`, and `compiled_from_recording_id`;
- a `safety_summary` block with guard and replay safety flags;
- `/demo` rendering of the Skill Inspector v0.4 section after compilation and after proof runs.

## Problem Solved Compared To Teach Mode v0.3

Teach Mode v0.3 explains whether the recording is ready to compile.

Skill Inspector v0.4 explains what was compiled into the reusable skill.

That matters because readiness proves the recording is complete, but it does not show the final skill package, the workflow steps, or the safety properties of the compiled artifact. Inspector closes that gap without adding LLM interpretation, broader automation, or real ERP execution.

## Inspection Endpoint

The endpoint is:

```http
GET /v1/skills/{skill_id}/inspect
```

It loads the skill row, then the latest `SkillVersion`, and then parses `skill_package_json` into the inspection response.

If the skill is missing, the endpoint returns a controlled `skill_not_found` response.

If the skill exists but has no version, the endpoint returns a controlled `skill_version_not_found` response.

## Inspection Response Contract

The response shape is:

```json
{
  "skill_id": "skill_...",
  "name": "Recorded Fake ERP Formula Review",
  "version_id": "skill_version_...",
  "runtime_type": "deterministic_browser",
  "llm_required_for_repeated_runs": false,
  "inputs": {"order_reference": "string"},
  "guards": ["formula_guard"],
  "workflow_steps": [
    {"id": "open_orders", "type": "navigate"},
    {"id": "search_order", "type": "fill"},
    {"id": "open_order", "type": "click"},
    {"id": "open_formula", "type": "click"},
    {"id": "review_formula", "type": "click"},
    {"id": "run_formula_guard", "type": "guard"}
  ],
  "compiled_from_recording_id": "recording_...",
  "safety_summary": {
    "has_guards": true,
    "guard_count": 1,
    "has_write_actions": false,
    "requires_llm_for_replay": false
  }
}
```

## Visible Fields

The inspector must surface:

- `skill_id`;
- skill `name`;
- latest `version_id`;
- `runtime_type`;
- `llm_required_for_repeated_runs`;
- `inputs`;
- `guards`;
- `workflow_steps`;
- `compiled_from_recording_id`;
- `safety_summary`.

`workflow_steps` exposes the deterministic workflow compiled from the recording, including the `formula_guard` step.

## Safety Summary

The `safety_summary` block communicates the most important replay safety facts in one place:

- `has_guards` says whether the compiled skill includes guards;
- `guard_count` reports how many guards are present;
- `has_write_actions` stays `false` for the current controlled Fake ERP flow;
- `requires_llm_for_replay` stays `false` for deterministic repeated runs.

## Relationship To Skill Registry

Skill Inspector reuses the existing Skill Registry.

It does not create a new persistence table or a new skill model.

It reads the skill row and then the latest `SkillVersion`, so the inspector is always a projection of the stored registry state rather than a separate source of truth.

## Relationship To Compiled Skill Package

The inspector is a read-only projection of the compiled skill package.

The compiler still owns package creation. Inspector only parses `skill_package_json` and reformats it for inspection.

The current compiled package is the Fake ERP formula review workflow with `inputs`, `guards`, `workflow`, `llm_required_for_repeated_runs`, and `compiled_from_recording_id`.

## Using Skill Inspector From `/demo`

Start the API:

```bash
uvicorn apps.api.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/demo
```

Use the controlled Human Recording flow to create and compile a skill. After compilation, `/demo` calls the inspection endpoint and renders:

- inputs;
- guards;
- workflow steps;
- no-LLM-required status;
- safety summary.

The same panel refreshes again after the proof run so the user can inspect the compiled skill before and after execution.

## Tests Performed

Skill Inspector v0.4 added and preserved tests for:

- inspecting a valid skill returning `200`;
- `workflow_steps` visibility;
- `formula_guard` visibility;
- `safety_summary.has_write_actions = false`;
- `safety_summary.requires_llm_for_replay = false`;
- inspecting a missing skill returning a controlled error;
- inspecting a skill without a latest version returning a controlled error;
- `/demo` containing `Skill Inspector v0.4`;
- health route;
- existing compile and run behavior;
- the full demo flow endpoint.

## Exact Pytest Result

The verification command is:

```bash
python -m pytest
```

Result for this evidence freeze:

```text
151 passed, 9 skipped
```

## Known Skips

The skipped tests are browser-dependent paths in this shell because Chromium/Playwright browser runtime availability is not active for the plain `python -m pytest` run.

The evidence artifact uses FastAPI `TestClient`; it does not require launching Chromium.

## Limitations

Skill Inspector v0.4 is intentionally narrow:

- it only inspects the latest compiled skill version;
- it only supports the controlled Fake ERP formula review flow;
- it depends on the compiled skill package stored in the registry;
- it does not infer arbitrary user intent;
- it does not repair unknown skill packages;
- it does not automate real ERP writes.

## No-Goals

This milestone did not add:

- real Odoo UI automation;
- MCP;
- LLM-based inspection or repair;
- browser extension capture;
- unrestricted/free recording;
- marketplace behavior;
- frontend framework;
- new skill tables;
- real ERP write actions;
- architecture redesign.

It also did not change or break `POST /v1/demo/full-record-to-skill-flow`, `GET /v1/recordings/{recording_id}/readiness`, `GET /v1/skills/{skill_id}/inspect`, `POST /v1/recordings/{recording_id}/compile-skill`, or `POST /v1/skills/{skill_id}/run`.

## Recommended Next Block

The next block should keep the current controlled evidence-first direction.

Recommended next step:

```text
v0.5 Run History / Audit Timeline
```

That block could show the full execution history for a compiled skill as auditable evidence, without adding LLM, MCP, browser extension, real Odoo, free recording, marketplace, or real ERP write actions.
