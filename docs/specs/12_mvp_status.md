# ERPGuard MVP Implementation Status

**Date:** May 17, 2026  
**Status:** MVP Phase 1 foundation implemented and test-covered  
**Scope:** Fake adapter demo path, read-only Odoo adapter skeleton, Formula Guard, preflight persistence, and audit retrieval

## 1. Current Implemented Architecture

The current working flow is:

```text
Connection API
-> Stored connection
-> Adapter factory
-> Fake/Odoo adapter interface
-> Canonical SalesOrder
-> Formula Guard
-> Policy Engine
-> Preflight Service
-> Persistence
-> Audit retrieval
```

The API can store ERP connection metadata, resolve a stored connection into an adapter, load a canonical `SalesOrder`, evaluate Formula Guard through the policy engine, persist the resulting preflight case and invariant evidence, and retrieve both the preflight details and audit trail.

The production-quality demo path today uses `FakeERPAdapter`. The Odoo path exists as a read-only adapter skeleton and mapper, tested with mocked client payloads only.

## 2. Current Working Endpoints

```http
GET /health
POST /v1/connections
GET /v1/connections
GET /v1/connections/{connection_id}
POST /v1/preflight
GET /v1/preflight/{preflight_id}
GET /v1/audit/{case_id}
```

`POST /v1/preflight` supports the preferred stored-connection flow with `connection_id`. It also keeps the older local-development `erp_type: "fake"` request path.

## 3. Current Implemented Modules

- Canonical models for company, customer, product, sales order, sales order line, formula line, formula validation summary, and structured formula errors.
- Canonical enums for ERP type, sales order state, product type/tracking, canonical actions, risk levels, preflight decisions, and invariant status/severity.
- Fake adapter with deterministic in-memory sales order fixtures.
- Odoo adapter skeleton, read-only, with XML-RPC client wrapper and mocked tests.
- Odoo mapper for `sale.order`, `sale.order.line`, `product.product`, and optional formula payloads.
- Formula Guard invariant logic over canonical sales orders.
- YAML policy loader for `policies/odoo/formula_guard.yaml`.
- Policy engine that uses YAML metadata and deterministic Formula Guard evaluation.
- Preflight service that loads a target through an adapter and fails closed on controlled errors.
- Connection persistence with secret redaction in API responses.
- Preflight case, invariant result, and audit event persistence.
- API routes for health, connections, preflight, preflight retrieval, and audit retrieval.
- Automated tests for canonical models, adapters, Formula Guard, policy engine/loader, preflight service, persistence, and API routes.

## 4. What Is Genuinely Demoable Now

The current project can demo:

- Creating a fake connection.
- Running preflight against a valid fake sales order.
- Running preflight against a formula mismatch fake sales order.
- Retrieving the persisted preflight case.
- Retrieving the audit trail for the preflight case.
- Showing fail-closed behavior for missing targets, unknown policies, missing connections, and invalid adapter configuration.

The strongest demo flow is:

1. `POST /v1/connections` with `erp_type: "fake"`.
2. `POST /v1/preflight` using the returned `connection_id`.
3. `GET /v1/preflight/{preflight_id}`.
4. `GET /v1/audit/{case_id}`.

## 5. What Is Not Implemented Yet

- No real Odoo live preflight is required in tests.
- No write actions.
- No execute endpoint.
- No approval flow.
- No UI.
- No LLM integration.
- No stock simulation.
- No manufacturing simulation.
- No full ACL/record-rule simulation.
- No encrypted secret storage yet.

## 6. Test Status

```text
92 tests passing
```

The test suite currently verifies the fake demo path, read-only Odoo adapter skeleton with mocks, persistence, retrieval, and secret redaction behavior.

## 7. Current Risks

- Connection secrets are redacted in API responses but not encrypted at rest.
- Odoo adapter is a read-only skeleton and has not been validated against a live customer database in automated tests.
- Formula Guard depends on correct field mapping for capacity and formula data.
- Simulation is not implemented yet.
- No Alembic migrations yet.
- JSON text columns are acceptable for MVP speed but should be normalized later if query needs grow.

## 8. Recommended Next Sprint

**Sprint 2: Real Odoo read-only preflight**

Tasks:

- Add connection-based Odoo manual preflight path.
- Improve Odoo field mapping config.
- Add manual command to run preflight against a real Odoo sale order.
- Add safe debug logging.
- Add README instructions.
- Keep live Odoo outside automated tests.

## 9. Documentation-Only Block

This status report is documentation only. It does not add feature code or change runtime behavior.
