# 17 MVP Record To Skill Fake ERP

**Status:** Implementation spec for the first complete demo
**Date:** May 18, 2026
**Relationship to ERP Agent OS:** Defines the first buildable product loop for the platform.
**Relationship to ERPGuard:** ERPGuard validates the generated skill, the guard outcome, and the audit trail.

## Purpose

This document freezes the first buildable MVP.

The MVP must demonstrate the full loop:

Business user uses a fake ERP web interface
-> records a process once
-> system captures UI actions
-> compiles the recording into a reusable UI skill
-> ERPGuard validates the skill
-> skill is saved in Skill Registry
-> skill runs again deterministically without LLM
-> audit trail stores evidence
-> system reports estimated token savings

## 1. Fake ERP Web

Create a simple local web app with:

- sales order list;
- sales order detail page;
- formula tab;
- valid formula order;
- invalid formula order;
- search order field;
- review button;
- visible status/result area.

The fake ERP should be small, local, and predictable. It exists to prove the loop, not to simulate every real ERP feature.

## 2. Recorder MVP

Capture:

- URL;
- clicked elements;
- input values;
- element text;
- element role if available;
- screenshots optional for now;
- before/after page text snapshot.

The recorder only needs enough evidence to reconstruct the interaction deterministically and compile a first usable skill.

## 3. UI Skill Format

Define a minimal skill with:

- skill_id;
- name;
- inputs;
- steps;
- selectors;
- guards;
- audit config;
- llm_required_for_repeated_runs=false.

This skill format should stay intentionally small. The first goal is a dependable generated artifact, not a comprehensive skill standard.

## 4. Compiler MVP

Convert a recorded session into a deterministic skill:

- identify order reference as variable;
- convert clicks and fills into steps;
- add screen assertions;
- attach formula_guard.

The compiler should prefer direct, deterministic mappings over any speculative abstraction. If a value is reused across the recording and varies per run, it becomes a variable. If a page state must hold before or after an action, it becomes an assertion.

## 5. Runtime MVP

Run the compiled skill with Playwright:

- open Fake ERP;
- search order;
- open order;
- go to formula tab;
- extract formula values;
- run Formula Guard;
- produce allow/block result.

Runtime must be deterministic first. The repeated execution path should not depend on the LLM unless the system enters a repair or unknown-state path.

## 6. Skill Registry MVP

Endpoints:

- POST /v1/skills;
- GET /v1/skills;
- GET /v1/skills/{skill_id};
- POST /v1/skills/{skill_id}/run.

The registry should store the generated skill and expose it for listing, inspection, and deterministic execution.

## 7. Audit

Store:

- skill run id;
- step results;
- guard result;
- decision;
- timestamps;
- errors.

Audit must be enough to prove what was run, what happened at each step, and why the final decision was taken.

## 8. Token Economics

For the MVP:

- creation_token_cost_estimate;
- repeated_execution_token_cost=0;
- estimated_tokens_saved_per_run.

The user should be able to see that the expensive learning moment happens once and the repeat path is cheap.

## 9. Non-Goals

Do not include:

- real Odoo UI yet;
- browser extension yet;
- full visual AI;
- coordinate-based automation;
- critical writes;
- payment or accounting actions;
- marketplace.

The MVP is a controlled demo loop, not the final platform.

## 10. Acceptance Criteria

- user can run Fake ERP locally;
- at least one skill can be created from a predefined or recorded process;
- skill can be replayed deterministically;
- valid order returns allow;
- invalid order returns block;
- audit is retrievable;
- tests pass.

If all acceptance criteria are met, the first product thesis is proven: teach once, convert into a skill, execute cheaply, and audit everything.