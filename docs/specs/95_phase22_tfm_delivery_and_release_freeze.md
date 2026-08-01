# Phase 22 — TFM Delivery and Release Freeze

Operationalizes master spec §22.4 (old dashboard retirement, cross-ref),
§31.3 (clean-install acceptance), §32 (CI/CD), §38 (README final
structure), §39 (TFM deliverables), §40/§40.1 (release versions and
calendar), §41 (Definition of Done — TFM), §42 (Definition of Done —
public beta). This is the phase with no code of its own — it freezes,
documents and packages everything Phases 0-21 and Spec 92 already built.

## Problem

Everything so far has been "does the feature work." This phase answers
"can a stranger install it, verify it, and read the thesis without
guessing" — the two audiences are the TFM committee (memory + video +
annexes) and a public-beta reader (README + clean install + license).
Nothing here should require touching implementation code; if it does,
that's a sign an earlier phase's exit criteria weren't actually met.

## Design

### Memory (§39.1)

Max 20 pages excluding cover/index/annexes, allocation:

```text
1.0  Executive summary
1.5  Problem and objectives
2.0  State of the art
2.0  Research design
3.0  Architecture
2.5  Implementation
4.0  Experiment and results       <- Phase 20's report, cited not restated
1.5  Security and interpretability <- docs/security/*, Sec 25/26 threat models
1.0  Product value
1.0  Limitations and conclusions   <- every "Known gaps" section across specs 84-95, consolidated
0.5  Bibliography
```

The "Experiment and results" chapter must cite `BenchmarkRun` ids and the
exact report artifact, never restate numbers by hand — same "report
generated from data, not edited manually" discipline Phase 20 enforces on
itself, extended to the memory that quotes it.

### Annexes (§39.2)

