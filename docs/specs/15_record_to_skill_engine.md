# 15 Record To Skill Engine Strategic Spec

**Status:** Strategic product spec
**Date:** May 18, 2026
**Relationship to ERP Agent OS:** Defines the hardest and most differentiated learning-to-execution module in the platform.
**Relationship to ERPGuard:** ERPGuard remains the mandatory safety kernel for critical UI actions, approval gates, and fail-closed execution.

## 1. Product Statement

Teach once, run safely forever.

The Record-to-Skill Engine lets a business user demonstrate a process once inside any ERP interface. ERP Agent OS records the interaction, understands the intent, generalizes constants into variables, compiles the process into a safe reusable UI skill, protects it with ERPGuard, and replays it later through a deterministic browser runtime with minimal or zero LLM tokens.

This is the product thesis behind durable UI automation in complex ERPs: humans should be able to show the system what they do, and the platform should convert that observed behavior into a tested, guarded, reusable skill.

## 2. Why This Is Hard

Screen recording alone is not enough.

A raw recording can replay clicks, but it does not reliably explain what the user was trying to do. In ERP systems, the same visible action can mean different things depending on the object, record state, form context, permissions, validation rules, or hidden dependencies. A useful skill engine must infer more than motion.

The system must determine:

- the user intent;
- stable selectors and fallback selectors;
- constants versus reusable variables;
- required preconditions;
- expected postconditions;
- allowed failure states;
- business rules that must be preserved;
- critical actions that require safety checks;
- how to verify that the UI state is the one expected before and after each step.

This is difficult because ERP interfaces are not uniform. One screen may be backed by a stable API, another by partial DOM, another by a virtualized table, another by an accessibility tree, and another by a highly dynamic page with modals, toasts, downloads, uploads, and context-sensitive controls. The engine must work across all of them without becoming brittle or unsafe.

The real challenge is not recording the steps. The challenge is converting one messy human demonstration into a reliable and auditable automation artifact that can be executed again with deterministic behavior.

## 3. Architecture

```text
Business user
-> Web App
-> Recording Session
-> Browser Event Recorder
-> DOM Snapshot Store
-> Screenshot Evidence Store
-> Intent Understanding Agent
-> UI Skill Compiler
-> ERPGuard Safety Kernel
-> Skill Registry
-> Deterministic Browser Runtime
-> Audit Trail
```

The architecture separates learning-time intelligence from execution-time determinism.

At recording time, the system captures evidence, interaction context, and state transitions.

At compile time, the system infers intent, abstractions, and reusable parameters.

At runtime, the system executes a vetted skill without requiring fresh LLM reasoning except for repair, explanation, or unknown-state handling.

## 4. Recording Session

The recording session is the evidence-capture layer for a single demonstrated process.

It must capture at least:

- URL;
- page title;
- DOM snapshot;
- accessibility tree;
- clicked element role, name, text, and selector;
- form fields;
- typed values;
- tables;
- screenshots before and after important actions;
- modals;
- downloads and uploads;
- visible errors;
- user annotations.

The recorder should also preserve timing and event ordering so the compiler can reconstruct the flow that occurred, not just the final page state.

The recording layer should be able to distinguish a navigation event, a data-entry event, a confirmation click, a modal dismissal, a file upload, and a visible validation error, because each of those has different safety and replay implications.

## 5. Generalization

The compiler must distinguish between observed values and reusable semantics.

It must classify:

- constants;
- variables;
- inputs;
- derived values;
- state assertions;
- business rules;
- critical actions.

Example:

```text
S00040 becomes {{order_reference}}.
```

In practice, the compiler should detect that `S00040` is not a fixed business requirement but an instance-specific value that should be parameterized. The same process may also contain stable business rules such as “the order must be in draft state before confirmation” or “the shipping address must exist before validation,” which should be encoded as assertions rather than treated as editable inputs.

Generalization should preserve meaning while removing accidental specificity. The goal is not to abstract everything. The goal is to keep the elements that define the process and parameterize the elements that vary across runs.

## 6. UI Skill Format

Each generated skill should be stored as a versioned package with explicit artifacts.

Generated files:

- `skill.yaml`;
- `workflow.yaml`;
- `selectors.yaml`;
- `guards.yaml`;
- `input_schema.json`;
- `output_schema.json`;
- `tests/`;
- `screenshots/`;
- `audit_config.yaml`;
- `mcp_tool_definition.json`.

The package should be self-describing. A reviewer must be able to inspect the skill definition, selectors, guard rules, input and output contracts, and evidence set without reading opaque runtime code.

The workflow definition should represent the logical process. The selector file should represent the UI mapping strategy. The guard file should represent safety rules, approval gates, and postcondition expectations. The test bundle should contain replay checks and negative cases. The audit configuration should define which evidence is stored for traceability.

## 7. Selector Strategy

Selector selection must be ordered by reliability and auditability.

Priority order:

1. native API if available;
2. DOM stable attributes;
3. ARIA role / accessible name;
4. label text;
5. visible text;
6. table/form structure;
7. screenshot vision;
8. coordinates as last resort only.

The selector engine should prefer semantics over geometry. Coordinates are brittle, environment-sensitive, and difficult to defend in audits, so they should only be used when no stable semantic selector exists.

Every step must include a Screen State Verifier entry with:

- expected page;
- expected record;
- expected visible state;
- expected result after action;
- failure states;
- screenshot evidence.

The verifier is not a luxury. It is the mechanism that prevents a replay from silently acting on the wrong record or an unexpected page state.

## 8. ERPGuard Integration

Critical UI actions must be wrapped by ERPGuard before activation and before execution.

Critical actions include:

- confirm;
- post;
- validate;
- pay;
- delete;
- change permissions;
- mark done.

R3+ actions require preflight and human approval.

The integration contract is simple: the UI skill may learn or propose an action, but ERPGuard decides whether it is safe to activate or execute. If the action is risky, ambiguous, or unauthorized, the skill must fail closed and stop.

## 9. Token Economics

The module must be economical with tokens.

Learning and compiling may use an LLM because those stages are infrequent and high-value. Repeated execution should use a deterministic Playwright runtime by default so that repeated business runs do not incur ongoing LLM cost.

LLM usage should be limited to:

- repair;
- explanation;
- modification;
- unknown screen state.

The long-term cost model is therefore:

- expensive once to learn and compile;
- cheap many times to execute;
- selective LLM use only when a deterministic path fails or the user changes the skill.

That cost structure is what makes Record-to-Skill materially different from generic chat-driven browser automation.

## 10. Repair Agent

When a selector fails or a screen state does not match the expected verifier, the Repair Agent may propose a patch.

The patch must not become active immediately.

Repair flow:

1. Detect failure.
2. Identify the local mismatch.
3. Ask the LLM to propose a patch.
4. Test the patch against the recorded evidence or a controlled replay.
5. Activate only after the patch passes verification.

This keeps the system from drifting into silent brittleness. A repair proposal is a candidate, not a permission slip.

## 11. MVP Plan

The initial MVP should use a local Fake ERP Web so the whole pipeline can be built and tested without risking real ERP data.

Fake ERP Web should include:

- sales order list;
- sales order detail;
- formula tab;
- valid formulas;
- invalid formulas.

Implement later:

- recording session;
- event capture;
- first compiled UI skill;
- deterministic replay;
- audit screenshots.

The Fake ERP Web should be intentionally small but representative enough to exercise the full record, compile, guard, and replay loop. The point is to prove the learning model and runtime architecture before extending to real ERP surfaces.

## 12. Non-Goals

This module explicitly does not aim to provide:

- unrestricted browser autonomy;
- coordinate-first RPA;
- silent critical actions;
- real payments;
- financial posting;
- replacement of API adapters when APIs are available.

The goal is a safe learning and replay system for ERP processes, not an unbounded browser agent.

## 13. Strategic Summary

The Record-to-Skill Engine is the most differentiated part of ERP Agent OS because it turns live human ERP behavior into a durable software asset.

It learns from demonstration, generalizes responsibly, protects risky steps with ERPGuard, stores evidence for auditability, and replays deterministically with low token cost. If the execution quality is good enough, a business user can teach a process once and trust the system to run it safely thereafter.