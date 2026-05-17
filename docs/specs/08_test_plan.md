# 08 Test Plan Spec

**Parent spec references:** Sections 23, 24, 26, 27, 28.

## Purpose

Define the Phase 1 testing strategy. Tests must prove that ERPGuard can load policies, map canonical objects, evaluate Formula Guard, persist evidence, and return preflight decisions.

## Test Levels

### Unit Tests

- Pydantic canonical model validation.
- Policy YAML schema validation.
- Check function behavior.
- Risk decision behavior.
- Repository persistence with test database.

### API Tests

- Create connection.
- List connections without secrets.
- Preflight success path with valid formula.
- Preflight block path with missing formula.
- Preflight block path with mismatched formula.
- Preflight unsupported action.

### Adapter Tests

- Fake adapter returns canonical `SalesOrder`.
- Odoo mapper handles representative native payloads.
- Missing configured formula field produces mapping error.

### Policy Fixture Tests

Each policy must have:

- one valid positive example;
- one negative example;
- expected invariant results;
- expected final decision.

## Formula Guard Required Cases

1. Product has no capacity requirement: formula may be absent.
2. Product has capacity, formula missing: block.
3. Product has capacity, formula ml per unit differs: block.
4. Product has capacity, total ml differs from `ml_per_unit * quantity`: block.
5. Product has capacity and formula matches: pass.

## Test Data

Use local JSON fixtures under `tests/fixtures/`. Do not require a live Odoo instance for normal test runs.

## Acceptance Criteria

- `pytest` passes locally.
- Tests can run without network access.
- Every Phase 1 module has at least one focused test.
- Preflight API tests assert persisted audit evidence, not just response shape.
