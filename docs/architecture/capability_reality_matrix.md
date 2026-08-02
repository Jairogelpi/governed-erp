# ERPGuard Evolution capability reality matrix

**Phase 0 baseline:** `e483f5c5f272139c65a02ebc32ab11f5e323b6a4`

**Inventory date:** 2026-08-02

**Current implementation reference:** Spec 92 Governed Decision-to-Outcome Backend RC (Workstreams A/B/C/D); Spec 93 (ERPRiskBench); Spec 94 (Product Web Application)

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
| Immutable analytical snapshots | `real` / `read_only` | Bounded Odoo extraction manifest, source rows, hashes, scope and actor are persisted; update/delete are rejected. |
| Analytical Data Quality Gate | `real` / `blocked_on_insufficient_evidence` | Revenue/cost coverage, duplicates, refunds, currency, required fields, truncation and cost reliability govern which metrics may be claimed. |
| Versioned margin metrics | `real` / `advisory` | `margin-truth/1.0.0` computes revenue, refunds, COGS, margin, discount, units and product/customer segments from a frozen snapshot. |
| Period margin bridge | `real` / `advisory` | Deterministic price, volume, mix, discount, cost and refund effects reconcile prior to current margin within tolerance. |
| Opportunity and ROI engine | `real` / `advisory` | Phase 16.6 (`erpguard/domain/opportunity/`): deterministic detection rules over margin drivers produce immutable, evidence-linked `MarginOpportunity` rows with conservative/base/optimistic sizing; `implementation_cost`/`payback_period_days` stay `null` rather than fabricated. |
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
| Canary, activation, promotion and rollback (deployment lifecycle) | `real` / `blocked_on_evidence` | Phase 19: `compiled -> approved -> canary -> active -> rolled_back` with at-most-one-active-package enforcement; promotion requires a `completed` `CanaryPolicy`, zero unresolved critical incidents and a real postcondition success rate when one exists (Spec 92 Sec 9.9). |
| Governed recommendation lifecycle | `real` | Spec 92 Workstream A (`erpguard/domain/recommendations/`): `draft -> submitted -> approved -> converted`, content-frozen after submit, independent approval bound to exact content hash. |
| Pricing-scenario Odoo draft (`sales.quote.create_pricing_scenario_draft`) | `staging_only` / `blocked_by_default` | Distinct capability from Phase 16's `quote.create_draft`; live/customer/product preflight, margin/line/total ceilings, draft-only postcondition, idempotent retry. `ERPGUARD_ALLOW_PRICING_SCENARIO_DRAFT=false` by default. Verified live against a real, authorized Odoo 19 staging instance — see `docs/demo/backend_rc_live_pricing_scenario_evidence.json`. |
| Operational canary router | `real` | Spec 92 Workstream B (`erpguard/domain/canary/routing.py`): deterministic `sha256`-bucket lane selection, append-only routing decisions, safety-threshold auto-pause. No RNG, no LLM. |
| Outcome measurement / realized ROI | `real` / `advisory` | Spec 92 Workstream C (`erpguard/domain/outcomes/`): gated comparison (metric version, currency, coverage), explicit `live_odoo_read` / `fixture` / `manual_import` labeling, no causal-claim language. Net ROI with a supplied, evidenced implementation cost is computed (`net_realized_value`); missing cost leaves the field `null`, never guessed. |
| Decision-to-outcome evidence bundle | `real` | Spec 92 Workstream D (`erpguard/domain/evidence/`, `erpguard/application/evidence/`): hash-chained manifest over the full lifecycle, sealed-immutable, tamper-detected on every read. |
| ERPRiskBench governed-vs-ungoverned benchmark | `real` / `fixture` | Spec 93 (`erpguard/benchmark/`): deterministic 120-case synthetic dataset, 3 configurations (`fixed_workflow`/`direct_tool_agent`/`erpguard_candidate`), Sec 28.3's 14 metrics as pure functions, append-only case results. `direct_tool_agent` is itself only `simulated` unless a real `ANTHROPIC_API_KEY` and `allow_benchmark_direct_agent=true` are configured. |
| Product web application | `real` | Spec 94 (`web/`): React/TypeScript SPA consuming the existing API surface only (no new backend capability); served by `create_public_app` behind `ERPGUARD_SERVE_FRONTEND=true`. Canary's `recommend` field and the outcome causal-confidence disclaimer are rendered as explicit, non-actionable advisory copy, never a button. |
| Development-only token bootstrap (`POST /internal/dev-tokens`) | `real` / `blocked_by_default` | Spec 94: issues a real, verifiable bearer token for the web app to authenticate against; gated behind `ERPGUARD_INTERNAL_SURFACES` exactly like `/demo`, explicitly documented as non-production auth, not a login/identity-provider capability. |
| Identity and tenant enforcement | `planned` | Master spec Phase 3; incomplete at baseline. |
| PostgreSQL/Alembic migration foundation | `planned` | Master spec Phase 2; absent from Phase 0 baseline. |
| Autonomous promotion, marketplace, second ERP connector, generic MCP | `blocked` | Explicit non-goals for the TFM path. |

## Safety invariant

No capability in this matrix authorizes an agent to call a raw ERP method. Any future effectful operation must remain behind the ERPGuard safety kernel and receive its own phase evidence.

