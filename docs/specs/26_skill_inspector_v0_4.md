# 26 Skill Inspector v0.4

**Status:** Implementation spec for Skill Inspector MVP
**Date:** May 19, 2026
**Baseline commits:** `10deeee`, `7345114`
**Relationship to Teach Mode v0.3:** Adds an inspection surface for the compiled skill created by the controlled Fake ERP teaching flow, without expanding automation scope.

## Purpose

Skill Inspector v0.4 lets the user inspect the generated skill package before trusting it for repeated use, and inspect it again after execution if desired.

It exposes the compiled skill as a readable safety artifact: the skill name, version, runtime type, inputs, guards, workflow steps, recording provenance, and a short safety summary.

## Problem Solved Compared To Teach Mode v0.3

Teach Mode v0.3 explains whether the recording is ready to compile.

Skill Inspector v0.4 explains what was actually compiled.

That matters because readiness proves the recording is complete, but it does not show the user the final reusable skill package they are about to run. Inspector closes that gap by making the compiled workflow visible and by surfacing the safety properties of the generated skill.

## Inspection Contract

The server exposes:

```http
GET /v1/skills/{skill_id}/inspect
```

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

The response is derived from the latest `SkillVersion` and its stored `skill_package_json`.

## Visible Fields

The inspector must surface:

- `skill_id`
- skill `name`
- latest `version_id`
- `runtime_type`
- `llm_required_for_repeated_runs`
- `inputs`
- `guards`
- `workflow_steps`
- `compiled_from_recording_id`
- `safety_summary`

`workflow_steps` should expose the deterministic workflow compiled from the recording, including the guard step.

## Relationship To Skill Registry

Skill Inspector reuses the existing Skill Registry.

It must not create a new persistence table or a new skill model.

It reads the skill row and then the latest `SkillVersion`. If the skill or version is missing, the endpoint returns a controlled error response.

## Relationship To Compiled Skill Package

The inspector is a read-only projection of the compiled skill package.

The compiler still owns package creation. Inspector only parses `skill_package_json` and reformats it for inspection.

The current compiled package is the Fake ERP formula review workflow with `inputs`, `guards`, `workflow`, `llm_required_for_repeated_runs`, and `compiled_from_recording_id`.

## Expected Tests

Tests must prove:

- inspecting a valid skill returns `200`;
- the inspection payload includes `workflow_steps`;
- the inspection payload includes `formula_guard`;
- `safety_summary.has_write_actions` is `false`;
- `safety_summary.requires_llm_for_replay` is `false`;
- inspecting a missing skill returns a controlled error;
- `/demo` contains `Skill Inspector v0.4`;
- `GET /health` still works;
- existing compile and run behavior remains intact;
- the full demo flow endpoint still works.

## No-Goals

Skill Inspector v0.4 must not add:

- real Odoo UI automation;
- MCP;
- LLM-based inspection or repair;
- browser extension capture;
- unrestricted recording of arbitrary websites;
- a new skill database table;
- marketplace behavior;
- a frontend framework;
- real ERP write actions;
- architecture redesign.

The scope remains the controlled Fake ERP skill created by the current recording-to-skill pipeline.

## Acceptance Criteria

Skill Inspector v0.4 is accepted when:

- `GET /v1/skills/{skill_id}/inspect` returns the contracted shape from the latest skill version;
- the endpoint is implemented as a read-only view over the existing Skill Registry;
- `/demo` shows a Skill Inspector v0.4 section after compilation;
- the inspector renders inputs, guards, workflow steps, no-LMM-required, and the safety summary;
- README and AGENTS are updated;
- `python -m pytest` passes, with browser-dependent skips documented if present;
- no LLM, MCP, browser extension, real Odoo UI, free recorder, marketplace, frontend framework, or real ERP write action is introduced.
