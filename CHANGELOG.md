# Changelog

## v1.0.0-tfm — TFM submission freeze

- `pyproject.toml` version bumped `0.14.0` → `1.0.0` and the README title
  updated to match the `v1.0.0-tfm` tag — both had been left pointing at
  the migration-foundation baseline well after Spec 92-95 landed.
- README's "Architecture and reality labels" section rewritten as a
  `real`/`staging_only`/`fixture`/`advisory`/`planned` table for
  scannability; the `v1.0.0-tfm` tag line in the Definition of Done
  checklist and `docs/release/versions.md` corrected to reflect the tag
  actually being cut.

## Unreleased — Spec 95 (Phase 22: TFM Delivery and Release Freeze)

### Added

- `scripts/validate_demo_install.py` + `docker-compose.demo.yml` --
  clean-install acceptance against Fake ERP data, driven purely over
  HTTP against a running server. Explicitly does not exercise the
  decision-to-outcome pillar (see "Fixed"/"Found" below).
- `scripts/export_benchmark_report.py` -- runs a real `BenchmarkRun`
  against a scratch database and exports its report + raw results, so
  the TFM memory can cite a real artifact instead of hand-restating
  numbers.
- `.github/workflows/ci.yml` `release-checks` job: dependency scan
  (`pip-audit`, advisory/non-blocking), SBOM generation (CycloneDX,
  uploaded as a CI artifact), a benchmark smoke test
  (`tests/test_phase22_benchmark_smoke.py`, `erpguard_candidate` only,
  8 cases), and a local-links-only docs link check (lychee `--offline`).
- `docs/tfm/annexes/` -- the Sec 39.2 annex set (OpenAPI export, the
  `direct_tool_agent` prompt verbatim, data rights/GDPR analysis,
  installation notes, code/repository pointers, test reports).
- `docs/tfm/memoria_draft.md` -- a first, explicitly-a-draft TFM memory
  in Spanish, every factual claim grounded in a real repository
  artifact.
- `docs/demo/five_minute_demo_script.md`, `docs/release/versions.md`.
- `tests/test_phase22_docs_contract.py`, `tests/test_phase22_definition_of_done.py`.
- README restructured (Sec 38): the top now leads with a Definition of
  Done section instead of the chronological phase narrative, which
  moved to `docs/architecture/phase_narrative.md`.

### Fixed

- `erpguard.db.session.init_db()` was missing four model-package imports
  (`replay`, `proof`, `skill_package`, `execution`) -- a database built
  via `init_db()` alone (used by `scripts/start_release_candidate.sh`/
  `.ps1`) silently never created `process_replays`, `process_replay_cases`,
  `process_proofs`, `skill_packages`, `execution_runs` or `approvals`,
  crashing the first time any of those were used. `alembic upgrade head`
  was never affected. Found only by actually running
  `validate_demo_install.py` against a live server.
