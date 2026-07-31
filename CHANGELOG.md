# Changelog

## Unreleased — Phase 16.5

### Added

- Immutable, tenant-scoped analytical snapshots over bounded Odoo reads.
- Versioned Data Quality Reports with explicit revenue/cost coverage and
  blocking issues.
- Canonical revenue, refund, cost, margin, discount, unit and customer
  metrics under `margin-truth/1.0.0`.
- Deterministic price/volume/mix/discount/cost/refund margin bridge,
  product/customer drivers and migration `0019_decision_intelligence`.

### Safety

- Odoo extraction is restricted to the existing read transport.
- Missing cost coverage leaves revenue visible but blocks margin conclusions.
- Current standard price is labelled as a non-historical fallback.
- No recommendation, ERP write or execution authority is created.

## Unreleased — Phase 18.1

### Added

- Automatic effects-free shadow evaluation after canonical OCEL/Odoo event
  ingestion.
- Persisted canonical trace provenance, timestamps, object links,
  correlation metadata and trace-derived idempotency.
- Append-only delayed outcomes with closed provenance labels and same-case
  source-event verification.
- Operational coverage, decision/review/outcome metrics, variant
  distribution and 95% Wilson intervals.
- Multi-gate advisory `eligible_for_canary` recommendation and migration
  `0018_operational_shadow_feed`.

### Safety

- Manual cases do not count toward canary eligibility.
- An unresolved `unsafe_candidate` review blocks the recommendation.
- Recommendation never creates canary routing, activation or promotion.
- The feed performs no connector write and creates no execution run.

## Unreleased — Phase 18

### Added

- Effects-free shadow deployments admitted only for submitted, valid
  candidates with an `eligible_for_shadow` Proof of Improvement.
- Deterministic active/candidate case comparison, normalized difference
  categories, optional observed outcomes and strict idempotency.
- Append-only shadow deployments, case evidence and human reviewer labels.
- Deployment-specific agreement dashboard and migration `0017_shadow_mode`.
- Sanitized selected disagreement evidence.

### Safety

- The candidate never calls a connector or creates an execution run.
- Threshold attainment does not activate, promote or route the candidate.
- Canary, promotion and rollback remain unimplemented Phase 19 work.

## Unreleased — Phase 17 / 17.1

### Added

- Bounded staging-only `sales.order.confirm` with independent exact-scope
  approval and signed single-use permit.
- Immutable order snapshot, automation fingerprint, side-effect budget,
  postcondition evaluation, sealed Evidence Pack and CompensationPlan.
- Migrations `0015_governed_confirmation` and
  `0016_confirmation_side_effect_contract`.
- Sanitized live staging failure/compensation evidence and an
  unexpected-posted-invoice regression.

### Safety

- Confirmation remains false by default.
- The live unexpected invoice was classified `failed`, not successful.
- Manual compensation preserved invoice and linked credit note and verified
  documentary net effect zero.
- No public cancellation, invoice-posting, payment, deletion or generic Odoo
  RPC capability was added.

## 0.14.0 - 2026-07-27

### Added

- Phase 0 baseline freeze artifacts and ADR-0001.
- Canonical package/API/README version metadata.
- `uv.lock`, CI quality gates, Docker install surface and community policy files.
- Public/legacy documentation boundary and deprecation policy.

### Safety

- No raw ERP execution or new ERP write capability was added.

## Historical releases

The previous `0.12.x` and `0.13.x` release-candidate material remains in the legacy documentation set.

