# ERPGuard Odoo Preflight Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 1 ERPGuard Odoo Preflight Core: a FastAPI backend that reads sales order state through an adapter boundary, maps it to canonical models, evaluates Formula Guard, persists evidence, and returns a preflight decision.

**Architecture:** The backend is organized around a preflight service that coordinates repositories, adapter interfaces, canonical models, policy loading, invariant evaluation, risk decisions, and audit persistence. Odoo-specific logic stays behind an adapter/mapper boundary; policies run only on canonical objects and deterministic check functions.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic, SQLAlchemy, SQLite for local MVP, PostgreSQL-ready models, PyYAML, pytest, httpx/FastAPI TestClient.

---

## Phase 1 Boundaries

**In scope:** FastAPI backend, basic project structure, database models, connection model, Odoo adapter interface, canonical models for `SalesOrder`, `SalesOrderLine`, `Product`, `Customer`, `Company`, policy loader, invariant result model, preflight endpoint contract, Formula Guard, tests.

**Out of scope:** UI, LLM/AI, controlled execution/write actions, approval UI, ERPNext or other multi-ERP adapter implementation.

## Planned File Structure

```text
erpguard/
  README.md
  pyproject.toml
  .env.example
  erpguard/
    __init__.py
    api/
      __init__.py
      main.py
      routes/
        __init__.py
        connections.py
        preflight.py
        audit.py
      schemas/
        __init__.py
        connections.py
        preflight.py
        audit.py
    core/
      __init__.py
      preflight_service.py
      risk_engine.py
      audit.py
      errors.py
    canonical/
      __init__.py
      objects.py
      actions.py
    adapters/
      __init__.py
      base.py
      factory.py
      odoo/
        __init__.py
        adapter.py
        mapper.py
        config.py
    policies/
      __init__.py
      dsl_schema.py
      loader.py
      registry.py
      evaluator.py
    invariants/
      __init__.py
      results.py
      sales.py
      formula.py
    db/
      __init__.py
      models.py
      session.py
      repositories.py
  policies/
    generic/
      safe_confirm_sales_order.yaml
    odoo/
      formula_guard.yaml
  tests/
    conftest.py
    fixtures/
      sales_order_valid_formula.json
      sales_order_missing_formula.json
      sales_order_mismatched_formula.json
    test_canonical_models.py
    test_policy_loader.py
    test_formula_guard.py
    test_repositories.py
    test_preflight_api.py
```

---

## Tasks

### Task 1: Project Foundation

**Parent spec references:** Sections 19.1, 19.2, 26.1, 27 Epic 1.

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `.env.example`
- Create: `erpguard/__init__.py`
- Create: `erpguard/api/main.py`
- Test: `tests/test_app_health.py`

- [ ] **Step 1: Write failing health test**

Assert `GET /health` returns `{"status": "ok"}`.

- [ ] **Step 2: Run test and confirm failure**

Run: `pytest tests/test_app_health.py -v`

- [ ] **Step 3: Add minimal FastAPI app**

Create `create_app()` and `/health`.

- [ ] **Step 4: Run test and confirm pass**

Run: `pytest tests/test_app_health.py -v`

- [ ] **Step 5: Commit**

Commit message: `chore: initialize FastAPI project foundation`

### Task 2: Database Session and Models

**Parent spec references:** Sections 19.1, 21, 26.1, 27 Task 1.2.

**Files:**
- Create: `erpguard/db/session.py`
- Create: `erpguard/db/models.py`
- Test: `tests/test_db_models.py`

- [ ] **Step 1: Write failing database metadata test**

Assert tables exist for `connections`, `preflight_cases`, `invariant_results`, `audit_events`, and `policies`.

- [ ] **Step 2: Run test and confirm failure**

Run: `pytest tests/test_db_models.py -v`

- [ ] **Step 3: Implement SQLAlchemy models**

Use text primary keys, JSON stored as text, and timestamps.

- [ ] **Step 4: Run database tests**

