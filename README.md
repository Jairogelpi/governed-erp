# ERPGuard Evolution v0.14.0

ERPGuard Evolution is a versioned, testable and governed platform for
understanding and improving ERP business processes. It keeps ERP effects behind
explicit safety boundaries: the current implementation is read-only or
simulated, and raw ERP writes are disabled.

> Current project state: **Phase 11 — Candidate branching**.

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
  → immutable process candidates
```

The repository can currently:

- discover Fake and Odoo Connector SDK v2 plugins through entry points;
- import/export tenant-scoped canonical events and keep ingestion cursors;
- normalize controlled Odoo bridge payloads with correlation and provenance labels;
- validate and version the Quote-to-Order baseline process;
- group canonical event traces into variants with counts and durations;
- create evidence-backed process candidates without activation.

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

Open [http://127.0.0.1:8000/demo](http://127.0.0.1:8000/demo) for the existing
operator dashboard. The current Phase 10/11 API surfaces are:

```text
GET  /v1/variants?object_type=sales_order
GET  /v1/variants/dashboard
GET  /v1/variants/cases/{case_id}
POST /v1/process-candidates
POST /v1/process-candidates/{candidate_id}/submit
```

There is no bundled GIF asset yet; the dashboard and JSON API are the current
reproducible demo surfaces.

## Architecture and reality labels

- `real`: identity boundaries, migrations, encrypted local secrets, canonical
  storage, validation, registry/versioning, variant projection and candidate
  immutability.
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

Completed: Phases 0–11, from baseline freeze through candidate branching.

Next: Phase 12 historical replay, then regression/proof gates, process-to-skill
compilation, governed execution permits, controlled quotation flow, shadow and
canary operation, experiments, product web experience and public release freeze.

The exact phase gates and no-goals are defined in the [master implementation
specification](docs/specs/84_erpguard_evolution_master_spec.md).

## Limitations

- Odoo JSON-2/live staging integration still requires deployment credentials and
  network access.
- The Odoo bridge and polling endpoints are controlled ingestion seams, not an
  autonomous webhook listener or background poller.
- Variant discovery now uses relational event/object links; migration `0007`
  backfills existing OCEL rows before large-scale benchmarking.
- Candidate branching has no activation path.
- No raw ERP execution or ERP write capability is enabled.

## Legacy release history

Historical v0.12/v0.13 release-candidate and sprint-era material is preserved
in [docs/legacy/releases.md](docs/legacy/releases.md). It is traceability
material, not the current product contract.

## License

MIT. See [LICENSE](LICENSE).
