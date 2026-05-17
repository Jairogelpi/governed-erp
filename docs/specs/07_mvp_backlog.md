# 07 MVP Backlog Spec

**Parent spec references:** Sections 26, 27, 29.

## Purpose

Convert the parent spec backlog into an MVP sequence. Phase 1 is the only implementation plan currently authorized.

## Phase 1: ERPGuard Odoo Preflight Core

### Epic 1: Project Foundation

- Initialize Python/FastAPI project.
- Add test framework.
- Add configuration.
- Add app startup and health endpoint.

### Epic 2: Persistence Foundation

- Configure SQLite/PostgreSQL-compatible SQLAlchemy.
- Add models for connections, preflight cases, invariant results, audit events, and policy metadata.
- Add repositories.

### Epic 3: Canonical Model

- Add Pydantic models for Company, Customer, Product, SalesOrderLine, and SalesOrder.
- Add enums for state, product type, tracking, route policy, and invoice policy.
- Add fixtures representing Odoo-derived sales orders.

### Epic 4: Odoo Adapter Boundary

- Define adapter interface.
- Add Odoo adapter shell/read boundary.
- Add fake adapter for tests.
- Keep final business writes out of scope.

### Epic 5: Policy Loader and Invariant Engine

- Load YAML policies.
- Validate policy schema.
- Register deterministic check functions.
- Emit invariant results.

### Epic 6: Formula Guard

- Add Formula Guard policy.
- Detect missing, partial, and mismatched formulas.
- Produce explainable blocking issues.

### Epic 7: Preflight API

- Implement `POST /v1/preflight`.
- Persist preflight case and invariant results.
- Return decision contract.
- Add audit event.

## Later Phases

- UI and audit views.
- Import Guard.
- Access Rule Guard.
- Approval and controlled execution.
- Mock ERP / ERPNext adapter.
- LLM explainers and policy drafting.

## Out of Scope for Phase 1

- React UI.
- LLM integration.
- Controlled executor.
- Native Odoo write actions for critical operations.
- Multi-ERP adapter implementation.
