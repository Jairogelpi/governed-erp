# 19 MVP v0.1 Technical Freeze

**Status:** Technical milestone freeze
**Date:** May 18, 2026
**Product parent:** ERP Agent OS
**Kernel:** ERPGuard
**MVP:** Record-to-Skill Fake ERP demo with deterministic replay and Formula Guard

## 1. Purpose

This document freezes the MVP v0.1 technical milestone.

The goal is to define exactly what has been proven, what remains intentionally out of scope, how the MVP supports the TFM thesis, and what the next implementation block should be.

This is not a new strategic spec. It is a technical closure document for the first working end-to-end MVP.

## 2. MVP v0.1 Summary

MVP v0.1 demonstrates the following loop:

```text
Fake ERP Web
-> Browser Recorder
-> Recording Session
-> Recording-to-Skill Compiler
-> Skill Registry
-> Deterministic Skill Run
-> ERPGuard Formula Guard
-> token economics
-> evidence JSON
```

The known-good real browser run is stored at:

```text
docs/demo/full_record_to_skill_success_response.json
```

The latest verified test result through the repository virtual environment is:

```text
139 passed
```

## 3. What The MVP Does

MVP v0.1 proves that ERP Agent OS can:

1. expose a deterministic Fake ERP Web surface;
2. use Playwright Chromium to execute a controlled browser flow;
3. record the UI interaction as structured `RecordingSession` and `RecordingEvent` data;
4. compile the recording into a reusable skill package;
5. store the compiled skill in the Skill Registry;
6. execute the skill through a deterministic non-LLM runtime;
7. run ERPGuard Formula Guard against canonical ERP data;
8. return `allow` for a valid order;
9. return `block` for an invalid formula order;
10. report repeated execution token cost as zero;
11. persist auditable run and step data;
12. produce a JSON evidence artifact for the full demo.

## 4. What The MVP Proves Against The Product Thesis

The product thesis is:

> A business user should be able to teach an ERP process once, convert that process into a safe reusable skill, and rerun it later with minimal or zero LLM token cost.

MVP v0.1 supports that thesis in a constrained but concrete environment.

It proves:

- browser interaction can be captured as structured events;
- captured events can be compiled into a reusable skill;
- the skill can be replayed deterministically;
- repeated execution does not require an LLM;
- business invariants can block invalid ERP data;
- the system can produce auditable evidence of decisions;
- token economics can be surfaced as part of the execution report.

## 5. What The MVP Does Not Yet Prove

MVP v0.1 intentionally does not prove:

- free-form human recording;
- a browser extension;
- unrestricted computer-use automation;
- LLM-based intent understanding;
- MCP Gateway exposure;
- real Odoo UI automation;
- real Odoo write actions;
- SAP, Dynamics, NetSuite, or ERPNext adapters;
- marketplace packaging;
- production-grade multi-tenant security;
- production-grade secret management;
- Alembic migrations;
- exact financial ROI calculation;
- human approval workflow for critical writes.

These are future phases, not failures of the current milestone.

## 6. Implemented Technical Components

The MVP v0.1 codebase includes:

- FastAPI backend;
- Fake ERP Web routes;
- canonical ERP models;
- FakeERPAdapter;
- read-only Odoo adapter skeleton;
- Formula Guard invariant logic;
- policy engine;
- preflight API;
- connection API;
- audit retrieval API;
- Skill Registry;
- deterministic Skill Run endpoint;
- Playwright browser runtime for Fake ERP;
- Recording Session API;
- Recording-to-Skill Compiler MVP;
- Browser Recorder MVP for Fake ERP;
- full MVP Demo Orchestrator endpoint;
- known-good demo evidence JSON.

## 7. Key Endpoint For The Demo

The end-to-end demo endpoint is:

```http
POST /v1/demo/full-record-to-skill-flow
```

It executes:

```text
demo recorder
-> compile skill
-> run skill with SO-VALID
-> run skill with SO-FORMULA-MISMATCH
-> return consolidated proof
```