Run: `pytest tests/test_db_models.py -v`

- [ ] **Step 5: Commit**

Commit message: `feat: add Phase 1 database models`

### Task 3: Connection Repository and API

**Parent spec references:** Sections 20.1, 21.1, 26.1, 27 Task 1.3.

**Files:**
- Create: `erpguard/db/repositories.py`
- Create: `erpguard/api/schemas/connections.py`
- Create: `erpguard/api/routes/connections.py`
- Modify: `erpguard/api/main.py`
- Test: `tests/test_connections_api.py`

- [ ] **Step 1: Write failing API tests**

Test create connection, list connections, and secret redaction.

- [ ] **Step 2: Run tests and confirm failure**

Run: `pytest tests/test_connections_api.py -v`

- [ ] **Step 3: Implement repository and routes**

Persist config JSON, return sanitized response.

- [ ] **Step 4: Run connection tests**

Run: `pytest tests/test_connections_api.py -v`

- [ ] **Step 5: Commit**

Commit message: `feat: add connection persistence and API`

### Task 4: Canonical Models

**Parent spec references:** Sections 8.5, 9.1, 9.2, 9.3, 20.2, 26.1, 27 Epic 2.

**Files:**
- Create: `erpguard/canonical/actions.py`
- Create: `erpguard/canonical/objects.py`
- Test: `tests/test_canonical_models.py`

- [ ] **Step 1: Write failing model validation tests**

Cover valid sales order, missing customer allowed, line requires product, decimals remain decimals.

- [ ] **Step 2: Run tests and confirm failure**

Run: `pytest tests/test_canonical_models.py -v`

- [ ] **Step 3: Implement Pydantic models and enums**

Include Formula Guard support fields on products and lines.

- [ ] **Step 4: Run canonical tests**

Run: `pytest tests/test_canonical_models.py -v`

- [ ] **Step 5: Commit**

Commit message: `feat: add canonical sales order models`

### Task 5: Odoo Adapter Interface and Fake Adapter

**Parent spec references:** Sections 8.4, 18.2, 22.1, 22.2, 26.1, 27 Epic 3.

**Files:**
- Create: `erpguard/adapters/base.py`
- Create: `erpguard/adapters/factory.py`
- Create: `erpguard/adapters/odoo/config.py`
- Create: `erpguard/adapters/odoo/adapter.py`
- Test: `tests/test_adapter_contract.py`

- [ ] **Step 1: Write failing adapter contract tests**

Assert fake adapter can return a canonical sales order and unsupported ERP type fails closed.

- [ ] **Step 2: Run tests and confirm failure**

Run: `pytest tests/test_adapter_contract.py -v`

- [ ] **Step 3: Implement adapter protocol, factory, and Odoo shell**

No critical write methods.

- [ ] **Step 4: Run adapter tests**

Run: `pytest tests/test_adapter_contract.py -v`

- [ ] **Step 5: Commit**

Commit message: `feat: define ERP adapter boundary`

### Task 6: Odoo Sales Order Mapper

**Parent spec references:** Sections 8.2, 8.5, 22.2, 23.2, 30 Risk 4.

**Files:**
- Create: `erpguard/adapters/odoo/mapper.py`
- Create: `tests/fixtures/odoo_sale_order_valid_formula.json`
- Create: `tests/fixtures/odoo_sale_order_missing_formula.json`
- Test: `tests/test_odoo_mapper.py`

- [ ] **Step 1: Write failing mapper tests**

Map native-like Odoo fixture into canonical `SalesOrder`, including formula fields.

- [ ] **Step 2: Run tests and confirm failure**

Run: `pytest tests/test_odoo_mapper.py -v`

- [ ] **Step 3: Implement deterministic mapper**

Support configurable formula and capacity field names.

- [ ] **Step 4: Run mapper tests**

Run: `pytest tests/test_odoo_mapper.py -v`

- [ ] **Step 5: Commit**

