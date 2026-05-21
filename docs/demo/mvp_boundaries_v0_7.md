# MVP Boundaries v0.7

## What Exists

- Fake ERP recording for the controlled formula review flow.
- Readiness analysis that tells whether the recording is ready to compile.
- Skill compilation into a reusable package.
- Skill inspection with workflow and safety summary.
- Deterministic skill runs for the recorded flow.
- Run history and audit timeline endpoints.
- Safe action planning for `confirm_sales_order`.
- Approval decision simulation for approve/reject evidence.
- `/demo` panels that surface the flow end to end.

## What Is Simulated

- The critical action plan for `confirm_sales_order`.
- The approval decision.
- The approval evidence response.
- The narrative that connects planning to decision.

## What Does Not Exist

- Real Odoo UI automation.
- Real Odoo writes.
- A real approval workflow.
- Approval persistence tables.
- Browser-extension capture.
- MCP.
- LLM-based decisioning or repair.
- Marketplace publishing.
- A frontend framework.
- Broad ERP adapter coverage.
- Free-form recorder behavior.

## Technical Risks Still Pending

- The current recording flow is still demo-specific.
- The compiler only knows the Fake ERP formula review path.
- The approval story is simulated, not operational.
- The safety layers prove the concept, but they do not yet integrate with real ERP state transitions.
- Real ERP permissions, edge cases, and session handling remain unproven.

## Recommended Decision

Freeze the functional scope here before any real Odoo work.

The current repository is strong enough for a TFM demo and evidence package, but not yet a justification for broadening into full ERP automation.

If real Odoo integration is pursued later, it should be a separate phase with a smaller scope and new acceptance criteria.