The expected output properties are:

```text
status = success
recording.status = finished
recording.event_count = 5
runs.valid.decision = allow
runs.invalid.decision = block
runs.invalid.issues_count = 1
token_economics.repeated_execution_token_cost = 0
proof.record_to_skill = true
proof.deterministic_replay = true
proof.erpguard_blocked_invalid_order = true
proof.no_llm_used_for_repeated_runs = true
```

## 8. Evidence Artifact

The known-good response file contains:

```text
recording finished with 5 events
skill compiled successfully
SO-VALID -> allow
SO-FORMULA-MISMATCH -> block
issues_count = 1
repeated_execution_token_cost = 0
proof.erpguard_blocked_invalid_order = true
proof.no_llm_used_for_repeated_runs = true
```

Evidence file:

```text
docs/demo/full_record_to_skill_success_response.json
```

## 9. TFM Evaluation Angle

For the TFM, MVP v0.1 can be evaluated around the following hypothesis:

> Separating the learning/compilation phase from the execution phase allows ERP automations to be created from interface demonstrations while keeping repeated execution deterministic, auditable, and low-cost in LLM tokens.

Suggested measurable criteria:

- valid order correctly allowed;
- invalid formula order correctly blocked;
- no LLM required for repeated deterministic execution;
- recording event count and step evidence stored;
- skill generated from recorded flow;
- deterministic skill run persisted;
- token economics surfaced;
- full demo repeatable through one endpoint;
- tests pass in the repository virtual environment.

## 10. Technical Risks Remaining

Important remaining risks:

1. **Recorder generalization risk**

   The current browser recorder is deterministic and demo-specific. Free-form recording will require robust event capture, selector stabilization, and user intent annotation.

2. **Compiler generalization risk**

   The current compiler only supports the Fake ERP formula review flow. General UI-to-skill compilation requires flow classification, variable inference, preconditions, postconditions, and unsupported-flow detection.

3. **Selector fragility risk**

   The current Fake ERP uses stable `data-testid` selectors. Real ERP interfaces may require role/label/text/accessibility fallback strategies.

4. **Security risk**

   The MVP is read-only and formula-validation oriented. Critical actions such as confirm, post, pay, delete, validate, or change permissions must require ERPGuard preflight and human approval.

5. **Persistence risk**

   The MVP uses SQLAlchemy metadata creation for simplicity. Production will require Alembic migrations and stricter database lifecycle management.

6. **Token economics risk**

   Token economics are currently hardcoded. Later versions should calculate actual creation, repair, explanation, and repeated execution savings.

7. **Real ERP integration risk**

   The Fake ERP flow proves the architecture. Real Odoo and other ERP UIs will require authentication, session handling, permissions, custom fields, and error screens.

## 11. Next Functional Block Recommendation

The next functional block should be a minimal demo dashboard, not another backend architecture expansion.

Recommended endpoint/surface:

```text
GET /demo
```

Purpose:

```text
show one button -> run full MVP demo
show recording_id
show skill_id
show valid decision = allow
show invalid decision = block
show tokens saved
show proof flags
```

This makes the MVP easier to present to non-technical stakeholders and TFM evaluators.

## 12. Explicit Stop Rules After v0.1

Do not start these before the demo dashboard or a clear v0.2 plan:

- LLM builder;
- MCP Gateway;
- real Odoo UI automation;
- browser extension;
- unrestricted user recording;
- marketplace;
- SAP/Dynamics/NetSuite adapters;
- critical ERP write actions;
- payment/accounting/posting automation.

## 13. v0.1 Conclusion

MVP v0.1 is a defensible technical milestone.

It demonstrates the core product loop:

```text
record ERP-like browser process
-> compile to skill
-> replay deterministically
-> apply ERPGuard
-> block invalid business data
-> report zero repeated LLM token cost
```

This is enough to support the first TFM proof-of-concept and to justify the next product step: a simple operator-facing demo dashboard.
