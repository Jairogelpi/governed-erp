# Spec 92 — Governed Decision-to-Outcome Backend Release Candidate

## Problem

Decision Intelligence (Phase 16.5/16.6) could explain a margin move and size
an opportunity, but nothing turned that evidence into a governed, executable
action; Governed Execution (Phase 14/15/17/17.1) could run a bounded write
under permit, but had no caller that ever selected *what* to run from
analytical evidence, and the Phase 19 skill lifecycle
(`compiled -> approved -> canary -> active -> rolled_back`) had a canary
status with no runtime router behind it. The two pillars existed side by
side, unconnected. This delivery links them end to end:

```text
AnalyticalSnapshot -> MarginAnalysis -> MarginOpportunity
  -> GovernedRecommendation -> approval -> GovernedActionDraft
  -> CanaryPolicy-routed ExecutionRun -> postconditions
  -> OutcomeMeasurementPlan -> RealizedOutcomeReport
  -> DecisionOutcomeEvidenceBundle (sealed, hash-chained)
```

Baseline commit `e858f48`. Four workstreams, delivered together because
each is evidence input to the next.

## Workstream A — Recommendation → Governed Action

`erpguard/domain/recommendations/` + `erpguard/application/recommendations/service.py`.

`GovernedRecommendation` freezes its content at `submit`; approval reuses
the existing `Approval`/`ApprovalService` primitive (same
creator-cannot-approve-own-work rule Phase 15 already enforces for runs),
bound by exact scope to `recommendation:{id}:approve:{content_hash}` and a
configurable max age (default 24h). Approved + a code-defined action
template produces a `GovernedActionDraft`, immutable once validated.

Three code-defined templates
(`erpguard/domain/recommendations/templates.py`): only
`customer_discount_quote_scenario_v1` is `executable`; `product_price_review_v1`
and `cost_drift_review_v1` are `review_only` — the compiler-enforced
`_CAPABILITIES_WITH_REAL_POSTCONDITION_SUPPORT` allowlist in
`erpguard/domain/skills/compiler.py` is the actual mechanism that makes a
`review_only` template's classification impossible to silently upgrade.

**New Odoo capability**, `sales.quote.create_pricing_scenario_draft` —
deliberately not a reuse of the pre-existing `quote.create_draft` (Sec 8.1
requires a distinct capability, since this write carries recommendation
evidence and its own precondition/postcondition contract):

- Preflight (`OdooConnectorPlugin.pricing_scenario_preflight`, called at
  `PermitService.plan()` *and* re-checked at `execute()`): staging-only
  connection, customer exists and active, every product exists/active/
  saleable, no forbidden product marker. Feature flag, line-count/total
  ceilings, per-line margin floor and non-negative cost evidence are
  domain-level checks in `validate_pricing_scenario` that run before an
  action draft is even built.
- Postcondition (`_verify_pricing_scenario_draft`): state stays `draft`;
  customer/company/pricelist/line product-set/quantities/prices match the
  recommendation's arguments exactly; per-line margin re-verified against
  the same cost/floor evidence; any invoice, picking, purchase order or
  manufacturing order fails the run (`forbidden_effect_observed:*`).
- Idempotency: `find_by_client_reference` before create — retry returns the
  existing draft, never a duplicate.

## Workstream B — Operational Canary Router

`erpguard/domain/canary/` + `erpguard/application/canary/service.py`.

Deterministic routing: `bucket = sha256(tenant_id, canary_policy_id,
process_key, business_object_key) mod 10000`, `lane = "canary" if bucket <
percentage_basis_points else "stable"` — pure functions in
`erpguard/domain/canary/routing.py`, no RNG, no LLM. Every decision persists
as an append-only `CanaryRoutingDecision` with a `selection_reason`
(`hash_selected_canary`, `outside_scope`, `maximum_cases_reached`,
`kill_switch`, …). `POST /v1/runs/plan` accepts an optional
`routing_context`; without one it always resolves the stable active
package, never defaults to canary.

