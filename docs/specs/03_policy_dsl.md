# 03 Policy DSL Spec

**Parent spec references:** Sections 10, 11, 12, 13, 23, 26.

## Purpose

Define the YAML policy structure used by ERPGuard Phase 1. Policies must be deterministic, versionable, explainable, and testable.

## Policy Shape

```yaml
policy: safe_confirm_sales_order
version: 0.1.0
status: active
applies_to:
  canonical_object: SalesOrder
  canonical_action: confirm_sales_order

preconditions:
  - id: customer_exists
    type: data
    severity: blocking
    check: customer_exists
    message: The sales order must have a customer.

simulation: []

risk_rules:
  - id: blocking_issue_blocks
    when: has_blocking_issues
    decision: block

postconditions: []
```

## Required Fields

- `policy`
- `version`
- `applies_to.canonical_object`
- `applies_to.canonical_action`
- at least one of `preconditions`, `risk_rules`, or `postconditions`

## Supported Decisions

- `allow`
- `allow_with_warning`
- `require_approval`
- `block`
- `unsupported`
- `needs_more_context`

## Phase 1 Check Strategy

Phase 1 avoids arbitrary expression execution. YAML `check` values map to registered deterministic check functions, such as:

- `customer_exists`
- `order_has_lines`
- `products_are_active`
- `formula_exists_for_capacity_products`
- `formula_matches_capacity`
- `total_ml_matches_quantity`

## Invariant Result

Every check returns:

```yaml
invariant_id: string
invariant_type: data | process | permission | business
status: passed | failed | skipped | error
severity: info | warning | blocking
message: string
evidence: object
```

## Formula Guard Policy

```yaml
policy: formula_guard
version: 0.1.0
status: active
applies_to:
  canonical_object: SalesOrder
  canonical_action: confirm_sales_order

preconditions:
  - id: formula_exists_for_capacity_products
    type: business
    severity: blocking
    check: formula_exists_for_capacity_products
    message: Capacity products require a formula.

  - id: formula_matches_capacity
    type: business
    severity: blocking
    check: formula_matches_capacity
    message: Formula ml per unit must match product capacity.

  - id: total_ml_matches_quantity
    type: business
    severity: blocking
    check: total_ml_matches_quantity
    message: Formula total ml must equal capacity times ordered quantity.
```

## Acceptance Criteria

- Valid YAML policies load into typed schema.
- Invalid YAML policies produce clear validation errors.
- Unknown check functions make the policy invalid at load time.
- Formula Guard produces blocking invariant results with evidence.
