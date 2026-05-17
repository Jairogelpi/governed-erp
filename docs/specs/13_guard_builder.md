# 13 Guard Builder Spec

**Status:** Product direction child spec  
**Date:** May 18, 2026  
**Parent spec relationship:** Extends ERPGuard's policy DSL, Formula Guard, preflight, approval, and audit concepts into human-configurable guard creation.

## 1. Guard Builder Vision

ERPGuard guards must become configurable by non-developers.

The long-term product should not require every business rule to be written directly as Python or hand-authored YAML. Instead, ERPGuard should offer a Guard Builder that lets users create, configure, test, preview, approve, version, and activate guards through progressively more powerful layers:

- templates;
- field mapping;
- visual conditions;
- decision tables;
- natural language assisted drafting;
- preview/dry-run;
- test generation;
- approval workflow;
- versioning and activation.

The goal is to make semantic ERP safety practical for real teams. Business users should be able to configure common protections from templates. ERP consultants should be able to map custom fields and tune decision tables. Developers should only be needed when a guard requires a custom invariant function or a new adapter capability.

ERPGuard should remain fail-closed. A guard that is incomplete, untested, invalid, or unapproved cannot become active.

## 2. User Levels

### Business User

Business users configure guards through templates and forms.

They can:

- select a guard template;
- fill required business fields;
- choose predefined decisions such as warn, require approval, or block;
- run previews against sample records;
- review human-readable explanations;
- request activation.

They cannot:

- write arbitrary expressions;
- deploy untested guards;
- bypass approval for critical guards.

### ERP Consultant

ERP consultants configure field mapping and decision tables.

They can:

- map ERP-native fields to canonical fields;
- map custom Odoo Studio fields;
- configure relationship paths;
- define decision tables;
- tune severity and decision rules;
- inspect generated YAML;
- validate guards against realistic sample data.

They cannot:

- execute arbitrary Python in a condition;
- activate AI-generated guards without validation and approval.

### Developer

Developers create custom invariant functions and adapter extensions.

They can:

- add deterministic invariant functions;
- extend adapter read capabilities;
- add new canonical mappings;
- create new guard templates;
- add test fixtures and integration test hooks.

Developers are required only when template, mapping, condition, and decision-table layers are not expressive enough.

## 3. Guard Lifecycle

```text
draft -> configured -> tested -> previewed -> approved -> active -> deprecated
```

### draft

The guard exists as an idea, template instance, natural language draft, or imported policy skeleton.

### configured

Required fields, mappings, conditions, and decisions are filled in.

### tested

The guard has passed generated or user-provided test cases.

### previewed

The guard has been dry-run against sample or real read-only ERP records, producing explainable outcomes.

### approved

A human approver has reviewed the guard, test results, preview outcomes, and expected operational impact.

### active

The guard can participate in preflight decisions.

### deprecated

The guard is retained for audit/history but should no longer be used for new decisions.

## 4. Guard Configuration Layers

### Template Layer

Reusable guard templates for common ERP safety scenarios.

Examples:

- Formula Guard.
- Import duplicate guard.
- Access rule visibility guard.
- Sales order confirmation guard.
- Invoice posting guard.

### Field Mapping Layer

Maps ERP-native fields and custom fields into canonical guard inputs.

Examples:

- `product.product.x_capacity_ml` -> `Product.capacity_ml`
- `x.sale.formula.line.ml_per_unit` -> `FormulaLine.ml_per_unit`
- `sale.order.line.product_uom_qty` -> `SalesOrderLine.quantity`

### Condition Builder Layer

A visual builder that creates safe, restricted conditions using only approved operators.

No arbitrary code is allowed.

### Decision Table Layer

DMN-style decision tables for mapping conditions to outcomes.

Example:

| Condition | Severity | Decision |
|---|---|---|
| formula missing | blocking | block |
| formula ml mismatch | blocking | block |
| formula exists and matches | info | allow |

### YAML / Policy Layer

The generated or edited policy DSL representation.

This layer is versionable, reviewable, portable, and testable. It should remain deterministic and schema-validated.

### Code Invariant Layer

Deterministic Python functions for checks that cannot be expressed safely through templates, mappings, conditions, or decision tables.