Safety pauses: a `critical`-severity `CanarySafetyIncident` auto-pauses the
policy (`status -> paused`) without deleting evidence; `maximum_cases` and
`maximum_total_amount` are checked before every routing decision, the
latter against the *actual* cumulative amount of past canary-lane runs
(`_run_amount` in `erpguard/application/canary/service.py`, reading each
run's `capability_payload.lines` or bound `state_snapshot.amount_total` —
not a placeholder). Promotion hardening
(`erpguard/domain/canary/eligibility.py`, called from
`SkillDeploymentService.promote_to_active`) requires a `completed` policy,
zero unresolved critical incidents, a minimum case count, and a real
postcondition success rate computed from terminal `ExecutionRun` outcomes
— `canary` status alone is never sufficient, and a package with only
`planned`/unexecuted canary cases cannot promote (no evidence yet, not
"assumed passing").

## Workstream C — Outcome and Realized ROI

`erpguard/domain/outcomes/` + `erpguard/application/outcomes/service.py`
(already on this branch before this delivery's A/B/D work; documented here
for completeness of the lifecycle). `OutcomeMeasurementPlan` compares a
baseline snapshot against a follow-up observation (`live_odoo_read`,
`fixture`, or `manual_import`, always labeled); refuses the comparison on
metric-version mismatch, incomparable currency, low cost coverage or a
blocked baseline. `RealizedOutcomeReport` classifies
`positive_observed_result` / `negative_observed_result` /
`neutral_observed_result` / `inconclusive` / `blocked` and never emits
`proved`/`caused`/`guaranteed` — `interpretation.py` explicitly labels the
observed change `"observed_change_is_not_a_causal_claim"`. Net ROI with
implementation cost (Sec 10.6) is implemented: `OutcomeService.create_plan`
accepts an optional `implementation_cost`, supplied and frozen at plan
creation — before the outcome is known, never invented after the fact —
and `evaluate()` computes `net_realized_value = realized_value -
implementation_cost` only when a cost was supplied; missing cost leaves
both `implementation_cost` and `net_realized_value` `null` on the report,
never guessed or defaulted to a fixed rate (migration
`0026_outcome_implementation_cost`).

## Workstream D — Decision-to-Outcome Evidence Bundle

`erpguard/domain/evidence/decision_outcome_bundle.py` +
`erpguard/application/evidence/decision_outcome_service.py`.

`DecisionOutcomeEvidenceService.build()` walks the whole chain for one
`GovernedRecommendation` — analytical snapshot, data-quality report, margin
analysis, opportunity, recommendation, its approval, action draft, action
validation, execution run, its approvals, its permit fields, its
postcondition result, its sealed Evidence Pack (re-verified via
`PermitService.get_evidence`, itself tamper-checked), canary policy/
routing-decision/safety-incidents *if the run was canary-routed at all*
(genuinely optional per Sec 9.5 point 4 — a run with no routing context
never touches canary), measurement plan, follow-up observation, realized
outcome report, and the involved skill package's deployment audit trail —
and marks the bundle `complete` or `incomplete` with the exact missing
resource types listed.

Each reference is pinned to a `reality_label` (`live`, `staging_live`,
`fixture`, `synthetic`, `derived`, `manual`) — e.g. the analytical snapshot
is `live` (real Odoo read), the execution run is `staging_live`, the
outcome observation's label is derived from its own `source` field.

`chain_hash` folds each ordered reference into the last (`chain =
sha256({"previous": chain, "resource": ref})`), so altering or reordering
any single reference invalidates every hash after it, not just its own.
`seal()` re-gathers live (never trusts the stored manifest), and additionally
requires: no unresolved safety incident, the recommendation not rejected/
expired, the execution run terminal, the measurement plan terminal, no
secret-like field (key-name scan: `secret`, `credential`, `password`,
`api_key`, `token`, …), and at most one sealed bundle per
(recommendation, measurement_plan) pair. Once sealed, the row is fully
immutable at the ORM level (`before_update` listener rejects any change).

