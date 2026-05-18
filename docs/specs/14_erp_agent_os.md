# 14 ERP Agent OS Strategic Vision

**Status:** Parent product strategic spec  
**Date:** May 18, 2026  
**Relationship to ERPGuard:** ERPGuard remains the safety kernel. Current ERPGuard code must not be removed or rewritten as part of this product expansion.

ERP Agent OS is a web platform where a business owner connects any ERP, talks to an AI agent, creates or modifies ERP automations in natural language, validates them through ERPGuard, compiles them into reusable skills, stores them in a Skill Registry, exposes them as MCP-style safe tools, and executes repeated runs with zero or minimal LLM tokens.

The differentiation is centered on five pillars:

1. Minimum token cost.
2. Universal multi-ERP architecture.
3. Extreme ease of use for non-programmers.
4. Deep ERP integration.
5. Safety through ERPGuard.

## 1. Product Vision

ERP Agent OS is the state-of-the-art target product above ERPGuard.

ERPGuard remains the semantic safety kernel. ERP Agent OS adds the product layer around it: a web app, natural-language automation creation, business memory, skill compilation, a skill registry, MCP-style safe tool exposure, deterministic runtime, ERP adapters, and audit evidence.

The core product sentence is:

> Create ERP automations by talking to an agent. ERP Agent OS verifies them through ERPGuard, compiles them into safe reusable skills, and runs repeated executions with zero or minimal LLM tokens.

The central thesis is that AI should be used to create, modify, repair, and explain automations, not to pay token cost on every repeated execution.

ERP Agent OS should let a business owner say:

> When an order contains perfume products, check formula, stock, and lots before manufacturing. If something is wrong, block unsafe manufacturing and tell me why.

The system should transform that request into a reusable, tested, approved, auditable skill.

## 2. User Journey

The primary user is a business owner, operator, or ERP consultant who understands the business process but does not want to write YAML, Python, BPMN, MCP definitions, Odoo server actions, SAP workflows, or adapter code.

### Onboarding

1. The user enters the Web App.
2. The user selects an ERP type, starting with Odoo.
3. The user creates a connection.
4. The system performs a safe read-only diagnosis.
5. The system discovers available objects, fields, modules, customizations, and risks.
6. The system builds initial Business Memory.

Example diagnosis:

```text
Detected:
- 4,283 products
- 1,120 customers
- 312 recent sales orders
- 18 custom fields
- 7 automated actions
- 5 manufacturing-related processes
- 3 possible formula consistency risks
```

### Automation Creation

The user writes:

> Quiero que cuando un pedido tenga productos de perfume, se revise la formula, stock y lotes antes de que nadie lo mande a fabricar.

The agent responds with a structured proposal:

```text
I understand that you want a preflight automation before manufacturing.

This skill will:
1. Read the sales order.
2. Detect products with capacity in ml.
3. Validate formula lines.
4. Check stock.
5. Check lot traceability.
6. Block manufacturing if formula validation fails.
7. Request approval if only stock is missing.
8. Produce a report for the responsible user.
```

The agent asks only necessary clarification questions:

- Is `x_studio_capacidad_ml` the capacity field?
- Is `x_sale_formula_line` the formula model?
- Should formula mismatch always block?
- Should stock shortage block or request approval?

### Preview

Before activation, the system runs a dry preview:

```text
Preview:
- 38 orders would pass.
- 6 orders would be blocked by formula mismatch.
- 9 orders would require approval because of stock shortage.
- 0 write actions would be executed in this preview.
```

### Activation

After human approval, the skill becomes active.

From then on, repeated executions use deterministic runtime by default. The LLM is not used unless the user modifies the skill, asks for an explanation, or the runtime encounters an unknown failure that requires repair.

## 3. Architecture

```text
Business User
-> ERP Agent Builder
-> Process Builder
-> ERPGuard Safety Kernel
-> Skill Compiler
-> Skill Registry
-> Semantic Skill Discovery
-> MCP Gateway
-> Deterministic Runtime
-> ERP Adapter
-> ERP
```

The architecture separates creation-time intelligence from runtime execution.

At creation time, the AI agent helps understand intent, ask questions, draft processes, propose mappings, generate tests, and explain previews.

At runtime, the deterministic engine loads approved skills, validates inputs, calls ERPGuard, calls adapters, enforces permissions, produces structured outputs, and records audit evidence.

The platform promise is:

```text
Universal by architecture.
Deep by adapter.
Safe by ERPGuard.
Cheap at repeated runtime.
Simple for business users.
```

## 4. Components

### Web App

The Web App is the business-facing control plane.

It should include:

- onboarding;
- ERP connection setup;
- chat with the agent;
- automation creation;
- automation panel;
- memory panel;
- preview and tests;
- approvals;
- audit panel;
- skill registry views;
- business-friendly explanations.

Business users should not see YAML, Python, MCP internals, JSON schemas, adapter code, or ERP-native API calls by default.

### ERP Agent Builder

ERP Agent Builder is the conversational layer.

Responsibilities:

- understand business requests;
- ask clarification questions;
- propose automations;
- modify existing skills;
- explain impact;
- route generated workflows through ERPGuard;
- avoid executing raw ERP actions directly;
- use Business Memory to reduce repeated questions.

### Business Memory

Business Memory stores organization-specific context.

It may include:

- business description;
- internal rules;
- owner preferences;
- glossary of ERP fields;
- recurring processes;
- historical decisions;
- approved naming conventions;
- known exceptions;
- preferred approval thresholds;
- mapped custom fields;
- known ERP modules and integrations.

Business Memory helps the agent create better automations without repeatedly asking the same questions.

### Process Builder

Process Builder converts intent into a structured workflow draft.

Example:

```yaml
trigger:
  event: sales_order_created

steps:
  - load_sales_order
  - validate_formula
  - check_stock
  - check_lots
  - if: formula_mismatch
    then:
      - block_manufacturing
      - produce_report
  - if: stock_shortage
    then:
      - request_approval
```

The Process Builder must produce deterministic workflows that can be tested, previewed, approved, versioned, and run without LLM reasoning on every execution.

### ERPGuard Safety Kernel

ERPGuard is the mandatory safety layer.

Responsibilities:

- canonical object validation;
- preflight;
- semantic guard evaluation;
- risk classification;
- policy decisions;
- approval requirements;
- fail-closed behavior;
- audit evidence;
- postcondition verification later;
- controlled execution boundaries later.

Every risky skill must pass through ERPGuard before it can affect ERP state.

### Guard Builder

Guard Builder lets non-developers configure guards later through templates, field mapping, safe conditions, decision tables, previews, tests, approval, and versioning.

Developers may still create custom invariant functions for advanced cases, but business users and consultants should configure most guards without code.

Guard Builder must never allow arbitrary Python, unrestricted `eval`, or unsafe expression execution for business-user-authored guards.

### Skill Compiler

Skill Compiler turns a validated workflow into a versioned executable skill package.

Responsibilities:

- generate `skill.yaml`;
- generate `workflow.yaml`;
- generate guard references;
- generate policy metadata;
- generate permissions;
- generate tests;
- generate input and output schemas;
- generate MCP tool definition;
- generate audit configuration;
- mark whether LLM is required at runtime.

### Skill Registry

Skill Registry stores and versions reusable automations.

Responsibilities:

- skill storage;
- lifecycle state;
- semantic index metadata;
- owner and approval metadata;
- version history;
- rollback;
- activation and deactivation;
- permissions;
- audit linkage;
- deprecation history.

### Semantic Skill Discovery

Semantic Skill Discovery prevents loading every skill into the LLM context.

It should retrieve only the top K relevant skills based on:

- user request;
- skill description;
- input and output schema;
- examples;
- ERP type;
- permissions;
- active status;
- business domain;
- current ERP object context.

### MCP Gateway

MCP Gateway exposes approved skills as MCP-style tools.

It must expose safe ERP skills, not raw ERP operations.

Examples:

- `safe_validate_sale_order`;
- `safe_prepare_purchase_draft`;
- `safe_import_products_preflight`;
- `safe_explain_access_issue`;
- `safe_perfume_order_preflight`.

### Deterministic Runtime

Deterministic Runtime executes approved skills without LLM reasoning on every run.

Responsibilities:

- validate input;
- load skill version;
- execute workflow steps;
- call ERPGuard;
- call ERP adapters;
- enforce idempotency;
- record runtime events;
- fail closed on unknown states;
- return structured outputs.

### ERP Adapter SDK

ERP Adapter SDK lets ERP Agent OS connect to multiple ERPs through a common interface.

Responsibilities:

- schema discovery;
- object mapping;
- field mapping;
- permission inspection;
- safe read capabilities;
- simulation capabilities where available;
- controlled write capabilities later;
- native error normalization;
- capability discovery;
- test fakes and mocks.

### Audit Store

Audit Store records both design-time and runtime evidence.

It should answer:

- who requested the automation;
- who approved it;
- which skill version ran;
- what input was used;
- what ERP objects were read;
- what guards ran;
- what decision was made;
- what actions were allowed or blocked;
- whether the LLM was used;
- what output was produced;
- which adapter and ERP version were involved.

