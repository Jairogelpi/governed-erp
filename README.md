# ERPGuard Evolution v1.0.0-tfm

ERPGuard Evolution is a versioned, testable and governed platform for
understanding and improving ERP business processes. It keeps ERP effects behind
explicit safety boundaries: almost everything is read-only or simulated.
Real ERP writes remain a small, permit-gated, allowlisted set —
`quote.create_draft` (Phase 16), `sales.order.confirm` (Phase 17) and
`sales.quote.create_pricing_scenario_draft` (Spec 92) — each staging-only,
false-by-default, and structurally incapable of a generic "raw ERP write."

> Current project state: **`v1.0.0-tfm`, TFM submission freeze.** The full
> path — data → process mining → economic diagnosis → opportunity →
> governed recommendation → independent approval → bounded action draft →
> operational canary routing → signed permit → controlled Odoo draft →
> postcondition verification → measured outcome → sealed, hash-chained
> evidence bundle — is implemented and tested end to end (Spec 92
> Workstreams A–D). ERPRiskBench (Spec 93) and the product web application
> (Spec 94) are complete and merged. Packaging and clean-install
> validation (Spec 95 / Phase 22) are done; the remaining Definition of
> Done items are human-judgment sign-off on the thesis memory/video, not
> code — see the checklist below and
> [docs/specs/95_phase22_tfm_delivery_and_release_freeze.md](docs/specs/95_phase22_tfm_delivery_and_release_freeze.md).

## What exists now

The implemented path is:

```text
identity/tenants
  → encrypted unified connections
  → Connector SDK v2
  → canonical OCEL-shaped events
  → Odoo read-only connector and controlled bridge
  → Quote-to-Order process definition
  → variant discovery
  → tenant-scoped immutable process candidates with deterministic definitions
```

The default FastAPI app mounts only the declared `/v1` public route roots.
The Fake ERP/operator demo is internal and requires
`ERPGUARD_INTERNAL_SURFACES=true`. The pre-C1 legacy route graph and its
opt-in flag were removed in wave C6; there is no way to mount it anymore.

The repository can currently:

- discover Fake and Odoo Connector SDK v2 plugins through entry points;
- expose SDK v2 connector definitions and a safe, tenant-scoped connection-test boundary;
- import/export tenant-scoped canonical events and keep ingestion cursors;
- normalize controlled Odoo bridge payloads with correlation and provenance labels;
- validate and version the Quote-to-Order baseline process;
- group canonical event traces into variants with counts and durations;
- create tenant-isolated, evidence-resolved process candidates without activation;
- materialize a validated candidate definition and stable base/patch/result digests.

Variant Discovery uses the relational `canonical_event_objects` link table and
the shared `sales.*` event vocabulary, so the current path is ready for larger
fixture sets after migration/backfill rather than relying on an object-by-all-
events scan.

## Current demo

Start the local API:

```bash
uv sync --extra dev
python -m alembic upgrade head
uvicorn apps.api.main:app --reload
```

Build and serve the product web application (Spec 94, Phase 21) with:

```bash
cd web && npm ci && npm run build && cd ..
ERPGUARD_SERVE_FRONTEND=true uvicorn apps.api.main:app --reload
```