Full spec (all of `docs/specs/84_*.md` through this one) · schemas
(OpenAPI export) · Connector SDK · process package · benchmark (dataset
manifest + report) · raw results (`BenchmarkCaseResult` export) · prompts
(the `direct_tool_agent` system prompt, verbatim, since it's the one LLM
prompt in the entire system) · Evidence Packs (one sample `ExecutionRun`
evidence pack, one sample `DecisionOutcomeEvidenceBundle` export, both
sanitized) · threat model (`docs/security/`) · installation (this
document's clean-install section) · code/repository (commit hash + tag) ·
data rights · GDPR analysis · test reports (final `pytest`/CI output).

### Five-minute video (§39.3) and demo sequence (§39.4, extended)

Timing unchanged from §39.3. Demo sequence extends the original 10 steps
with the Spec 92 pillar so the video actually shows the product's second
half, not just the pre-Spec-92 path:

```text
1.  Connect Odoo.
2.  Import/seed process history.
3.  Show variants.
4.  Compare baseline and candidate.
5.  Run replay.
6.  Show Proof of Improvement.
7.  Compile skill.
8.  Create real Odoo draft.
9.  Show block/approval for confirmation.
10. Show Evidence Pack and duplicate prevention.
11. Show a margin opportunity and its governed recommendation.
12. Show independent approval and canary-routed execution.
13. Show the realized outcome report and its non-causal disclaimer.
14. Show the sealed, verified Decision-to-Outcome evidence bundle.
```

Given the 5-minute budget (§39.3: 1:25-3:20 is the entire demo block,
~115 seconds for 14 steps), the video must use the pre-recorded live-Odoo
evidence already captured
(`docs/demo/backend_rc_live_pricing_scenario_evidence.json`,
`docs/demo/backend_rc_decision_to_outcome_evidence.json`) rather than
performing a second live Odoo write on camera — same non-repudiation, less
demo risk.

### Release versions (§40, unchanged) and tagging

```text
v0.13.0-rc1        historical ERPGuard candidate
v0.14.0            migration foundation
v0.15.0            Connector SDK + events
v0.16.0            process/version/mining
v0.17.0            replay/proof
v0.18.0            compiler/runtime v2
v0.19.0            Odoo quote vertical + Spec 92 decision-to-outcome backend
v0.20.0            shadow/canary + benchmark (Phase 20)
v1.0.0-tfm         immutable TFM release
v1.0.0-beta.1      public beta presentation
```

(Spec 92's four workstreams landed inside the `v0.19.0` window rather than
getting their own version bump — versions "may be consolidated but must
be consistent," §40.)

### Clean-install acceptance (§31.3)

```bash
docker compose -f docker-compose.demo.yml up --build
python scripts/validate_demo_install.py
```

`validate_demo_install.py` (new) asserts: application healthy, demo
seeded, variant discovery works, replay works, Proof generated, skill
compiled, Fake execution works — and, extending the original checklist for
Spec 92: a recommendation can be created/approved, a canary policy can be
activated, an outcome report can be evaluated, and an evidence bundle can
be sealed and verified, all against Fake ERP data seeded by the same
compose file. No live Odoo credentials required for this path — matches
every other "demo" surface in this repository.

### CI/CD (§32) — gate additions this phase closes

Compared against §32.1's pull-request-pipeline list, this repository's CI
(`.github/workflows/ci.yml`) already has: lint, type check, unit/contract/
integration tests (the full `pytest` run), secret scan (added this
delivery), migration test (SQLite + PostgreSQL, both with a
downgrade/upgrade cycle), and container build. Phase 22 adds the
remainder: dependency scan (`pip-audit` or `uv pip audit` as a new CI
step), build web (Phase 21's `vite build`, already speced there), SBOM
generation (`cyclonedx-py` or `syft` against the built image), benchmark
smoke (`erpguard_candidate` config only, a handful of cases, not the full
120×3×N — a fast confidence check, not a re-run of Phase 20's actual
experiment), docs link check (`lychee` or equivalent over `docs/`).

Release gate (§32.3) blocks on: version mismatch, red CI, no benchmark
artifact, no SBOM, secret found, clean-install failure, demo-path failure,
missing current/simulated capability matrix
(`docs/architecture/capability_reality_matrix.md`, already maintained),
unresolved critical regression.

### README final structure (§38)

Rewrite `README.md`'s top section around the Definition of Done items
below rather than the current chronological phase-by-phase narrative
(which stays, moved to `docs/legacy/` or kept as an appendix link, same
"legacy release history" pattern this README already uses for pre-Phase-0
material).

## Definition of Done — TFM (§41, extended with Spec 92 items)

- [ ] Baseline frozen.
- [ ] Full tests reproducible.
- [ ] PostgreSQL and migrations work (including downgrade/upgrade).
- [ ] Authentication and tenant enforcement exist.
- [ ] Real secret provider exists.
- [ ] Connector SDK v2 exists.
- [ ] Fake, OCEL, and Odoo plugins exist.
- [ ] OCEL import/export works.
- [ ] Odoo read path works.
- [ ] Quote-to-Order process package exists.
- [ ] Variants are discovered.
- [ ] Candidate v2 exists.
- [ ] Historical replay is deterministic.
- [ ] Regressions are detected.
- [ ] Proof of Improvement is generated.
- [ ] Process-to-Skill compiler v2 works.
- [ ] Signed single-use permits work.
- [ ] Real Odoo quotation draft works in staging.
- [ ] Retry creates no duplicate.
- [ ] Postconditions are verified.
- [ ] Confirmation is safely executed or correctly blocked.
- [ ] Shadow mode is demonstrated.
- [ ] **Governed recommendation lifecycle works (Spec 92 Workstream A).**
- [ ] **Operational canary router routes deterministically (Spec 92 Workstream B).**
- [ ] **Outcome measurement produces a non-causal realized-value report (Spec 92 Workstream C).**
- [ ] **Decision-to-Outcome evidence bundle seals and verifies (Spec 92 Workstream D).**
- [ ] Benchmark compares three configurations.
- [ ] Raw results are stored.
- [ ] New web journey works, including the decision-to-outcome pillar.
- [ ] Clean install works.
- [ ] Memory is within 20 pages.
- [ ] Video is within 5 minutes.
- [ ] Annexes and repository permissions are correct.
- [ ] Tag `v1.0.0-tfm` exists.

## Definition of Done — public beta (§42, unchanged)

- [ ] Public-safe history scan completed.
- [ ] No secret in git history.
- [ ] Apache-2.0 or approved license.
- [ ] README hero demo.
- [ ] Docker demo works.
- [ ] Benchmark report shown.
- [ ] Connector template works.
- [ ] `good first issue` set exists.
- [ ] Security policy exists.
- [ ] SBOM exists.
- [ ] Release artifact exists.
- [ ] No unsupported uniqueness claim.
- [ ] Odoo limitations clearly stated.
- [ ] Telemetry is absent or opt-in.

## Test plan

- `scripts/validate_demo_install.py` — new, drives the extended
  clean-install acceptance list above; exits non-zero on any failure with
  a named reason, matching `scripts/validate_rc_demo.py`'s existing
  structured-output convention.
- `tests/test_phase22_docs_contract.py` — asserts every annex file listed
  in §39.2 exists at the expected path before allowing the release-gate
  script to report success (same pattern as
  `tests/test_release_docs_contract.py`, extended to the new annex list).
- `tests/test_phase22_definition_of_done.py` — a single test that runs
  every TFM DoD checklist item above as an assertion where one is
  mechanically checkable (tag exists, files exist, CI green via `gh api`)
  and lists the rest as documented manual-verification steps in its
  docstring, not silently skipped.

## Exit criteria (§Phase 22, verbatim)

- no feature work after freeze;
- links tested;
- repository access tested;
- submission package verified.

## Out of scope

Any new product feature (this phase is packaging and evidence only — if
something is missing here, it means an earlier phase's exit criteria
weren't actually met, and the fix belongs in that phase's spec, not this
one) · public beta execution itself (§42's checklist is prepared here but
`v1.0.0-beta.1` is explicitly a separate, later release per §40 — this
phase only proves `v1.0.0-tfm` is submittable) · any claim of guaranteed
commercial ROI, universal ERP support, or autonomous optimization (§29 of
the master spec and §5 "Definition of success" of Spec 92 already forbid
these; this phase's README/video copy must not reintroduce them under
release-messaging pressure).
