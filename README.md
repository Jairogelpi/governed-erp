# ERPGuard Evolution v0.14.0

ERPGuard Evolution is a versioned, testable and governed platform for
understanding and improving ERP business processes. It keeps ERP effects behind
explicit safety boundaries: almost everything is read-only or simulated.
The one exception is a single, narrowly-scoped, permit-gated write
(`quote.create_draft` -- create a draft sales quotation, nothing else) added
in Phase 16; there is no generic "raw ERP write" capability anywhere.

> Current project state: **Phase 16 - Real quotation draft (Odoo)**.

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

Completed: Phases 0–16, from baseline freeze through the candidate
integrity gate, controlled API composition, connector convergence, the
full product consolidation (Phase 11.5 C0–C8), historical replay, the
regression engine / Proof of Improvement, the skill compiler, the
execution permit runtime, and the first real business write:

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

Phase 13 — Regression engine and Proof of Improvement (master spec sections
16/17): `erpguard/domain/proofs/` classifies regressions between two replay
runs and generates an immutable Proof of Improvement. Given this codebase's
single real policy evaluator (`formula_guard`, binary block/allow), only 4
of the spec's 11 regression categories are genuinely detectable —
`new_unsafe_effect` (critical: a decision the baseline blocked is now
allowed), `false_block` (low: the reverse, surfaced for review not assumed
an improvement — no ground truth to tell), `evidence_incompleteness`
(medium), `postcondition_failure` (medium). The other 7 (duplicate
detection, entity resolution, approval count, fingerprint, latency, token
metrics) have no detector here and are never emitted — documented in
`regression_classifier.py`'s module docstring. Eligibility (17.3): 2 of the
7 criteria are structurally unmeasurable (duplicate-prevention rate,
test-suite pass/fail) and there's no reviewer-decision field in the spec's
own `ProofOfImprovement` model to invent an approval workflow around, so
this implementation's ceiling is `eligible_for_shadow` — it never
recommends `eligible_for_canary`/`eligible_for_promotion`. Any critical
regression → `reject`. API: `POST /v1/replays/{id}/proofs`,
`GET /v1/proofs/{id}` (spec 23.5). Proofs are permanently immutable from
creation (17.4) — no freeze verb, updates are always rejected.

Phase 13.1 — Replay and Proof integrity (review-driven hardening, not in
the master spec's phase list): two gaps found after Phase 12/13 landed.
(1) Declared process decisions with no evaluator were silently skipped, so
a case could read "passed" having only evaluated part of the process. The
replay engine now tracks `declared_decision_count`/
`evaluated_decision_count`/`unsupported_decisions`/`decision_coverage_rate`
per case and forces `needs_clarification` whenever coverage is incomplete;
`ProofService` requires full coverage across every matched case before it
will ever recommend `eligible_for_shadow`. (2) The immutable-after-freeze
listener covered `ProcessReplay` but not `ProcessReplayCase` — freezing a
replay's header didn't stop its case rows from changing underneath it.
Added `before_update`/`before_delete` listeners on the case table that
check the parent replay's frozen status via the connection (no ORM
relationship exists between the two tables). `ProofService` also now
requires both replays to be `status="frozen"`, not merely `"completed"`,
before generating a proof. Migration `0012` adds the coverage columns.