`GET .../{bundle_id}` revalidates the *stored* manifest's hashes on every
read (cheap, catches raw DB tampering) and returns `409
evidence_integrity_failed` on mismatch; `GET .../{bundle_id}/verify`
additionally re-fetches every referenced resource's *current* hash (the
heavier, explicitly on-demand check).

## Integration fix: canary routing was unreachable from a recommendation

Found while building the end-to-end test: `RecommendationService
.convert_to_run` always resolved `SkillDeploymentService.get_active()`
directly — it never passed `process_key`/`routing_context` into
`PermitService.plan()`, so a `CanaryPolicy` deployed for
`sales.quote.create_pricing_scenario_draft` could never actually route a
recommendation's execution, even though Workstream B's router worked
correctly for any *other* capability planned directly through
`POST /v1/runs/plan`. Fixed by adding an optional `routing_context` to
`convert_to_run` and to `POST /v1/action-drafts/{id}/plan-run`'s request
body (same `RunRoutingContext` shape `/v1/runs/plan` already uses);
omitting it keeps the pre-existing direct-to-stable behavior, so no
existing caller changed behavior.

## API surface added

```text
POST /v1/opportunities/{opportunity_id}/recommendations
GET  /v1/recommendations/{recommendation_id}
POST /v1/recommendations/{recommendation_id}/submit
POST /v1/recommendations/{recommendation_id}/approve
POST /v1/recommendations/{recommendation_id}/reject
POST /v1/recommendations/{recommendation_id}/action-drafts
GET  /v1/action-drafts/{action_draft_id}
POST /v1/action-drafts/{action_draft_id}/validate
POST /v1/action-drafts/{action_draft_id}/plan-run
POST /v1/action-drafts/{action_draft_id}/invalidate

POST /v1/canary-policies
GET  /v1/canary-policies/{policy_id}
POST /v1/canary-policies/{policy_id}/approve
POST /v1/canary-policies/{policy_id}/activate
POST /v1/canary-policies/{policy_id}/pause
POST /v1/canary-policies/{policy_id}/resume
POST /v1/canary-policies/{policy_id}/abort
GET  /v1/canary-policies/{policy_id}/dashboard
GET  /v1/canary-policies/{policy_id}/routing-decisions
GET  /v1/canary-policies/{policy_id}/incidents

POST /v1/recommendations/{recommendation_id}/measurement-plans
GET  /v1/measurement-plans/{plan_id}
POST /v1/measurement-plans/{plan_id}/approve
POST /v1/measurement-plans/{plan_id}/start
POST /v1/measurement-plans/{plan_id}/capture-followup
POST /v1/measurement-plans/{plan_id}/evaluate
GET  /v1/outcome-reports/{report_id}

POST /v1/recommendations/{recommendation_id}/evidence-bundle
GET  /v1/decision-outcome-evidence/{bundle_id}
GET  /v1/decision-outcome-evidence/{bundle_id}/verify
```

## Migrations

`0022_recommendation_action_drafts`, `0023_operational_canary_router`,
`0024_outcome_measurement`, `0025_decision_outcome_evidence`,
`0026_outcome_implementation_cost`. All verified
`upgrade head -> downgrade -1 -> upgrade head` against SQLite (see
Verification); `0025`/`0026` additionally verified against PostgreSQL 16 in
CI.

## Known gaps and deferred work

Net ROI with implementation cost (Sec 10.6) and the canary dashboard's
`estimated_opportunity_value` (Sec 9.8) — the two gaps this document
originally listed here — are both implemented; see Workstream C and
Workstream B above respectively. What remains:

