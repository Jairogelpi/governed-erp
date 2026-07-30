# ERPGuard Evolution capability reality matrix

**Baseline:** `e483f5c5f272139c65a02ebc32ab11f5e323b6a4`  
**Inventory date:** 2026-07-30 (Phase 18.1 working tree)

The labels below are evidence labels, not marketing claims:

- `real`: implemented and exercised against the repository’s current runtime or controlled local persistence.
- `staging_only`: allowed only in an explicitly controlled staging path.
- `fixture`: operates on fixed or synthetic data.
- `simulated`: models a future behavior without performing it.
- `advisory`: produces review information but does not authorize an effect.
- `planned`: specified but not implemented.
- `blocked`: intentionally prevented by a safety boundary.

| Capability | Reality label | Baseline evidence / boundary |
| --- | --- | --- |
| FastAPI health and API surface | `real` | Existing API and health tests. |
| SQLAlchemy persistence | `real` | Existing model/repository/API tests; SQLite-compatible baseline. |
| Canonical ERP object mapping | `real` | Canonical model and adapter tests. |
| Formula Guard and preflight | `real` | Existing policy, preflight and audit tests. |
| Skill registry/versioning | `real` | Existing skill registry, versioning and inspector tests. |
| Recording-to-skill compiler | `real` | Controlled Fake ERP recording/compiler tests. |
| Deterministic Fake ERP runtime | `fixture` | Runs against the Fake ERP surface and local records. |
| Approval planning and decision simulation | `simulated` / `advisory` | Produces safe plans and decisions; does not perform real ERP confirmation. |
| Operator action governance | `advisory` / `blocked` | Planning, validation and audit exist; real ERP writes remain disabled. |
| Odoo connection/diagnosis foundations | `staging_only` | Read-only adapter and controlled diagnosis paths exist; live availability depends on configured staging. |
| Odoo business reads | `staging_only` | Allowlisted read mappings exist; not a general Odoo model/query API. |
| Odoo quotation draft creation | `staging_only` | Bounded real `sale.order.create`, idempotent client reference and draft-state postcondition; no generic RPC. |
| Odoo order confirmation | `staging_only` / `blocked_by_default` | Bounded real `sale.order.action_confirm` behind independent approval, signed one-use permit, staging/amount gates and a false-by-default feature flag. |
| Confirmation side-effect budget | `real` | Versioned effects and model creation ceilings are evaluated against before/after snapshots. |
| Confirmation automation fingerprint | `staging_only` | Bounded read-only module, automation, field, permission and configuration signals; incomplete inspection blocks. |
| Confirmation compensation execution | `advisory` | Typed plan and manual staging runbook; no public cancellation, credit-note or generic compensation capability. |
| Phase 17 live staging outcome | `real_failure_evidence` | Unexpected posted invoice exceeded budget; run remained failed; authorized manual compensation preserved accounting evidence and net effect zero. |
| Process event ingestion/OCEL | `planned` | Master spec Phase 6; not implemented by Phase 0. |
| Variant discovery | `planned` | Master spec Phase 10; not implemented by Phase 0. |
| Historical replay | `real` | Persisted replay runs/cases and regression coverage exist. |
| Proof of Improvement | `real` | Persisted proof artifacts and decision-coverage gates exist. |
| Process-to-Skill compiler v2 | `real` | Approved candidate/proof compilation and governed write checks exist. |
| Signed single-use execution permits | `real` | Tenant-bound plans, approvals, signatures, expiry, one-use enforcement and Evidence Packs exist. |
| Shadow candidate evaluation | `real` / `no_effects` | Eligible submitted candidates are compared with the active definition on identical cases; differences, observed outcomes and reviews are append-only. No connector or execution runtime is reachable. |
| Operational shadow feed | `real` / `no_effects` | Canonical event ingestion projects affected cases into matching shadow deployments with persisted trace provenance and trace-derived idempotency. |
| Shadow outcome reconciliation | `real` / `advisory` | Later outcomes are append-only, explicitly sourced and optionally linked to same-case canonical events. |
| Canary eligibility metrics | `advisory` / `blocked` | Operational coverage, agreement, decisions, reviews, outcomes, safety labels, window and confidence intervals produce a recommendation only. |
| Canary, activation, promotion and rollback | `planned` / `blocked` | Explicitly outside Phase 18; meeting an agreement threshold does not change routing or active versions. |
| Identity and tenant enforcement | `planned` | Master spec Phase 3; incomplete at baseline. |
| PostgreSQL/Alembic migration foundation | `planned` | Master spec Phase 2; absent from Phase 0 baseline. |
| Autonomous promotion, marketplace, second ERP connector, generic MCP | `blocked` | Explicit non-goals for the TFM path. |

## Safety invariant

No capability in this matrix authorizes an agent to call a raw ERP method. Any future effectful operation must remain behind the ERPGuard safety kernel and receive its own phase evidence.