Phase 14 — Process-to-Skill compiler v2 (master spec section 18):
`erpguard/domain/skills/` compiles a submitted `ProcessCandidate` with an
acceptable `ProcessProof` into a versioned `SkillPackage`. Real, checkable
validation for 4 of spec 18.3's items — capability existence / no raw
native methods (every workflow-step capability must exist in the target
connector's `capability_definitions()`), policy references resolve, proof
acceptability (recommendation not `reject`/`needs_changes`), package hash
reproducibility. Everything else (fingerprint requirements, postconditions,
compensation, idempotency strategy, full JSON Schema validation) ships as
documented structural placeholders, not fabricated passes — this
codebase's connectors are all read-only, so "postconditions/idempotency
for writes" is vacuously satisfied by construction, and compilation is
rejected outright if a step ever claims write capability (nothing exists
to check a postcondition against). Only `draft → compiled → approved` is
implemented; `shadow`/`canary`/`active`/`rolled_back`/`deprecated` need a
live execution/deployment runtime that doesn't exist yet (Phase 15+). API:
`POST /v1/process-candidates/{id}/compile` (this repo's real candidate
prefix, not the spec's literal `/v1/candidates`),
`GET`/`POST /v1/skills/{skill_id}/versions/{version_id}[/approve]` (spec
23.6) — the legacy v0 skills router (`apps/api/routes/public_v1/skills.py`)
is untouched and has no `/versions/` path segment, so there's no collision.

Phase 15 — Execution Permit runtime (master spec section 19): a "Run"
(`ExecutionRun`) carries a permit through `planned → approved → executed`,
or `revoked`. `plan()` builds the ActionPlan from an approved `SkillPackage`
and computes reproducible operation/native-plan/state-snapshot hashes.
`approve()` binds single-use `Approval` records and HMAC-signs the permit
(same primitive `erpguard/domain/identity/auth.py` uses for bearer tokens).
`execute()` re-verifies every spec 19.4 rejection reason against *current*
state — not just trusting plan/approve-time validity — before calling the
connector: signature/tamper detection, expiry, single-use (reused),
revocation, tenant/connection/capability matching, and single-use approval
binding are all real, enforced checks. `unsupported_fingerprint` is always
`not_checked` — no connector-agnostic fingerprint-requirement schema
exists anywhere in this codebase, same gap Phase 14 documented for
compilation. The connector SDK's `ConnectorPlugin` protocol is untouched;
`execute()` adapts the rich domain permit into the SDK's simple placeholder
at the connector call boundary. Since Phase 17, terminal run status reports
the actual outcome (`succeeded`, `blocked`, `failed`, or `unknown`) rather
than calling every connector attempt `executed`. Kill switch: a real,
tenant-scoped on/off flag checked at
both plan and execute time, not a broader circuit-breaker system. API:
spec 23.7's `POST /v1/runs/plan`, `GET /v1/runs/{id}`,
`POST /v1/runs/{id}/approve`, `POST /v1/runs/{id}/execute`, plus two
documented additions (`POST /v1/runs/{id}/revoke`,
`POST /v1/runs/kill-switch`) and `POST /v1/approvals` (fills the
previously-empty stub). `.../evidence` and `.../compensate` (also in 23.7)
are out of scope — no live Evidence Pack or compensation-planning logic
exists yet.

Phase 16 — Real quotation draft (Odoo, master spec Phase 16): closes the
first real business write. `erpguard/connectors/odoo/plugin.py` declares
exactly one write-capable capability, `quote.create_draft`
(`supports_execution=True`); at the Phase 16 baseline every other capability
was read-only and no confirmation method existed, so that phase's
"no invoice/picking/confirmation" boundary held by construction. Idempotency is
real: `execute_capability` searches by `client_order_ref` before creating,
so a retry with the same reference returns the existing order rather than
a duplicate. Postconditions are real: `verify_execution` reads the order
back and confirms `state == "draft"`. `ConnectorApplicationService
.connection_context()` now wires up real credential resolution for the
first time — it unseals a connection's secret via the existing
`EncryptedLocalSecretProvider` vault and builds an Odoo transport factory
from it; this infrastructure existed since the connections phase but had
never been connected end-to-end for any connector before now. Verified
live once against a real Odoo 19 staging instance (credentials supplied
out-of-band, never committed): one real draft `sale.order` created and
independently confirmed (`state=draft`, no invoice, no delivery); a retry
with the same client reference correctly found the existing order and
performed no write. Automated suite coverage uses injected fake
transports, never a live call.

Phase 17 — Governed confirmation: adds the bounded
`sales.order.confirm` capability and no generic Odoo RPC execution. Planning
reads and persists the live order/line/picking/invoice snapshot, enforces an
R3 preflight (explicit feature flag, staging-only connection, configurable
amount ceiling, allowed state, forbidden marker and no pre-existing
invoices), predicts downstream effects conservatively, and binds the
snapshot hash into the native plan and signed permit. Approval must be
non-empty, single-use, issued by a different actor, bound by exact scope to
the run/capability/snapshot, and no older than 900 seconds. Execution is
restricted to the actor who planned the run. State is re-read before
approval, by the runtime before execution, and by the connector
immediately before `action_confirm`; any drift blocks without writing.
Successful execution verifies the confirmed state, order identity,
unexpected-invoice boundary and generated picking IDs. Terminal outcomes
seal a tenant-scoped Evidence Pack available at
`GET /v1/runs/{run_id}/evidence`; a read-only manual cleanup strategy is
available at `GET /v1/runs/{run_id}/cleanup-plan`. Automatic rollback is
deliberately not claimed because confirmation may launch logistics,
procurement or manufacturing.

The real capability is fail-closed by default:
`ERPGUARD_ALLOW_ODOO_GOVERNED_CONFIRMATION=false`. Automated coverage uses
an injected staging transport and proves both success and controlled block
paths. One separately authorized live Odoo 19 staging experiment confirmed
an isolated test order but also triggered an unexpected auto-posted invoice.
ERPGuard detected that forbidden postcondition and marked the run `failed`.
After separate operator authorization, the uncompleted picking was cancelled,
the invoice was compensated with a posted linked credit note, and the order
was cancelled; accounting residuals and net document total were verified at
zero. This is compensation rather than rollback. The sanitized evidence is
in
[`docs/demo/phase17_governed_confirmation_live_staging_evidence.json`](docs/demo/phase17_governed_confirmation_live_staging_evidence.json).
The feature flag remains disabled by default.

Phase 17.1 hardens that incident into a permanent control contract. Every
confirmation now carries a versioned side-effect budget, bounded read-only
automation fingerprint and structured CompensationPlan. Approval and permit
bind both the order snapshot and control-contract hash. Incomplete
fingerprints or later fingerprint drift block before the write; observed
invoice/payment/purchase/manufacturing effects or model creation ceilings
reject success. The incident-derived posted-invoice regression remains in
the automated suite. Phase 17.1 adds no compensation execution or other ERP
write.

Phase 18 — Shadow Mode is now implemented as an effects-free evaluation
surface. A submitted valid candidate backed by an `eligible_for_shadow`
Proof of Improvement can be deployed in status `shadow`. Incoming staged or
replayed cases are evaluated by the same deterministic Replay Engine against
the active and candidate definitions; both decisions, normalized
differences, optional observed outcome and append-only reviewer labels are
stored. The dashboard applies a deployment-specific agreement threshold but
cannot promote or activate a version. The Shadow Service has no connector,
Odoo, permit or execution-runtime dependency and creates no `ExecutionRun`.
The selected sanitized disagreement is in
[`docs/demo/phase18_shadow_mode_selected_example.json`](docs/demo/phase18_shadow_mode_selected_example.json).

Next: Decision Intelligence Foundation or Phase 19 canary/promotion design.
No canary routing, activation, promotion or rollback is implemented yet.

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
