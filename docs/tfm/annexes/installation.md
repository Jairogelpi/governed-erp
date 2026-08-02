# Installation annex (Spec 95 Sec 39.2 / Sec 31.3)

Two supported paths; both operate on Fake ERP / synthetic data only, no
live Odoo credentials required.

## 1. Clean-install acceptance (Docker Compose)

```bash
docker compose -f docker-compose.demo.yml up --build -d
python scripts/validate_demo_install.py
docker compose -f docker-compose.demo.yml down -v
```

`validate_demo_install.py` drives the real golden path over HTTP against
the running container -- process registration, Fake-ERP event seeding,
variant discovery, candidate creation, replay, freeze, Proof of
Improvement, skill compilation, approval, and execution-permit
plan/approve/execute. It explicitly does **not** exercise the
decision-to-outcome pillar (opportunity -> recommendation -> canary ->
outcome -> evidence bundle) -- see the script's own module docstring and
this repository's capability reality matrix for why: every path to a
`MarginOpportunity` currently requires a real Odoo-derived analytical
snapshot, and no Fake-ERP/fixture equivalent exists yet.

## 2. Local development install

```bash
uv sync --extra dev
python -m alembic upgrade head
uvicorn apps.api.main:app --reload
```

Optionally build and serve the product web application (Spec 94):

```bash
cd web && npm ci && npm run build && cd ..
ERPGUARD_SERVE_FRONTEND=true uvicorn apps.api.main:app --reload
```

then open `http://127.0.0.1:8000/`.

## Environment variables that must be set for a working install

`ERPGUARD_AUTH_SECRET` and `ERPGUARD_LOCAL_SECRET_KEY` are both required
for authentication and the connections API to work at all -- a genuinely
fresh install with neither set will 503 on every authenticated request
(`authentication_not_configured`). `.env.example` documents safe,
non-production defaults; `docker-compose.demo.yml` sets demo-only values
directly (never reuse them for a real deployment).

## A gap this phase's validation work found and fixed

`erpguard.db.session.init_db()` (used by
`scripts/start_release_candidate.sh`/`.ps1` and this phase's
`docker-compose.demo.yml`) was missing four model-package imports
(`replay`, `proof`, `skill_package`, `execution`) -- a fresh SQLite
database built via `init_db()` alone would create every table except
`process_replays`, `process_replay_cases`, `process_proofs`,
`skill_packages`, `execution_runs` and `approvals`, crashing the moment
replay/proof/skill/execution was used. `python -m alembic upgrade head`
was never affected (all 27 migrations create every table correctly) --
this only broke the `init_db()` quick-start path, and was only caught by
actually running `validate_demo_install.py` against a live server this
phase. Fixed in `erpguard/db/session.py`.
