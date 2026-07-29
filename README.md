# ERPGuard Evolution v0.14.0

ERPGuard Evolution is a versioned, testable and governed platform for
understanding and improving ERP business processes. It keeps ERP effects behind
explicit safety boundaries: the current implementation is read-only or
simulated, and raw ERP writes are disabled.

> Current project state: **Phase 12 - Historical replay**.

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

Set `ERPGUARD_INTERNAL_SURFACES=true` before starting the API and open
[http://127.0.0.1:8000/demo](http://127.0.0.1:8000/demo) for the existing
operator dashboard. The current public API surfaces are:

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

## Architecture and reality labels

- `real`: identity boundaries, migrations, encrypted local secrets, canonical
  storage, validation, connector registry/runtime convergence, variant
  projection, candidate immutability and public/internal app composition
  boundaries.
- `fixture`: FakeConnector, Fake ERP data and local process/variant fixtures.
- `staging_only`: real Odoo read-only transport paths and live smoke checks.
- `planned`: historical replay, regression gates, skill compilation v2,
  execution permits, governed writes and the product web experience.

Read the [current architecture inventory](docs/architecture/current_inventory.md),
[capability reality matrix](docs/architecture/capability_reality_matrix.md),
[master specification](docs/specs/84_erpguard_evolution_master_spec.md), and
[ADR-0001](docs/adr/0001-erpguard-evolution.md).

## Quickstart and focused verification

```bash
uv sync --extra dev
python -m pytest tests/test_phase9_process_package.py tests/test_phase10_variant_discovery.py tests/test_phase11_candidate_branching.py -q
```

The full suite is intentionally not part of the quickstart command. Browser
dependent tests may be skipped when Chromium is unavailable.

## Roadmap

Completed: Phases 0–12, from baseline freeze through the candidate
integrity gate, controlled API composition, connector convergence, the
full product consolidation (Phase 11.5 C0–C8), and historical replay:

- C0 inventory
- C1 composition root
- C2 connector convergence
- C2.5 quality gate (mypy clean)
- C3 evolution routes moved to their final `public_v1` location
- C4 skills/identity routes finalized; recording/replay pipeline extracted
  out of `erpguard/product`
- C5 dead repository function pruning (`erpguard/db/repositories.py`
  6699 → 1631 lines)
- C6 legacy composition root and unreachable code deleted
- C7 migration-scaffolding retirement
- C8 final consolidation gate (ruff, mypy, pytest, alembic all green)
- C8.1 read-only ORM/schema audit of `erpguard/db/models.py` (see
  [docs/architecture/c8_1_orm_schema_audit.md](docs/architecture/c8_1_orm_schema_audit.md))
- C8.2 retired-schema migration: manually skimmed the 40 live tables'
  `*_id`/`*_ref`/`*_key` columns for by-convention references the audit's
  FK-only check couldn't see (found 4: `write_impact_previews`,
  `write_rollback_plans`, `write_pilot_requests`,
  `r2_write_pilot_requests` are still referenced and were kept); dropped
  the remaining 95 tables and their ORM classes in
  `migrations/versions/0009_drop_retired_tables.py`
  (`erpguard/db/models.py` 2831 → 900 lines); `erpguard/product` deleted
  entirely, everything now lives in `erpguard/release_ops`

The 0009 migration is destructive for data: `downgrade()` recreates the
95 tables empty (schema only) but cannot restore dropped rows. Verified
locally: fresh-empty-db upgrade path, existing-db-with-data upgrade path
(rows in two sample tables confirmed gone after upgrade), and downgrade
path (tables recreated, zero rows) — all against SQLite. Not verified
locally against PostgreSQL or via `docker build` (no local Postgres/Docker
in this environment); both run in CI on every push.

Phase 12 — Historical replay (master spec section 15): `erpguard/domain/replays/`
executes a registered process version over already-ingested canonical events
for a given object_type and evaluates the process's declared decisions
against them (`formula_guard` is the only decision with a real evaluator
today; others declared in a process definition are skipped, not faked). No
LLM is invoked anywhere in the replay path and no connector plugin is ever
called, so "no source ERP write" holds by construction rather than needing a
dedicated simulator. `deterministic_trace_hash` is verified deterministic
by a repeatability test (same dataset/version/policy twice → identical hash
per case). API: `POST /v1/processes/{key}/versions/{version}/replays`,
`GET /v1/replays/{id}`, `GET /v1/replays/{id}/cases`,
`GET /v1/replays/{id}/comparison?baseline_replay_id=...`,
`POST /v1/replays/{id}/freeze` (immutable once frozen, same pattern as
process candidates). The comparison endpoint is a minimal hash/status diff
between two replay runs, not the regression taxonomy from master spec
section 16 — that's Phase 13's job. No UI in this pass.

Next: Phase 13 — Regression engine and Proof of Improvement.

The exact phase gates and no-goals are defined in the [master implementation
specification](docs/specs/84_erpguard_evolution_master_spec.md).

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

## Legacy release history

Historical v0.12/v0.13 release-candidate and sprint-era material is preserved
in [docs/legacy/releases.md](docs/legacy/releases.md). It is traceability
material, not the current product contract.

## License

MIT. See [LICENSE](LICENSE).
