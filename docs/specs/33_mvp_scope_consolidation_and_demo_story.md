# 33 MVP Scope Consolidation and Demo Story

**Status:** Consolidation and narrative spec
**Date:** May 19, 2026
**Baseline commits:** `b3608f3`, `b615ad4`
**Relationship to v0.7:** Freezes the current MVP story and separates the product core from the simulated safety layers.

## Purpose

This document consolidates the current MVP into a simple, defensible story.

It does not add features. It explains what already exists, what is simulated for the demo, and why the current scope is the right stopping point before any real Odoo integration.

## Simple MVP Narrative

The current demo story is:

```text
record -> readiness -> compile -> inspect -> run -> audit -> safe plan -> simulated decision
```

That is the full visible loop today.

A user can teach the Fake ERP formula-review process once, compile it into a reusable skill, inspect the package before trusting it, run it deterministically, audit what happened, preview a critical action plan, and simulate a human approval decision without executing ERP writes.

## Core MVP Vs Demonstration Layers

### Core MVP

The core MVP is the part that proves the architecture works end to end:

- Fake ERP recording;
- readiness analysis;
- skill compilation;
- skill inspection;
- deterministic run execution;
- run history and timeline evidence.

These pieces demonstrate a controlled record-to-skill loop with auditable results.

### Demonstration Layers

The demonstration layers are the safety-story extensions around the core loop:

- Approval Gate / Safe Action Plan v0.6;
- Approval Decision Simulation v0.7;
- `/demo` narrative panels and operator-facing guidance;
- frozen JSON evidence artifacts.

These layers are useful for explaining safety, but they are not real ERP execution.

## What Is Real Today

The repository already provides working backend behavior for:

- recording the controlled Fake ERP formula review flow;
- validating readiness through compiler-compatible analysis;
- compiling a skill package from the recording;
- inspecting the compiled skill package;
- running the skill deterministically;
- listing run history and timeline evidence;
- previewing a critical action plan;
- simulating approval decisions as evidence only.

This is a real MVP in the sense that it runs, persists the core skill and run evidence, and passes the test suite.

## What Is Simulated Today

The following parts are intentionally simulated:

- the critical action planning for `confirm_sales_order`;
- the human approval decision;
- the approval evidence response;
- the narrative from plan to decision.

These simulation layers exist to prove safety boundaries, not to execute ERP writes.

## What Is Not Implemented Yet

The repository still does not have:

- real Odoo UI automation;
- real Odoo writes;
- a real approval workflow;
- approval persistence tables;
- browser-extension capture;
- MCP;
- LLM-based planning or repair;
- marketplace behavior;
- a frontend framework;
- broad ERP adapter coverage;
- production-grade security hardening for multi-tenant use.

## Why v0.7 Is The Functional Stop Point

v0.7 is the correct place to stop functional growth for this demo because the project already proves the important chain:

- a process can be recorded;
- the recording can be compiled into a skill;
- the skill can be inspected before use;
- the skill can be executed deterministically;
- execution history can be audited;
- the critical action can be planned safely;
- the approval decision can be simulated without writes.

Beyond this point, new features start to look like a platform expansion rather than a defendable MVP.

That is the moment to consolidate the story, not multiply surface area.

## Demo Story Structure

The demo should be presented as three layers:

- **Layer 1: Core automation** - record, compile, inspect, run, audit;
- **Layer 2: Safety planning** - preview a critical action and show Formula Guard before execution;
- **Layer 3: Safety simulation** - simulate approve or reject as evidence only.

This structure makes it clear which parts are product capability and which parts are safety narration.

## Recommended Next Steps

Do not implement new functional automation yet.

Recommended next steps are:

- freeze the v0.7 evidence state;
- keep the MVP demo explainable and stable;
- prepare a concise evaluator walkthrough;
- collect TFM documentation and screenshots;
- decide later whether Odoo real integration is worth a separate phase.

## No-Goals

This consolidation spec does not add:

- new endpoints;
- new tables;
- new schemas;
- new runtime behavior;
- real Odoo integration;
- approval persistence;
- extra ERP adapters;
- LLM features;
- MCP features;
- browser extensions;
- marketplace features;
- a frontend framework.

It exists to stop scope drift and make the MVP easy to defend.

## Acceptance Criteria

This consolidation is accepted when:

- the README tells a simple, accurate story;
- the operator demo script can be followed without interpretation gaps;
- the boundary document clearly separates real MVP behavior from simulations;
- the current test suite remains green;
- the repository reads as a controlled MVP, not an open-ended platform roadmap.