- **Live Odoo staging test (Sec 19/20) — performed 2026-07-31/2026-08-01**
  against a real Odoo 19 staging instance (server version `19.0+e`),
  authorized by the instance owner. Two runs, both against the real
  `LegacyXmlRpcWriteTransport`, not the fake transport the automated suite
  uses:
  1. Direct-to-stable: full governed pipeline (recommendation → approval →
     action draft → validated → planned → approved → executed), one draft
     `sale.order` created (id 155, `GUIA-00465`).
  2. Genuinely canary-routed: two real Odoo skill packages sharing one
     process_key, an approved/activated `CanaryPolicy`, and a
     `routing_context`-planned run that `CanaryRouterService` actually
     routed to the canary package (confirmed on the persisted
     `ExecutionRun.deployment_lane`, not assumed) — one draft `sale.order`
     created (id 156, `GUIA-00466`).

  Both: independently re-read after execution (a separate `OdooClient`
  call outside the governed pipeline's own postcondition check) to confirm
  `state=draft` with zero invoices/pickings/purchase/manufacturing orders;
  retry via a fresh `plan-run` call returned the same `ExecutionRun`
  rather than creating a duplicate. Full evidence:
  `docs/demo/backend_rc_live_pricing_scenario_evidence.json`.
- Sealing a `DecisionOutcomeEvidenceBundle` requires the referenced
  `ExecutionRun` to be terminal but does not require it to be
  `succeeded` specifically (`blocked`/`failed`/`unknown` runs can still
  seal an otherwise-complete chain) — intentional (a sealed bundle records
  what actually happened, including a governed rejection), but worth
  flagging since "sealed" could be misread as "succeeded."

## Verification

- Full suite: `942 passed, 4 skipped` (Python, local SQLite).
- `tests/test_backend_rc_end_to_end.py` drives the entire lifecycle above
  in one flow, asserting: no generic ERP call exists structurally; the
  exact selected canary package is recorded on the `ExecutionRun`; the same
  routing context always selects the same package/bucket; the canary
  dashboard's `estimated_opportunity_value` traces back to the real
  `MarginOpportunity.impact_base`; the sealed evidence bundle's `verify`
  returns `stored_hashes_intact=True` and
  `live_mismatches=[]`.
- Ruff and mypy clean on every file touched by this delivery (pre-existing
  errors in untouched files — `erpguard/policies/loader.py`,
  `erpguard/domain/processes/validation.py` missing `types-PyYAML` stubs;
  `erpguard/domain/outcomes/comparison.py` unrelated `Decimal | None`
  narrowing — are unchanged by this work).
- Alembic `upgrade head -> downgrade -1 -> upgrade head` verified against
  SQLite for `0025_decision_outcome_evidence`. Not verified locally against
  PostgreSQL (no local Postgres in this environment); the same
  downgrade/upgrade cycle now also runs in CI against real PostgreSQL 16
  (added to `postgres-migrations` — the existing workflow only ran a plain
  `upgrade head` before this branch).
- Sec 21's "secret scan" CI gate did not exist in the workflow at all
  before this branch; added a `gitleaks` job (full git history, every
  push/PR). Its first run correctly found nothing sensitive but flagged
  one false positive — an internal `rec_<uuid4().hex>` resource id in
  `docs/demo/backend_rc_live_pricing_scenario_evidence.json`, high-entropy
  enough to trip the default `generic-api-key` rule. Added `.gitleaks.toml`
  allowlisting ERPGuard's own `{prefix}_{32 hex chars}` id format
  specifically (not a blanket path exemption) after manually re-confirming
  the real staging credential handled during live testing (see below)
  never entered git history or the working tree.
- CI (`secret-scan`, `postgres-migrations`, `docker`, `quality` 3.11/3.13)
  all green on this branch's PR, after clearing two pre-existing
  repo-wide lint/type issues (unrelated to this delivery, predating it)
  and the two CI-gate additions above.
- Live Odoo staging test (Sec 19/20) performed and verified, including a
  genuinely canary-routed run — see "Known gaps and deferred work" above.

## Out of scope

Everything Sec 3 excludes: a second ERP connector, generic model/method
execution, arbitrary SQL/Python, browser automation, unrestricted HTTP,
mass price updates, automatic price-list activation, automatic approval,
automatic promotion, automatic accounting/payment actions, deletion of
financial documents, causal-impact claims, reinforcement learning, an LLM
inside deterministic calculations, the product web application, the
ERPRiskBench benchmark suite, and the public beta release package.