Commit message: `feat: map Odoo sales orders to canonical model`

### Task 7: Policy DSL Schema and Loader

**Parent spec references:** Sections 10.1, 10.2, 10.3, 23, 26.1, 27 Epic 4.

**Files:**
- Create: `erpguard/policies/dsl_schema.py`
- Create: `erpguard/policies/loader.py`
- Create: `policies/generic/safe_confirm_sales_order.yaml`
- Create: `policies/odoo/formula_guard.yaml`
- Test: `tests/test_policy_loader.py`

- [ ] **Step 1: Write failing policy loader tests**

Valid policies load; invalid policies fail; unknown check names fail.

- [ ] **Step 2: Run tests and confirm failure**

Run: `pytest tests/test_policy_loader.py -v`

- [ ] **Step 3: Implement YAML loader and schema validation**

Use registered deterministic check names only.

- [ ] **Step 4: Run policy loader tests**

Run: `pytest tests/test_policy_loader.py -v`

- [ ] **Step 5: Commit**

Commit message: `feat: add YAML policy loader`

### Task 8: Invariant Results and Formula Guard Checks

**Parent spec references:** Sections 11.1, 20.3, 21.3, 23.2, 26.1, 27 Epic 5.

**Files:**
- Create: `erpguard/invariants/results.py`
- Create: `erpguard/invariants/formula.py`
- Create: `erpguard/invariants/sales.py`
- Test: `tests/test_formula_guard.py`

- [ ] **Step 1: Write failing Formula Guard tests**

Cover missing formula, ml-per-unit mismatch, total mismatch, valid formula, and no-capacity product.

- [ ] **Step 2: Run tests and confirm failure**

Run: `pytest tests/test_formula_guard.py -v`

- [ ] **Step 3: Implement invariant result and check functions**

Return line-level evidence with product, capacity, actual formula, expected total, and difference.

- [ ] **Step 4: Run formula tests**

Run: `pytest tests/test_formula_guard.py -v`

- [ ] **Step 5: Commit**

Commit message: `feat: add Formula Guard invariant checks`

### Task 9: Policy Evaluator and Risk Engine

**Parent spec references:** Sections 10.3, 13.1, 13.2, 20.3, 23.1, 26.1, 27 Task 4.3.

**Files:**
- Create: `erpguard/policies/registry.py`
- Create: `erpguard/policies/evaluator.py`
- Create: `erpguard/core/risk_engine.py`
- Test: `tests/test_policy_evaluator.py`

- [ ] **Step 1: Write failing evaluator tests**

Blocking invariant yields `block`; all checks passed for `confirm_sales_order` yields R3 and `allow` or `require_approval` according to policy result.

- [ ] **Step 2: Run tests and confirm failure**

Run: `pytest tests/test_policy_evaluator.py -v`

- [ ] **Step 3: Implement evaluator and risk decision**

Default `confirm_sales_order` to R3.

- [ ] **Step 4: Run evaluator tests**

Run: `pytest tests/test_policy_evaluator.py -v`

- [ ] **Step 5: Commit**

Commit message: `feat: evaluate policies and risk decisions`

### Task 10: Preflight Persistence and Audit

**Parent spec references:** Sections 20.3, 21.2, 21.3, 21.6, 24.1, 26.1, 27 Epic 6 and Epic 8.

**Files:**
- Create: `erpguard/core/audit.py`
- Extend: `erpguard/db/repositories.py`
- Test: `tests/test_preflight_persistence.py`

- [ ] **Step 1: Write failing persistence tests**

Persist preflight case, invariant results, and audit event for one decision.

- [ ] **Step 2: Run tests and confirm failure**

Run: `pytest tests/test_preflight_persistence.py -v`

- [ ] **Step 3: Implement repository methods and audit helper**

Store JSON snapshots and decision event.

- [ ] **Step 4: Run persistence tests**

Run: `pytest tests/test_preflight_persistence.py -v`

- [ ] **Step 5: Commit**

