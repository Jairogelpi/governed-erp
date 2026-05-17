# 14 ERP Agent OS Strategic Vision

**Status:** Parent-level product direction child spec  
**Date:** May 18, 2026  
**Relationship to ERPGuard:** ERPGuard remains the safety kernel. Current ERPGuard code must not be removed or rewritten as part of this strategy shift.

ERP Agent OS is a web platform where a business owner connects any ERP, talks to an AI agent, creates or modifies ERP automations in natural language, validates them through ERPGuard, compiles them into reusable skills, stores them in a Skill Registry, exposes them as MCP-style safe tools, and executes repeated runs with zero or minimal LLM tokens.

The product sentence is:

> Create automations for your ERP by talking to an agent. ERP Agent OS converts them into safe skills that later execute with minimum token cost.

The differentiation centers on five pillars:

1. Minimum token cost.
2. Universal multi-ERP architecture.
3. Extreme ease of use for non-programmers.
4. Deep ERP integration.
5. Safety through ERPGuard.

## 1. Product Vision

ERP Agent OS is not only an ERP safety checker. It is a state-of-the-art operating layer for AI-created ERP automation.

The target experience:

```text
Business owner
-> Web App
-> Connects ERP
-> Agent understands the business
-> Agent creates or modifies automations
-> ERPGuard verifies safety and impact
-> Skill Compiler turns the automation into a skill
-> Skill Registry stores the versioned skill
-> MCP Gateway exposes it as a safe tool
-> Deterministic Runtime executes it without using the LLM every time
-> Business owner edits automations and memory in natural language
```

ERP Agent OS should let a user say:

> "When an order contains perfume products, check formula, stock, and lots before manufacturing. If something is wrong, warn me and block unsafe manufacturing."

The system should transform that request into a reusable, tested, approved, auditable skill.

The key thesis is:

> AI is used to create, modify, repair, and explain automations. Repeated execution runs through deterministic runtime.

This is the difference between an agent that reasons from scratch every time and a system that learns a process once, compiles it, governs it, and reuses it cheaply.

## 2. User Journey

The primary user is a business owner or operator who understands the business process but does not want to write YAML, Python, BPMN, or adapter code.

### Onboarding

1. The user enters the Web App.
2. The user selects an ERP type, starting with Odoo.
3. The user creates a connection.
4. The system performs a safe read-only diagnosis.
5. The system builds initial Business Memory.

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

> "Quiero que cuando un pedido tenga productos de perfume, se revise la formula, stock y lotes antes de que nadie lo mande a fabricar."

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

From then on, repeated executions use deterministic runtime by default. The LLM is not used unless the user modifies the skill, asks for explanation, or the runtime encounters an unknown failure.

## 3. Architecture

```text
Business User
-> Web App
-> ERP Agent Builder
-> Business Memory
-> Process Builder
-> ERPGuard Safety Kernel
-> Guard Builder
-> Skill Compiler
-> Skill Registry
-> Semantic Skill Discovery
-> MCP Gateway
-> Deterministic Runtime
-> ERP Adapter SDK
-> ERP
-> Audit Store
```

### Universal Layer

The universal layer is shared across ERPs:

- Web App;
- natural language automation builder;
- Business Memory;
- skill package format;
- workflow runtime;
- policy and guard engine;
- Skill Registry;
- Semantic Skill Discovery;
- MCP Gateway;
- deterministic runtime;
- audit store.

### ERP-Specific Layer

ERP depth comes from adapters and packs:

- Odoo adapter;
- ERPNext adapter;
- SAP adapter;
- Dynamics adapter;
- NetSuite adapter;
- object mappings;
- field mappings;
- process packs;
- domain packs;
- industry packs.

The architecture promise is:

> Universal by architecture, deep by adapter.

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
- audit panel.

Business users should not see YAML, Python, MCP internals, or adapter code.

### ERP Agent Builder

The ERP Agent Builder is the conversational layer.

Responsibilities:

- understand business requests;
- ask clarification questions;
- propose automations;
- modify existing skills;
- explain impact;
- route generated workflows through ERPGuard;
- avoid executing raw ERP actions directly.

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
- preferred approval thresholds.

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
- audit evidence.

Every skill must pass through ERPGuard before risky execution.

### Guard Builder

Guard Builder lets non-developers configure guards later through templates, field mapping, safe conditions, decision tables, previews, tests, approval, and versioning.

Developers may still create custom invariant functions for advanced cases, but business users and consultants should configure most guards without code.

### Skill Compiler

Skill Compiler turns a validated workflow into a versioned executable skill package.