- Broken relative links in `docs/legacy/releases.md` and
  `docs/specs/18_mvp_demo_report.md` (root-relative paths that don't
  resolve from the file's own directory) -- found by the new docs link
  check before it ever ran in CI.
- `POST /v1/events/fake-generate`'s event vocabulary
  (`erpguard.domain.events.fake_generator.build_fake_ocel`) emitted
  `sales.order.created`/`sales.order.reviewed`, which do not match
  `quote_to_order_v1.yaml`'s declared vocabulary
  (`sales.quote.created`/`sales.quote.reviewed`) -- variant discovery
  never matched the canonical happy-path variant. Fixed in a follow-up
  pass to this phase (found by reading the generator against the process
  YAML, not just a surface review); verified with a test that runs
  `VariantDiscoveryService.discover(...)` against freshly generated
  events and checks the exact happy-path sequence, and manually via a
  real browser walkthrough of the merged Phase 21 web app. The same pass
  also ran `docker compose -f docker-compose.demo.yml up --build` for
  real (not just `uvicorn` locally) and `validate_demo_install.py`
  against that live container: 22/22 checks passed.

### Found, not fixed (documented as a known gap)

- The decision-to-outcome pillar (Spec 92) has no Fake-ERP/fixture entry
  point: every `MarginOpportunity` requires a real Odoo-derived
  analytical snapshot (`POST /v1/decision-intelligence/snapshots`).
  `validate_demo_install.py` exercises the full existing pillar (connect
  through execution) but explicitly skips recommendations, canary,
  outcomes and evidence for this reason -- resolving it is product work
  for a future phase, not packaging work for this one.

## Unreleased — Spec 94 (Phase 21: Product Web Application)

### Added

- `web/` — React + TypeScript + Vite SPA, typed API client generated from
  the backend's own OpenAPI schema (`openapi-typescript` + `openapi-fetch`),
  no hand-maintained request/response types.
- Screens for the existing pillar (Overview, Connections/onboarding,
  Processes with variant explorer and candidate builder, Replays with
  Proof of Improvement, Deployments with skill-package promotion/rollback,
  Runs) and the decision-to-outcome pillar (Opportunities, Recommendations
  with the pricing-scenario Action Draft editor and a canary-routing
  toggle, Canary with the `recommend` field rendered as an explicit
  advisory banner — never an auto-acting button, Outcomes with the
  measurement-plan stepper and the literal `observed_change_is_not_a_causal_claim`
  disclaimer next to every realized-value number, Evidence with the
  Decision-to-Outcome bundle viewer/verify/export), plus Benchmarks
  (ERPRiskBench report viewer) and Settings (session token, dev-token
  bootstrap).
- `POST /internal/dev-tokens` — scoped, internal-only, non-production
  bearer-token bootstrap (gated behind `ERPGUARD_INTERNAL_SURFACES`, same
  as `/demo`); the backend previously had no route capable of issuing a
  session token to a browser at all.
- `create_public_app(..., serve_frontend=...)` mounts `web/dist` at `/`
  with SPA deep-link fallback, opt-in via `ERPGUARD_SERVE_FRONTEND=true`
  (off by default so existing tests are unaffected by incidental local
  build artifacts).
- `/demo` now carries a banner pointing at the product application and is
  excluded from new README/demo screenshots.
- CI: a `frontend` job (Vitest component tests, `tsc -b`, production
  build) and `tests/test_phase21_web_build.py`.
- `web/e2e/` — two Playwright specs covering both exit-criteria paths
  against a real backend (Fake connector only); documented as a manual
  local verification path, not wired into CI (see `web/e2e/README.md`).

## Unreleased — Spec 92 (Governed Decision-to-Outcome Backend RC)

### Added

- Governed recommendation lifecycle (`GovernedRecommendation`,
  `GovernedActionDraft`): content-frozen at submit, independent approval
  bound to exact content hash, code-defined allowlisted action templates.
- New Odoo capability `sales.quote.create_pricing_scenario_draft` —
  distinct from `quote.create_draft`, with live customer/product/staging
  preflight and a draft-only postcondition that re-verifies lines, prices
  and per-line margin against the recommendation's own evidence.
- Operational canary router: deterministic `sha256`-bucket routing,
  append-only routing decisions, safety-threshold auto-pause, and
  promotion hardening requiring a completed policy, zero unresolved
  critical incidents and a real (not simulated) postcondition success
  rate.
- `DecisionOutcomeEvidenceBundle`: hash-chained manifest over the full
  decision-to-outcome lifecycle, reality-labeled per reference,
  sealed-immutable, tamper-detected on every read and on demand via
  `.../verify`.
- Net ROI with implementation cost (Sec 10.6): `OutcomeMeasurementPlan
  .implementation_cost`, supplied and frozen at plan-creation time;
  `net_realized_value = realized_value - implementation_cost` computed
  only when a cost was supplied, `null` otherwise.
- Canary dashboard's `estimated_opportunity_value`: traces every routed
  run back through its action draft/recommendation to the
  `MarginOpportunity` that motivated it.
- Migrations `0022_recommendation_action_drafts`,
  `0023_operational_canary_router`, `0024_outcome_measurement`,
  `0025_decision_outcome_evidence`, `0026_outcome_implementation_cost`.
- CI: PostgreSQL downgrade/upgrade cycle for the latest migration; a
  `secret-scan` job (gitleaks, full git history, every push/PR).
- `tests/test_backend_rc_end_to_end.py` — full lifecycle acceptance test.

### Fixed

- `RecommendationService.convert_to_run` never routed through the canary
  router — it always resolved the stable active package directly. Added an
  optional `routing_context` (same shape `/v1/runs/plan` already accepts),
  backward-compatible when omitted.
- Canary dashboard's `cumulative_amount` and `unexpected_side_effects`
  were hardcoded to `0`/`0.0`, making the `maximum_total_amount` safety
  pause inoperative. Now computed from actual `ExecutionRun` data.
- Promotion eligibility's `postcondition_success_rate` was faked as `1.0`
  whenever any canary case existed, regardless of whether it had actually
  executed. Now computed from terminal `ExecutionRun` outcomes only.

### Safety

- `sales.quote.create_pricing_scenario_draft` remains false by default
  (`ERPGUARD_ALLOW_PRICING_SCENARIO_DRAFT=false`) and staging-only.
- Two live Odoo 19 staging tests performed against a real, authorized
  staging instance (one direct-to-stable, one genuinely canary-routed):
  each created one draft `sale.order`, independently re-read to confirm
  `state=draft` with zero invoices/pickings, retry proven idempotent —
  see `docs/demo/backend_rc_live_pricing_scenario_evidence.json`.
- Missing implementation cost leaves `net_realized_value` unset rather
  than guessed or defaulted to a fixed rate; a negative supplied cost is
  rejected (`422`).
- No generic model/method/`execute_raw` entry point exists on the Odoo
  connector; canary bucket selection has no caller-suppliable seed; no
  credential or secret reference is ever gathered into an evidence bundle.

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

