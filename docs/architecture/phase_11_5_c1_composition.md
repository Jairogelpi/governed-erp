# Phase 11.5 Wave C1 — Composition Root and Route Boundaries

Status: current runtime composition; legacy implementation remains available only through an explicit opt-in.

## Composition contract

`apps/api/main.py` is now a small composition root backed by
`apps/api/app_factory.py`:

- default `app` is created by `create_public_app()`;
- `ERPGUARD_INTERNAL_SURFACES=true` adds the controlled internal demo,
  Fake ERP, diagnostics and migration routers;
- `ERPGUARD_LEGACY_API_ENABLED=true` selects the explicit pre-C1 composition;
- `create_app(legacy=True)` is available for migration tests and does not alter
  the default production mode.

The public app disables the automatic docs/OpenAPI routes so the route surface
cannot grow outside the declared API whitelist accidentally.

## Public whitelist result

The public package is `apps/api/routes/public_v1/`. It owns the declared roots:

```text
/v1/health
/v1/identity
/v1/connections
/v1/connectors
/v1/events
/v1/processes
/v1/variants
/v1/process-candidates
/v1/replays
/v1/proofs
/v1/skills
/v1/approvals
/v1/executions
/v1/evidence
```

Connector, replay, proof, approval, execution and evidence modules are explicit
reserved boundaries in C1; no new capability was invented to fill them. The
existing skill, event, process, variant and candidate behavior is mounted
through named compatibility shims whose deletion waves are documented in the
module docstrings.

## Internal and legacy result

The internal package is `apps/api/routes/internal/` and is not mounted by
default. The pre-C1 route graph moved to `apps/api/legacy_app.py`; it is not
imported into the default router composition and is reachable only through the
explicit legacy flag/factory argument.

The browser demo therefore requires the internal flag in C1:

```powershell
$env:ERPGUARD_INTERNAL_SURFACES = "true"
uvicorn apps.api.main:app --reload
```

## Verification

```text
python -m pytest tests/test_phase115_composition_root.py -q
```

The focused C1 boundary slice passed (`3 passed`). Full regression was not run
in this continuation by user request. No runtime module was deleted, and no
replay, activation, ERP execution or ERP write capability was added.
