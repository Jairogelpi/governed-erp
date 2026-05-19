# Operator Demo Script v0.7

## Goal

Show the evaluator a controlled MVP story, not a promise of full ERP automation.

## Start The API

Run:

```bash
uvicorn apps.api.main:app --reload
```

Say:

"I am starting the controlled ERPGuard demo API."

## Open The Demo Page

Open:

```text
http://127.0.0.1:8000/demo
```

Say:

"This page is a guided demo surface over the backend MVP."

## What To Click

1. Run full demo.
2. Show the Human Recording section.
3. Show Teach Mode readiness.
4. Show Skill Inspector.
5. Show Run History / Audit Timeline.
6. Show Approval Gate / Safe Action Plan.
7. Show Approval Decision Simulation.

## What To Explain

- Human Recording: "A controlled recording of the Fake ERP formula review flow."
- Teach Mode: "A checklist that shows whether the recording is ready to compile."
- Skill Inspector: "The compiled skill package and its safety summary."
- Run History / Audit Timeline: "The auditable proof of what happened when the skill ran."
- Approval Gate: "A dry-run plan for a critical action that still blocks real ERP writes."
- Approval Decision Simulation: "A simulated approve/reject decision over the safe plan, without executing the ERP action."

## What To Show The Evaluator

- The demo works from one controlled Fake ERP flow.
- The run result is deterministic.
- The audit trail is visible.
- The safe plan marks the critical action as approval-required.
- The simulation records approve/reject evidence only.

## What Not To Promise

Do not say this already does any of the following:

- automate a real Odoo UI;
- execute real ERP writes;
- provide a real approval workflow;
- replace manual business judgment;
- support every ERP or every screen.

## If Asked: "Does This Already Work With Real Odoo?"

Answer:

"No. This version is still the controlled Fake ERP MVP. It proves the record-to-skill and safety story, but it does not yet write to real Odoo."

## If Asked: "What Is The Point Of v0.7?"

Answer:

"v0.7 is the last safety demonstration before real integration: it shows planning, approval requirement, and simulated approval evidence without performing an ERP write."

## Close

End with:

"The value here is the controlled demo and the audit story. Real ERP integration should be a separate phase after consolidation."
