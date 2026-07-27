# Database migrations

Phase 2 introduces Alembic without deleting or rewriting the existing SQLAlchemy models.

## Commands

```bash
alembic upgrade head
alembic current
```

The URL comes from `ERPGUARD_DATABASE_URL`; otherwise Alembic uses the SQLite URL in `alembic.ini`. Deployment should run `alembic upgrade head` before starting the API.

## Baseline policy

Revision `0001_baseline` creates missing tables from the current SQLAlchemy metadata and leaves existing rows untouched. Its downgrade is intentionally non-destructive because dropping the accumulated legacy schema would be unsafe. Future revisions must use explicit bounded migrations and must not add new models to `erpguard/db/models.py`.

## Persistence boundary

`erpguard.db.model_packages` is the first bounded model package. `ProcessDefinition` is storage-only in Phase 2: it has no public endpoint, repository, activation or execution behavior. Future process lifecycle work must arrive in its own approved phase.

## PostgreSQL reality label

`staging_only`: CI provisions PostgreSQL 16 and runs the migration smoke tests. This local Windows session had no PostgreSQL daemon, so local PostgreSQL execution was not claimed.

