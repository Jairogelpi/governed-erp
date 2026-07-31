# Phase 16.6 — Opportunity & ROI Engine

## Problem

Phase 16.5's `MarginAnalysis` can explain why margin moved (price/volume/mix/
discount/cost/refund effects, per-segment drivers) but produces no
actionable, economically-sized recommendation. Nothing turned "margin fell
8%" into "raise price on these 14 products, expect +€X, confidence Y."

## Design

`erpguard/domain/opportunity/rules.py` runs deterministic detection rules
over a `MarginAnalysis`'s `product_drivers_json`/`customer_drivers_json`
(each `{"current": [SegmentMetric...], "comparison": [SegmentMetric...]}`).
No rule invents data the driver rows don't have — no per-segment price,
quantity, or discount depth exists at this grain, so nothing below claims
it does.

Rules (v1, three causes):
1. **`product_margin_percent_erosion`** — products whose `gross_margin_percent`
   dropped comparison → current. Impact = margin-percent-points lost ×
   current net revenue.
2. **`cost_drift`** — products where `cost_of_sales / net_revenue` grew
   faster than revenue. Impact = cost-ratio-points gained × current net
   revenue.
3. **`customer_margin_percent_erosion`** — same computation as (1), over
   customers.

A segment only qualifies if both its current and comparison rows have
non-null cost/margin data (missing data is skipped, never guessed).

`erpguard/application/opportunity/service.py` (`OpportunityEngineService`)
wraps rule output into persisted `MarginOpportunity` rows:
- **Scenario spread** — conservative = base × 0.6, optimistic = base × 1.3.
  Fixed constants, not tuned/forecast — v1 is intentionally simple, and this
  is stated in code, not disguised as a model.
- **Confidence band** — inherited from the analysis's `DataQualityReport
  .confidence_grade` (A→high, B→medium, C→low), not a fabricated score.
- **Risk level** — derived from `cost_coverage_rate` (≥0.95 low, ≥0.8
  medium, else high).
- **`implementation_cost`/`payback_period_days`** — left `None`. This
  codebase has no operational-cost input to back those numbers; faking them
  would violate the project's existing "don't force a conclusion the data
  doesn't support" ethos (cf. Phase 16.5's blocked-margin gating).

`MarginAnalysis.status == "blocked"` short-circuits generation to an empty
result with an explicit `blocked: true` in the API response — never a
silent empty list indistinguishable from "no opportunities found."

Output rows are immutable (`erpguard/db/model_packages/opportunity.py`,
same `before_update`/`before_delete` idiom as `margin_analyses`).
Generation is idempotent per `margin_analysis_id` — a second call returns
the existing rows rather than duplicating.

## API

- `POST /v1/margin-analyses/{margin_analysis_id}/opportunities`
- `GET /v1/margin-analyses/{margin_analysis_id}/opportunities`

## Naming note

A dead, unmounted legacy `Opportunity`/`OpportunityScan` pair already
exists in `erpguard/db/models.py` (unrelated `BusinessSnapshot`/
`BusinessSignal` heuristic scanner, zero live references). This phase's
model is named `MarginOpportunity` to avoid an ORM class-name collision and
to avoid conflating governed, evidence-linked output with that dead code.

## Out of scope

Turning an `Opportunity` into a selectable, governed automation draft
(spec's "Opportunity → skill draft" pipeline) — this phase only produces
the evidence and economic sizing.