Responsibilities:

- generate `skill.yaml`;
- generate `workflow.yaml`;
- generate guard references;
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
- audit linkage.

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
- business domain.

### MCP Gateway

MCP Gateway exposes approved skills as MCP-style tools.

It must expose safe ERP skills, not raw ERP operations.

Examples:

- `safe_validate_sale_order`;
- `safe_prepare_purchase_draft`;
- `safe_import_products_preflight`;
- `safe_explain_access_issue`.

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
- fail closed on unknown states.

### ERP Adapter SDK

ERP Adapter SDK lets ERP Agent OS connect to multiple ERPs through a common interface.

Responsibilities:

- schema discovery;
- object mapping;
- field mapping;
- permission inspection;
- safe read capabilities;
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
- what output was produced.

## 5. Skill Package Format

A skill is a versioned package:

```text
skills/safe_perfume_order_preflight/
  skill.yaml
  workflow.yaml
  guards.yaml
  policy.yaml
  permissions.yaml
  input_schema.json
  output_schema.json
  tests/
  examples/
  mcp_tool_definition.json
  audit_config.yaml
```

Example:

```yaml
skill:
  id: safe_perfume_order_preflight
  name: Validar pedido de perfume antes de fabricacion
  version: 1.0.0
  status: active

inputs:
  sale_order_id: string

workflow:
  - load_sales_order
  - validate_formula
  - check_stock
  - check_lots
  - produce_preflight_report

guards:
  - formula_guard
  - stock_guard
  - lot_traceability_guard

permissions:
  - odoo.read.sale_order
  - odoo.read.product
  - odoo.read.stock
  - odoo.read.lot

execution:
  mode: deterministic
  llm_required: false

on_failure:
  use_llm_for_diagnosis: true

audit:
  enabled: true
```

Each skill package must be portable at the semantic level. ERP-specific details belong in adapter mappings, field mappings, and domain packs.

## 6. Skill Lifecycle

```text
draft -> generated -> validated -> tested -> previewed -> approved -> published -> active -> deprecated
```

### draft

The user describes a desired automation or starts from a template.

### generated

The system generates a structured skill draft.

### validated

Schemas, workflow structure, guard references, permissions, and mappings are valid.

### tested

Generated and curated tests pass against fake fixtures and allowed read-only samples.

### previewed

The user sees what would happen before activation.

### approved

A human approves the skill version.

### published

The skill is available in the registry.

### active

The skill can execute through deterministic runtime and MCP Gateway.

### deprecated

The skill is retained for audit and rollback but should not be used for new executions.

## 7. Token Economics

Token economics is a first-class product constraint.

### Creation Cost

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

LLM usage is allowed when a skill breaks because of:

- changed ERP schema;
- missing fields;
- invalid mappings;
- unexpected adapter payload;
- unknown runtime failure.

Repair creates a new draft or new version. It must not silently mutate an active skill.

### Explanation Cost

LLM usage is allowed when the user asks:

- why a skill blocked an action;
- what changed between versions;
- how to fix a failed mapping;
- what an audit trail means.

Explanations must be grounded in structured evidence.

### Break-Even Point

The system becomes economically valuable when:

```text
creation_tokens + modification_tokens + occasional_repair_tokens
<
tokens_spent_by_a_generic_agent_reasoning_through_every_execution
```

For repeated ERP processes, the break-even point should arrive quickly.

## 8. MCP Strategy

ERP Agent OS should expose safe skills, not raw ERP tools.

Do not expose:

- raw `odoo.write`;
- raw `odoo.call_method`;
- raw `odoo.execute_action`;
- unrestricted SQL;
- direct stock validation;
- direct payment execution;
- unmanaged manufacturing confirmation.

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
- `AccessRule`.

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

Domain packs contain reusable object mappings, workflows, and guards for:

- sales;
- inventory;
- manufacturing;
- purchasing;
- accounting;
- access control.

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

- Formula Guard becomes the first guard.
- Current preflight flow becomes the first deterministic skill runtime base.
- Fake adapter remains the test ERP.
- Odoo adapter becomes the first real ERP adapter.
- Canonical models become the first canonical ERP model.
- Policy Engine becomes the first ERPGuard decision layer.
- YAML policy loader becomes the first policy metadata layer.
- Connection API becomes the first ERP connection layer.
- Audit retrieval becomes the first evidence trail.

Nothing in this product shift requires removing existing ERPGuard work. The current flow:

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
- convert Formula Guard preflight into the first skill;
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

The near-term focus is to evolve ERPGuard from a preflight service into the safety kernel underneath reusable ERP skills.