Commit message: `feat: persist preflight evidence`

### Task 11: Preflight API

**Parent spec references:** Sections 8.1, 20.2, 20.3, 23.1, 23.2, 26.1, 27 Epic 6.

**Files:**
- Create: `erpguard/api/schemas/preflight.py`
- Create: `erpguard/api/routes/preflight.py`
- Create: `erpguard/core/preflight_service.py`
- Modify: `erpguard/api/main.py`
- Test: `tests/test_preflight_api.py`

- [ ] **Step 1: Write failing preflight API tests**

Valid formula returns non-blocking decision; missing formula returns block with evidence and persisted case ID.

- [ ] **Step 2: Run tests and confirm failure**

Run: `pytest tests/test_preflight_api.py -v`

- [ ] **Step 3: Implement preflight service and route**

Keep `allow_write=false` enforced; reject execute-like requests.

- [ ] **Step 4: Run API tests**

Run: `pytest tests/test_preflight_api.py -v`

- [ ] **Step 5: Commit**

Commit message: `feat: add preflight endpoint`

### Task 12: Audit Retrieval API

**Parent spec references:** Sections 20.6, 21.6, 24.2, 26.1, 27 Epic 8.

**Files:**
- Create: `erpguard/api/schemas/audit.py`
- Create: `erpguard/api/routes/audit.py`
- Modify: `erpguard/api/main.py`
- Test: `tests/test_audit_api.py`

- [ ] **Step 1: Write failing audit API test**

Retrieve case, invariant results, and audit events by preflight ID.

- [ ] **Step 2: Run test and confirm failure**

Run: `pytest tests/test_audit_api.py -v`

- [ ] **Step 3: Implement audit route**

Return structured JSON without secrets.

- [ ] **Step 4: Run audit tests**

Run: `pytest tests/test_audit_api.py -v`

- [ ] **Step 5: Commit**

Commit message: `feat: expose audit case retrieval`

### Task 13: End-to-End Verification

**Parent spec references:** Sections 24.1, 26.4, 28.4, 30.

**Files:**
- Create or update: `README.md`
- Test: full test suite

- [ ] **Step 1: Add README usage notes**

Document running tests and starting the backend.

- [ ] **Step 2: Run full test suite**

Run: `pytest -v`

- [ ] **Step 3: Run app smoke command**

Run: `uvicorn erpguard.api.main:create_app --factory --reload`

- [ ] **Step 4: Record known limitations**

Document no UI, no LLM, no write execution, fake/live Odoo test boundary.

- [ ] **Step 5: Commit**

Commit message: `docs: document Phase 1 backend usage`

---

## Proposed First 10 Coding Tasks

1. Initialize Python/FastAPI project foundation.
2. Add SQLAlchemy database session and Phase 1 table models.
3. Add connection repository and API.
4. Add canonical Pydantic models and action enums.
5. Define ERP adapter interface, factory, and fake adapter.
6. Add Odoo sales order mapper with configurable formula fields.
7. Add YAML policy schema and loader.
8. Add invariant result objects and Formula Guard check functions.
9. Add policy evaluator and risk engine.
10. Add preflight case persistence and audit event storage.

## Risks and Ambiguities From Parent Spec

- **Formula field names are custom:** the parent spec names examples like `x_sale_formula_line`, but real Odoo installations may differ.
- **Simulation scope is broad:** Phase 1 should not promise inventory, purchase, or manufacturing impact beyond empty or placeholder predicted impact.
- **Permissions are underspecified for Phase 1:** actor metadata can be recorded, but full Odoo ACL and record-rule simulation should be later.
- **Decision semantics need tightening:** valid R3 `confirm_sales_order` could be `allow` for preflight-only mode or `require_approval` if future execution is considered.
- **Connection secret storage is not fully specified:** Phase 1 can redact responses, but encryption/secret manager design should be a later security task.
- **Live Odoo dependency risk:** tests should use fakes and fixtures so development is not blocked by Odoo availability.