This layer is developer-owned and must have tests.

## 5. Required Modules

### GuardTemplateRegistry

Stores available guard templates, required inputs, supported ERP types, supported canonical objects/actions, default checks, and default decisions.

### FieldMapper

Maps native ERP fields to canonical inputs. It should support custom fields, relationship paths, validation, and sample-value inspection.

### ConditionBuilder

Builds safe conditions from a restricted operator set. It must not allow arbitrary Python, arbitrary eval, or unrestricted expressions.

### DecisionTableEditor

Lets users configure condition-to-decision mappings using a structured table model.

### NaturalLanguageToGuardDraft

Uses LLM assistance to propose guard drafts from natural language requirements. Output must be schema-validated and treated as untrusted until tested and approved.

### GuardTestGenerator

Generates positive and negative test cases for a guard based on its template, field mapping, conditions, and decision table.

### GuardPreviewEngine

Runs a guard in dry-run mode against sample records or read-only live ERP records, returning explainable outcomes and evidence.

### GuardVersioning

Tracks versions, diffs, authorship, status changes, and activation history.

### GuardApprovalWorkflow

Routes guards through human review before activation. Critical guards require explicit approval.

### GuardActivationManager

Activates, deactivates, rolls back, and deprecates guards while preserving audit history.

## 6. Formula Guard Example

A human configures Formula Guard without code:

1. Select the Formula Guard template.
2. Map the product capacity field, for example `product.product.x_capacity_ml`.
3. Map the formula model, for example `x.sale.formula.line`.
4. Map the formula line relationship field, for example `sale_order_line_id`.
5. Map the ml per unit field, for example `ml_per_unit`.
6. Map the ml total field, for example `ml_total`.
7. Choose the decision on mismatch: block.
8. Preview against sample sales orders.
9. Review expected blocks, warnings, and evidence.
10. Run generated tests.
11. Submit for approval.
12. Activate after approval.

The user never writes Python. The system generates or updates the policy metadata and field mapping configuration, then routes runtime evaluation to the deterministic Formula Guard invariant.

## 7. Safe Condition Language

Allowed operators only:

- `equals`
- `not_equals`
- `greater_than`
- `less_than`
- `is_empty`
- `is_not_empty`
- `contains`
- `in_list`
- `sum_equals`
- `count_greater_than`
- `any_match`
- `all_match`
- `exists`
- `not_exists`

Prohibited:

- arbitrary Python;
- arbitrary eval;
- unrestricted expressions;
- arbitrary imports;
- filesystem access;
- network access;
- dynamic code execution.

The condition language must be declarative, schema-validated, and explainable.

## 8. AI Role

LLMs may help generate guard drafts from natural language, but they cannot activate guards.

AI can assist with:

- proposing a guard template;
- identifying likely field mappings;
- drafting conditions;
- suggesting decision table rows;
- generating test cases;
- explaining preview results.

Every AI-generated guard must pass:

- schema validation;
- deterministic safety checks;
- generated and/or human-provided tests;
- preview/dry-run;
- human approval.

AI output is advisory. The ERPGuard kernel remains deterministic and cannot be bypassed by an LLM.

## 9. State-of-the-Art References

Guard Builder should draw from these design foundations:

- DMN-style decision tables for transparent condition-to-decision logic.
- Policy-as-code for versioned, reviewable, testable rules.
- Natural language to DSL as an assisted drafting workflow, not as direct execution.
- Test generation to create positive and negative guard examples.
- Preview/dry-run to show operational impact before activation.

The product goal is not to invent a free-form automation builder. The goal is to make semantic ERP guards configurable while preserving determinism, auditability, and fail-closed behavior.

## 10. MVP Implications

Do not implement the full Guard Builder UI yet.

Near-term backend preparation should focus on:

- data structures for guard templates;
- field mapping schemas;
- safe condition schema;
- decision table schema;
- guard version metadata;
- generated test fixture format;
- preview result format;
- approval status fields.

The current MVP should continue prioritizing backend correctness and auditability. Guard Builder becomes the product direction for making ERPGuard usable by business users and ERP consultants after the core preflight engine is stable.
