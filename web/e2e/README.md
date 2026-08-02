# Spec 94 Playwright E2E

Not wired into the `frontend` CI job -- standing up the full backend
(Postgres, migrations, a running FastAPI process) inside the frontend job
is disproportionate for a TFM-scope product, and both specs here already
require `ERPGUARD_INTERNAL_SURFACES=true` for the dev-token bootstrap.
This is a documented manual/local verification path, not a CI gate.

## Run locally

```bash
# terminal 1 -- backend, with internal surfaces on for the dev-token bootstrap
ERPGUARD_INTERNAL_SURFACES=true uvicorn apps.api.main:app --port 8000

# terminal 2 -- frontend build + browsers + tests
cd web
npm run build
npx playwright install --with-deps chromium
npm run e2e
```

## Coverage

- `operational-path.spec.ts` -- connect (create a Fake ERP connection) ->
  ingest (fake-generate events) -> inspect variants, then confirms the
  replay/deployments/runs screens are reachable. Does not walk
  replay -> proof -> compile -> execute end-to-end: that chain requires a
  registered process definition and a submitted, compiled candidate,
  which is exercised by the backend's own integration tests
  (`tests/test_backend_rc_end_to_end.py` and the Phase 12-15 suites).
- `decision-to-outcome-path.spec.ts` -- confirms every screen in the
  opportunity -> recommendation -> canary -> outcome -> evidence pillar
  is reachable and renders its safety-critical copy (the "enrutar por
  canary" toggle, the evidence bundle section). Does not fabricate a full
  margin-analysis precondition chain to reach a real opportunity.
