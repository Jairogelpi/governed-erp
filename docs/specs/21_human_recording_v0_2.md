# 21 Human Recording MVP v0.2

**Status:** Implementation spec for controlled human recording
**Date:** May 18, 2026
**Relationship to ERP Agent OS:** Extends the current MVP with a real user-driven capture path over the existing demo surface.
**Relationship to ERPGuard:** Keeps the recording path narrow, auditable, and compatible with the existing deterministic compile-and-run loop.

## Purpose

This document defines the next MVP block after the dashboard.

The goal is to move from a fully backend-driven demo flow to a controlled human recording flow where a person can perform the Fake ERP scenario themselves and the system captures that interaction as a structured `RecordingSession` plus `RecordingEvent` data.

This is still not the final ERP Agent OS recording system.
It is a narrow and safe v0.2 step that proves human-driven capture without introducing a browser extension, unrestricted recording, or any LLM-based interpretation.

The product loop remains:

Fake ERP Web
-> Human Recording
-> Recording Session
-> Recording-to-Skill Compiler
-> Skill Registry
-> Deterministic Skill Run
-> ERPGuard Formula Guard
-> token economics

## 1. Product Purpose

The purpose of v0.2 is to prove that a real human can drive the demonstration flow in the browser and the platform can capture that session as structured evidence.

This makes the MVP more believable for evaluation because the recording is no longer only produced by an automated demo routine.

## 2. User Journey

The expected journey is:

- user opens the demo surface
- user starts a recording session
- system opens or exposes the Fake ERP flow in a controlled browser context
- user clicks and types through the formula review path manually
- system stores the interaction as a recording session with ordered events
- user ends the recording
- user compiles the recording into a reusable skill
- user runs the skill deterministically with valid and invalid orders

## 3. Scope

The v0.2 human recording block should support only the Fake ERP formula review scenario at first.

Supported actions:

- open sales orders
- search an order by reference
- open a sales order
- open the formula tab
- review the formula
- capture URL, selector, input, and text snapshots
- finish the recording cleanly

The system should continue to reuse the existing deterministic compiler and runtime.

## 4. UI and API Shape

The recording experience may be surfaced through the current demo dashboard or a similarly thin operator page.

Suggested surfaces:

```text
GET /demo
POST /v1/recordings
POST /v1/recordings/{recording_id}/events
POST /v1/recordings/{recording_id}/finish
POST /v1/recordings/{recording_id}/compile-skill
```

The dashboard can initiate a recording session and then let the user interact with the Fake ERP flow while the system stores the captured evidence.

## 5. Data To Capture

The recording should store the same core evidence the MVP already uses:

- event type
- URL
- page title
- element role
- element text
- selector
- input value
- before text snapshot
- after text snapshot
- metadata needed to reconstruct the flow

The recording should remain structured and deterministic enough to compile into a reusable skill.

## 6. Safety and Scope

This block must remain controlled.

It must not:

- add a browser extension
- add unrestricted recording of arbitrary sites
- add LLM interpretation of user intent
- add MCP
- add real Odoo UI automation
- add write actions to real ERP systems
- add marketplace behavior

The first supported path should stay on the Fake ERP demo surface.

## 7. Technical Requirements

Prefer a minimal implementation that reuses the existing recording repository and compiler.

The block may add a small amount of UI glue if needed, but it should not duplicate the deterministic compiler or the skill runtime.

The implementation should keep the current contract of `RecordingSession` and `RecordingEvent` intact.

## 8. Expected Output

The recording flow should produce:

- a finished recording session
- ordered recording events
- a recording that can be compiled by the existing compiler
- a skill that can run deterministically
- allow/block proof for valid and invalid orders
- token economics with repeated execution cost at zero

## 9. Testing Expectations

The tests for this block should prove:

- a human-driven recording session can be started and finished
- recorded events persist in order
- the known Fake ERP formula review flow compiles successfully
- the compiled skill runs allow for `SO-VALID`
- the compiled skill runs block for `SO-FORMULA-MISMATCH`
- health and existing demo routes still work

## 10. Non-Goals

Do not include:

- browser extension capture
- free-form recorder for any website
- LLM-based step recovery
- MCP Gateway
- real Odoo UI
- SAP or other ERP adapters
- marketplace packaging
- production-grade session recovery

## 11. TFM Evaluation Angle

For the TFM, v0.2 can be evaluated as the first proof that a human can drive the loop manually while the system still captures structured evidence and keeps the repeat path deterministic.

Useful evaluation questions:

- can a human perform the demo without API-only orchestration?
- is the resulting recording structured enough to compile?
- does the compiled skill remain deterministic and auditable?
- does ERPGuard still block the invalid formula order?

## 12. Next Recommended Block

If this human recording step lands, the next block should focus on tightening the capture experience and making the recorder easier to teach and replay, not expanding to arbitrary UI automation.

The current direction after v0.2 should still favor small, controlled surfaces over broad generalization.