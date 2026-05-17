# 06 Database Schema Spec

**Parent spec references:** Sections 19, 20, 21, 24, 26.

## Purpose

Define Phase 1 persistence. The schema should work with SQLite for local development and PostgreSQL later.

## Tables

### connections

Stores ERP connection metadata. Secret handling must be designed so API responses never expose secrets.

```sql
CREATE TABLE connections (
    id TEXT PRIMARY KEY,
    erp_type TEXT NOT NULL,
    name TEXT NOT NULL,
    config_json TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

### preflight_cases

```sql
CREATE TABLE preflight_cases (
    id TEXT PRIMARY KEY,
    connection_id TEXT NOT NULL,
    actor_json TEXT NOT NULL,
    action_json TEXT NOT NULL,
    canonical_action TEXT NOT NULL,
    canonical_object TEXT NOT NULL,
    state_snapshot_json TEXT NOT NULL,
    simulation_json TEXT,
    decision TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    summary TEXT,
    created_at TIMESTAMP NOT NULL
);
```

### invariant_results

```sql
CREATE TABLE invariant_results (
    id TEXT PRIMARY KEY,
    preflight_case_id TEXT NOT NULL,
    invariant_id TEXT NOT NULL,
    invariant_type TEXT NOT NULL,
    status TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL
);
```

### audit_events

```sql
CREATE TABLE audit_events (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_json TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL
);
```

### policies

Policy persistence is optional in Phase 1 if policies are file-backed. The table should be included in the model design for later activation/versioning.

```sql
CREATE TABLE policies (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    canonical_action TEXT NOT NULL,
    canonical_object TEXT NOT NULL,
    erp_scope TEXT,
    industry_scope TEXT,
    policy_yaml TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

## Phase 1 Repository Requirements

- Create and list connections.
- Create preflight case.
- Create invariant results for a case.
- Create audit events for preflight decisions.
- Retrieve audit case by ID.

## Migration Requirement

Use a migration path compatible with Alembic, even if Phase 1 initially creates tables in tests through SQLAlchemy metadata.
