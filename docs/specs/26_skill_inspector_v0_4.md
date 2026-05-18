# 26 Skill Inspector v0.4

**Status:** Implementation spec for Skill Inspector MVP
**Date:** May 19, 2026
**Baseline commits:** `10deeee`, `7345114`
**Relationship to Teach Mode v0.3:** Adds an audit view for the generated skill after a process has been taught and compiled.

## Purpose

Skill Inspector v0.4 lets an operator inspect the compiled skill before trusting, reusing, or running it.

Teach Mode v0.3 explains whether the recorded process is complete. Skill Inspector explains what the system created from that process: inputs, guards, deterministic workflow steps, source recording, runtime, and safety summary.

## Problem Solved Compared To Teach Mode v0.3

Teach Mode answers:

```text
Did the user teach the required process steps?
```

Skill Inspector answers:

```text
What reusable skill was created from those steps, and is it safe to replay deterministically?
```

This helps the user audit the generated skill package without opening the database or reading raw API responses.

## Inspection Contract

The API exposes:

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

If the skill does not exist, return the existing controlled `skill_not_found` error. If the skill exists but has no version, return `skill_version_not_found`.

## Visible Fields

The inspector must expose:

- skill id;
- skill name;
- latest version id;
- runtime type;
- LLM replay requirement;
- declared inputs;
- guards;
- workflow steps;
- source recording id;
- safety summary.

## Relationship With Skill Registry

Skill Inspector must reuse the existing Skill Registry.

It must not create new tables or duplicate skill storage. It reads the existing `Skill` row, resolves the latest `SkillVersion`, parses `skill_package_json`, and projects that data into an inspection response.

## Relationship With Compiled Skill Package

The inspector is a read-only view over the compiled skill package.

For the current Fake ERP formula review skill, the package contains:

- `inputs`;
- `guards`;
- `workflow`;
- `compiled_from_recording_id`;
- `llm_required_for_repeated_runs`.

The inspector renames `workflow` to `workflow_steps` for clarity and derives `safety_summary` from the package and latest version metadata.

## Expected Tests

Tests must prove:

- inspecting a valid skill returns `200`;
- the response includes `workflow_steps`;
- the response includes `formula_guard`;
- `safety_summary.has_write_actions = false`;
- `safety_summary.requires_llm_for_replay = false`;
- inspecting a missing skill returns a controlled error;
- `/demo` contains `Skill Inspector v0.4`;
- health still works;
- existing compile/run behavior still passes.

## No-Goals

This block must not add:

- real Odoo UI automation;
- MCP;
- LLM interpretation or repair;
- browser extension capture;
- unrestricted/free recording;
- marketplace behavior;
- frontend framework;
- real ERP write actions;
- new database tables;
- architecture redesign;
- changes to `POST /v1/demo/full-record-to-skill-flow`;
- changes to `GET /v1/recordings/{recording_id}/readiness`;
- breaking changes to compile-skill.

## Acceptance Criteria

Skill Inspector v0.4 is accepted when:

- `GET /v1/skills/{skill_id}/inspect` returns the contracted inspection response;
- the endpoint reads existing Skill Registry data and latest `SkillVersion`;
- `/demo` renders the inspector after compiling a human recording;
- existing compile and run paths keep working;
- README and AGENTS are updated;
- `python -m pytest` passes, with browser-dependent skips documented if present;
- no LLM, MCP, browser extension, real Odoo UI, free recorder, marketplace, frontend framework, new persistence model, or real ERP write action is introduced.