then open [http://127.0.0.1:8000/](http://127.0.0.1:8000/). The old
engineering dashboard is still available for internal debugging: set
`ERPGUARD_INTERNAL_SURFACES=true` before starting the API and open
[http://127.0.0.1:8000/demo](http://127.0.0.1:8000/demo) -- it now carries
a banner pointing back at the product application and is excluded from
new README/demo screenshots from Phase 21 onward. The current public API
surfaces are:

```text
GET  /v1/variants?object_type=sales_order
GET  /v1/variants/dashboard
GET  /v1/variants/cases/{case_id}
GET  /v1/connectors
GET  /v1/connectors/{connector_id}
POST /v1/connectors/{connector_id}/test
POST /v1/process-candidates
POST /v1/process-candidates/{candidate_id}/submit
```

There is no bundled GIF asset yet; the dashboard and JSON API are the current
reproducible demo surfaces.

## What is real / What is simulated

| Label | Meaning | Examples |
| --- | --- | --- |
| `real` | Runs for real, no simulation, on every request. | Identity boundaries, migrations, encrypted local secrets, canonical storage, validation, connector registry/runtime convergence, variant projection, candidate immutability, public/internal app composition boundaries, the governed recommendation/action-draft lifecycle, the operational canary router, outcome measurement gating, the sealed decision-to-outcome evidence bundle. |
| `staging_only` | Real code path, real Odoo call, gated to non-production by default. | Odoo read-only transport, live smoke checks, `sales.order.confirm`, `sales.quote.create_pricing_scenario_draft` (both false-by-default; the latter verified live 2026-07-31 — see [evidence](docs/demo/backend_rc_live_pricing_scenario_evidence.json)). |
| `fixture` | Deterministic local data, not a live system. | FakeConnector, Fake ERP data, local process/variant fixtures, `fixture`/`manual_import`-sourced outcome observations. |
| `advisory` | A computed recommendation, never auto-applied, never a causal claim. | Canary eligibility recommendations, opportunity/ROI sizing, realized-outcome classification. |
| `planned` | Not implemented yet. | A Fake-ERP/fixture path into the decision-to-outcome pillar (every `MarginOpportunity` requires a real Odoo-derived analytical snapshot — see [installation notes](docs/tfm/annexes/installation.md)); production-grade authentication (`POST /internal/dev-tokens` is an explicitly non-production bootstrap); the `v1.0.0-beta.1` public-beta tag (see [docs/release/versions.md](docs/release/versions.md)). |

Full label-by-capability detail lives in the
[capability reality matrix](docs/architecture/capability_reality_matrix.md).

Read the [current architecture inventory](docs/architecture/current_inventory.md),
[capability reality matrix](docs/architecture/capability_reality_matrix.md),
[master specification](docs/specs/84_erpguard_evolution_master_spec.md),
[decision-to-outcome flow diagrams](docs/architecture/decision_to_outcome_flow.md),
[operational canary threat model](docs/security/operational_canary_threat_model.md), and
[ADR-0001](docs/adr/0001-erpguard-evolution.md).

## Quickstart and focused verification

```bash
uv sync --extra dev
python -m pytest tests/test_phase9_process_package.py tests/test_phase10_variant_discovery.py tests/test_phase11_candidate_branching.py -q
```

The full suite is intentionally not part of the quickstart command. Browser
dependent tests may be skipped when Chromium is unavailable.

## Roadmap

`ROADMAP.md` tracks what's completed vs. next in one place; the detailed,
phase-by-phase engineering narrative that used to live here moved to
[docs/architecture/phase_narrative.md](docs/architecture/phase_narrative.md)
(current-system detail, not historical material -- see that file's own
note). The exact phase gates and no-goals are defined in the
[master implementation specification](docs/specs/84_erpguard_evolution_master_spec.md).

## Definition of Done (Spec 95, TFM)

Phase 22 (Spec 95) restructures this section around the actual TFM
Definition of Done rather than a chronological narrative. Full checklist,
including the items that need human judgment and are deliberately **not**
claimed here as done: [docs/specs/95_phase22_tfm_delivery_and_release_freeze.md](docs/specs/95_phase22_tfm_delivery_and_release_freeze.md).
Mechanically-checkable status: `tests/test_phase22_definition_of_done.py`.

- [x] Baseline frozen, full tests reproducible (990 tests, CI green on
      every push -- Python 3.11 + 3.13, PostgreSQL with a downgrade/upgrade
      cycle, Docker build, secret scan, frontend build, dependency scan +
      SBOM + benchmark smoke + docs link check).
- [x] Authentication and tenant enforcement exist (bearer tokens,
      tenant-scoped queries everywhere) -- **but no production-grade
      login/identity-provider exists**; `POST /internal/dev-tokens` is an
      explicit, non-production bootstrap (Spec 94).
- [x] Connector SDK v2, Fake/OCEL/Odoo plugins, OCEL import/export, Odoo
      read path, Quote-to-Order process package, variant discovery,
      candidate v2, deterministic historical replay, regression
      detection, Proof of Improvement, Process-to-Skill compiler v2,
      signed single-use permits.
- [x] Real Odoo quotation draft works in staging; retry creates no
      duplicate; postconditions verified; confirmation safely executed
      or correctly blocked; shadow mode demonstrated.
- [x] Governed recommendation lifecycle, operational canary router,
      non-causal outcome measurement, sealed decision-to-outcome
      evidence bundle (Spec 92 Workstreams A-D).
- [x] Benchmark compares three configurations and stores raw results
      (Spec 93 -- see `docs/tfm/annexes/00_index.md`).
- [x] New web journey works, including the decision-to-outcome pillar
      (Spec 94).
- [x] Clean install works against Fake ERP data
      (`docker-compose.demo.yml` + `scripts/validate_demo_install.py`)
      -- **except the decision-to-outcome pillar**, which currently has
      no Fake-ERP path (every `MarginOpportunity` requires a real
      Odoo-derived analytical snapshot; see
      [docs/tfm/annexes/installation.md](docs/tfm/annexes/installation.md)).
- [ ] Memory within 20 pages, video within 5 minutes, bibliography and
      annexes complete, repository permissions correct -- all pending
      the thesis author's own review (`docs/tfm/memoria_draft.md` is an
      explicit **draft**, not final).
- [x] `v1.0.0-tfm` tag created (see
      `docs/tfm/annexes/code_and_repository.md`).

## Known gaps (consolidated)

- The decision-to-outcome pillar has no Fake-ERP/fixture entry point
  (above).
- `false_block_rate` for the governed configuration is 16.7% in the Sec
  93 benchmark (`docs/benchmark/reports/`) -- a real, measured cost of
  the conservative design, not zero-cost safety.
- Only `formula_guard` has a real decision evaluator; `approval_gate` and
  7 of 11 Sec 16 regression categories have none.
- `direct_tool_agent` (the ungoverned LLM baseline) requires a real
  `ANTHROPIC_API_KEY` and was not run with one in the benchmark result
  cited in `docs/tfm/memoria_draft.md`.
- No data erasure/retention tooling exists (`docs/tfm/annexes/data_rights_and_gdpr.md`).
- `web/e2e/` Playwright specs are unexecuted against a live backend this
  session (syntax-verified only).

## Limitations

- Odoo JSON-2/live staging integration still requires deployment credentials and
  network access.
- The Odoo bridge and polling endpoints are controlled ingestion seams, not an
  autonomous webhook listener or background poller.
- Variant discovery now uses relational event/object links; migration `0007`
  backfills existing OCEL rows before large-scale benchmarking.
- Candidate branching has no activation path or replay path; submitted candidates are tenant-isolated and immutable.
- No raw ERP execution or ERP write capability is enabled.
- The internal route surface is not mounted by default; the controlled demo
  requires the explicit internal-surface flag. The legacy composition root
  was deleted entirely in wave C6 and cannot be re-enabled.
- The public connection path resolves SDK v2 definitions and uses
  `credential_ref`; there is no separate connector setup/auth/credential
  compatibility surface anymore.
- The decision-to-outcome pillar (Spec 92) has no Fake-ERP/fixture entry
  point: every `MarginOpportunity` requires a real, Odoo-derived
  analytical snapshot. `scripts/validate_demo_install.py` exercises the
  full existing pillar against Fake ERP data but explicitly does not
  exercise recommendations/canary/outcomes/evidence for this reason.
- No production-grade authentication exists. `POST /internal/dev-tokens`
  (Spec 94) is a scoped, internal-only bootstrap explicitly documented as
  non-production, gated the same way `/demo` is.

## Legacy release history

Historical v0.12/v0.13 release-candidate and sprint-era material is preserved
in [docs/legacy/releases.md](docs/legacy/releases.md). It is traceability
material, not the current product contract.

## License

MIT. See [LICENSE](LICENSE).