## 5. Skill Package Format

A skill is a versioned package:

```text
skills/safe_perfume_order_preflight/
  skill.yaml
  workflow.yaml
  policy.yaml
  guards.yaml
  permissions.yaml
  input_schema.json
  output_schema.json
  tests/
  examples/
  mcp_tool_definition.json
  audit_config.yaml
```

### `skill.yaml`

Defines skill identity, name, description, owner, version, lifecycle state, ERP scope, domain scope, industry scope, and registry metadata.

### `workflow.yaml`

Defines deterministic steps, branching, preflight calls, adapter calls, idempotency behavior, failure handling, and outputs.

### `policy.yaml`

Defines policy-level decisions, risk thresholds, approval requirements, fail-closed behavior, and guard decision aggregation.

### `guards.yaml`

Lists required semantic guards, such as Formula Guard, stock guard, lot traceability guard, import guard, access rule guard, automated action guard, or invoice guard.

### `permissions.yaml`

Defines who can run, approve, modify, publish, deprecate, or inspect the skill.

### `input_schema.json`

Defines strict runtime inputs.

### `output_schema.json`

Defines strict runtime outputs.

### `tests/`

Contains generated and curated tests for positive, warning, blocking, approval, and error scenarios.

### `examples/`

Contains sample inputs, outputs, previews, reports, and business explanations.

### `mcp_tool_definition.json`

Defines the safe MCP-style tool exposed by the MCP Gateway.

### `audit_config.yaml`

Defines what evidence must be stored at design time and runtime.

Each skill package must be portable at the semantic level. ERP-specific details belong in adapter mappings, field mappings, and domain packs.

## 6. Skill Lifecycle

```text
draft → generated → validated → tested → previewed → approved → published → active → deprecated
```

### draft

The user describes a desired automation or starts from a template.

### generated

The system generates a structured skill draft.

### validated

Schemas, workflow structure, guard references, permissions, mappings, and adapter capability requirements are valid.

### tested

Generated and curated tests pass against fake fixtures, mock adapters, and allowed read-only samples.

### previewed

The user sees what would happen before activation, including expected reads, possible writes, blocks, warnings, approval needs, and audit evidence.

### approved

A human approver reviews the skill version, tests, preview, risk, permissions, and expected operational impact.

### published

The skill is stored in the registry and becomes discoverable.

### active

The skill can execute through deterministic runtime and MCP Gateway.

### deprecated

The skill is retained for audit and rollback but should not be used for new executions.

## 7. Token Economics

Token economics is a first-class product constraint.

### Creation Cost

Creation cost is the LLM cost paid to transform a business request into a validated reusable skill.

Creation may use LLM tokens for:

- understanding natural language;
- asking clarifying questions;
- creating workflow drafts;
- suggesting field mappings;
- generating tests;
- explaining previews;
- producing a skill package.

This is acceptable because it creates a reusable automation asset.

### Repeated Execution Cost

Repeated execution should use zero LLM tokens by default.

The runtime should execute the approved skill deterministically:

```text
skill input
-> input validation
-> adapter read
-> canonical mapping
-> ERPGuard checks
-> workflow step execution
-> structured result
-> audit event
```

### Repair Cost

Repair cost is the LLM cost paid when a skill breaks or needs to be changed because of schema drift, changed fields, invalid mappings, unexpected adapter payloads, missing permissions, or unknown runtime failures.

Repair creates a new draft or new version. It must not silently mutate an active skill.

### Explanation Cost

Explanation cost is the LLM cost paid when the user asks:

- why a skill blocked an action;
- why approval is required;
- what changed between versions;
- how to fix a failed mapping;
- what an audit trail means.

Explanations must be grounded in structured evidence.

### Break-Even Point

The system becomes economically valuable when:

```text
creation_tokens + modification_tokens + occasional_repair_tokens + explanation_tokens
<
tokens_spent_by_a_generic_agent_reasoning_through_every_execution
```

For repeated ERP processes, the break-even point should arrive quickly.

## 8. MCP Strategy

ERP Agent OS should expose safe skills, not raw ERP tools.

Do not expose by default:

- raw `odoo.write`;
- raw `odoo.call_method`;
- raw `odoo.execute_action`;
- unrestricted SQL;
- direct stock validation;
- direct payment execution;
- unmanaged manufacturing confirmation;
- unrestricted permission changes.

Expose high-level safe skills:

- `safe_validate_sale_order`;
- `safe_prepare_purchase_draft`;
- `safe_import_products_preflight`;
- `safe_explain_access_issue`;
- `safe_perfume_order_preflight`.

Each MCP-style tool must have:

- strict input schema;
- strict output schema;
- permission requirements;
- guard requirements;
- audit requirements;
- fail-closed behavior.

### Top-K Skill Discovery

The system must not load all skills into the agent context.

Semantic Skill Discovery should retrieve only the top K relevant tools for a request. This reduces context cost, improves tool selection, and prevents a large registry from becoming an LLM prompt burden.

## 9. Guard Strategy

Every skill must pass through ERPGuard before risky execution.

ERPGuard provides:

- semantic preflight;
- guard evaluation;
- risk level;
- policy decision;
- approval requirements;
- explainable issues;
- fail-closed behavior;
- audit evidence.

Guards must become human-configurable later through Guard Builder.

Guard configuration should support:

- templates;
- field mapping;
- safe condition language;
- decision tables;
- preview;
- generated tests;
- approval;
- versioning.

No guard builder feature should allow arbitrary Python, arbitrary `eval`, or unrestricted expressions for business-user-authored guards.

## 10. Universal ERP Strategy

ERP Agent OS should be universal by model and deep by adapter.

### Canonical ERP Model

Skills should target canonical ERP objects and actions.

Initial objects:

- `SalesOrder`;
- `SalesOrderLine`;
- `Product`;
- `Customer`;
- `Company`;
- `Invoice`;
- `InventoryMove`;
- `ManufacturingOrder`;
- `AccessRule`;
- `AutomatedAction`.

Initial actions:

- `inspect_sales_order`;
- `validate_formula`;
- `check_stock`;
- `inspect_access_rules`;
- `confirm_sales_order`;
- `prepare_purchase_draft`.

Skills should say `confirm_sales_order`, not `sale.order.action_confirm()`.

### Adapters

Adapters translate canonical objects and actions into native ERP behavior.

Adapter roadmap:

1. Odoo.
2. ERPNext.
3. SAP partial adapter.
4. Dynamics partial adapter.
5. NetSuite partial adapter.

### Field Mapping

Field mapping lets consultants connect canonical fields to native and custom ERP fields.

Examples:

- product capacity field;
- formula model;
- formula line relation;
- milliliters per unit field;
- milliliters total field;
- stock location field;
- lot tracking field;
- Studio/custom fields.

### Domain Packs

Domain packs contain reusable object mappings, workflows, guards, tests, and skill templates for:

- sales;
- inventory;
- manufacturing;
- purchasing;
- accounting;
- access control;
- imports.

### Industry Packs

Industry packs contain specialized process knowledge for:

- fragrance manufacturing;
- food production;
- wholesale distribution;
- field services;
- regulated inventory;
- project-based services.

## 11. Relationship With Current Implementation

Current ERPGuard code becomes the first safety kernel.

Current implementation maps to ERP Agent OS as follows:

- Current Formula Guard becomes the first guard.
- Current preflight flow becomes the first deterministic skill runtime base.
- Fake adapter remains the test ERP.
- Odoo adapter is the first real ERP adapter.
- Canonical models become the first canonical ERP model slice.
- Policy Engine becomes the first ERPGuard decision layer.
- YAML policy loader becomes the first policy metadata layer.
- Connection API becomes the first ERP connection layer.
- Audit retrieval becomes the first evidence trail.

Nothing in this product shift requires removing or rewriting existing ERPGuard work. The current flow:

```text
connection
-> adapter
-> canonical model
-> Formula Guard
-> policy
-> preflight
-> audit
```

becomes the runtime safety foundation for skills.

## 12. MVP Path

The next MVP after the current preflight core should add the smallest useful skill loop.

Scope:

- Skill model;
- Skill Registry;
- convert Formula Guard preflight into first skill;
- `POST /v1/skills`;
- `GET /v1/skills`;
- `POST /v1/skills/{skill_id}/run`.

The first skill should be:

```text
safe_formula_guard_preflight
```

or:

```text
safe_order_formula_preflight
```

The endpoint should reuse the current preflight service first. A separate execution engine can come later.

MVP demonstration:

1. Create or register the Formula Guard skill.
2. Run it against a valid fake order.
3. Run it against a formula mismatch fake order.
4. Retrieve audit evidence.
5. Run the same skill again without LLM involvement.
6. Show that the skill is versioned and inspectable.

## 13. Non-Goals

- No full marketplace yet.
- No unrestricted ERP write actions.
- No SAP/Dynamics full adapter yet.
- No autonomous critical actions without approval.
- No exposing raw ERP write tools to agents.
- No full UI implementation in the immediate backend block.
- No live ERP requirement in automated tests.
- No arbitrary Python or unrestricted expressions in human-authored guard configuration.

This is a documentation-only strategic spec. It does not require runtime code changes.
