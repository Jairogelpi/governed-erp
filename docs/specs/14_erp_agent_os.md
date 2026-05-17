# 14 ERP Agent OS Spec

**Status:** Parent-level product direction child spec  
**Date:** May 18, 2026  
**Relationship to ERPGuard:** ERPGuard is not removed or replaced. ERPGuard becomes the safety kernel inside the higher-level ERP Agent OS platform.

## 1. Product Vision

ERP Agent OS is an AI agent platform for ERP automation.

Any business owner should be able to say:

> "When X happens in my ERP, do Y safely."

The system should then create a reusable, audited, safe automation skill.

ERP Agent OS combines:

- natural language automation creation;
- ERP process design;
- ERPGuard semantic safety verification;
- skill compilation;
- skill registry and versioning;
- MCP-style safe tool exposure;
- deterministic repeated execution;
- complete auditability.

The key product shift is this:

ERPGuard protects ERP operations. ERP Agent OS lets companies create safe ERP automations that become reusable skills. The first creation may use an LLM, but repeated execution should run through deterministic runtime with zero or minimal token usage.

## 2. Architecture

```text
User / Business Owner
-> ERP Agent
-> Process Builder
-> ERPGuard Safety Kernel
-> Skill Compiler
-> Skill Registry
-> MCP Gateway
-> Deterministic Skill Runtime
-> ERP Adapter
```

### Flow

1. A business owner describes an ERP automation in natural language.
2. ERP Agent clarifies intent and constraints.
3. Process Builder converts the request into a structured workflow draft.
4. ERPGuard Safety Kernel verifies risk, permissions, invariants, impact, and approval requirements.
5. Skill Compiler turns the approved workflow into a reusable skill package.
6. Skill Registry stores the skill, metadata, permissions, tests, examples, and versions.
7. Semantic Skill Discovery retrieves only relevant skills when a user asks for something later.
8. MCP Gateway exposes selected safe skills as MCP-style tools.
9. Deterministic Skill Runtime executes the compiled skill.
10. ERP Adapter performs read/write operations only through safe, governed interfaces.
11. Audit Store records creation, validation, approval, execution, errors, and outcomes.

## 3. Components

### ERP Agent

Conversational interface for business owners and consultants.

Responsibilities:

- understand natural language requests;
- ask clarifying questions;
- propose automation drafts;
- explain risks and outcomes;
- request human approval when needed.

The ERP Agent does not bypass ERPGuard.

### Process Builder

Transforms user intent into a structured workflow draft.

Example:

```yaml
trigger:
  event: sale_order_created

steps:
  - validate_formula
  - check_stock
  - if: stock_shortage
    then:
      - create_purchase_draft
      - request_approval
    else:
      - allow_confirmation
```

### ERPGuard Safety Kernel

The semantic safety layer every skill must pass through before execution.

Responsibilities:

- canonical model validation;
- guard evaluation;
- policy decisions;
- risk classification;
- fail-closed behavior;
- audit evidence;
- approval requirements.

### Guard Builder

Human-configurable safety rule system.

It lets non-developers configure guards through templates, field mapping, safe conditions, decision tables, tests, preview, approval, and versioning.

### Skill Compiler

Converts approved workflow drafts into executable skill packages.

Responsibilities:

- validate workflow schema;
- attach policy and guard requirements;
- generate input/output schemas;
- generate MCP tool definitions;
- package permissions and audit configuration;
- produce deterministic runtime artifacts.

### Skill Registry

Stores skills and their metadata.

Responsibilities:

- skill versioning;
- lifecycle state;
- ownership;
- permissions;
- tests;
- examples;
- embeddings / semantic index metadata;
- audit history.

### Semantic Skill Discovery

Retrieves relevant skills without loading the entire registry into the LLM context.

Responsibilities:

- embed/index skill descriptions and schemas;
- retrieve top K relevant skills;
- rank by semantic relevance, permissions, ERP type, and status;
- reduce token overhead and improve tool selection.

### MCP Gateway

Exposes approved safe skills as MCP-style tools.

The gateway should expose high-level safe tools only, not raw ERP write primitives.

### Deterministic Skill Runtime

Executes compiled skills without requiring the LLM for every run.

Responsibilities:

- validate inputs;
- run workflow steps;
- call ERPGuard before risky operations;
- call ERP adapters;
- produce structured outputs;
- write audit events;
- fail closed on unknown or unsafe states.

### ERP Adapter SDK

Vendor-neutral adapter interface for Odoo, ERPNext, and later ERP systems.

Responsibilities:

- translate native ERP records into canonical objects;
- expose safe read/write capabilities;
- hide ERP-specific transport details;
- support capability discovery;
- support mock/fake adapters for tests.

### Audit Store

Stores creation, validation, approval, activation, execution, failure, and runtime evidence.

Audit must answer:

- who requested what;
- what skill version ran;
- what ERP state was read;
- what guards evaluated;
- what decision was made;
- what action was executed or blocked;
- what output was produced.

## 4. Skill Package Format

A skill is a package containing:

```text
skill.yaml
workflow.yaml
policy.yaml
input_schema.json
output_schema.json
tests/
examples/
mcp_tool_definition.json
permissions.yaml
audit_config.yaml
```

### skill.yaml

Declares identity, name, description, version, owner, lifecycle state, ERP scope, and runtime mode.

Example:

```yaml
skill:
  id: odoo_safe_sale_order_preflight
  name: Safe Sale Order Preflight
  version: 1.0.0
  status: active
  runtime: deterministic
  requires_llm: false
```

### workflow.yaml

Defines trigger, steps, branches, expected inputs, and outputs.

### policy.yaml

Defines ERPGuard policies, guards, risk behavior, approvals, and fail-closed rules.

### input_schema.json

JSON Schema for runtime inputs.

### output_schema.json

JSON Schema for runtime outputs.

### tests/

Positive, negative, edge-case, and regression tests for the skill.

### examples/

Sample requests, records, outputs, and audit traces.

### mcp_tool_definition.json

MCP-style tool metadata:

- tool name;
- description;
- input schema;
- output schema;
- safe usage notes;
- required permissions.

### permissions.yaml

Declares required ERP permissions and ERPGuard permissions.

### audit_config.yaml

Declares what runtime events and evidence must be recorded.

## 5. Skill Lifecycle

```text
draft -> validated -> tested -> approved -> published -> active -> deprecated
```

### draft

Created by a user, template, natural language request, import, or AI-assisted workflow.

### validated

Schemas, workflow structure, policy references, permissions, and guard requirements are valid.

### tested

The skill has passing generated and/or user-provided tests.

### approved

A human reviewer approves the skill for publication.

### published

The skill is available in the registry but may not yet be enabled for runtime execution.

### active

The skill can be discovered and executed through the runtime or MCP Gateway.

### deprecated

The skill is retained for historical/audit purposes but should not be used for new executions.

## 6. Token Economics

The first creation of a skill may use LLM tokens.

Repeated execution should use deterministic runtime with zero or minimal tokens.

LLM usage should be limited to:

- creation;
- modification;
- repair;
- explanation;
- unknown failures.

### Creation-Time Token Use

The LLM may help:

- interpret the user's request;
- ask clarifying questions;
- draft a workflow;
- suggest field mappings;
- propose tests;
- explain preview results.

### Runtime Token Use

Once a skill is compiled and approved, normal execution should not require LLM reasoning.

The deterministic runtime should:

- validate input;
- execute workflow steps;
- call ERPGuard;
- call ERP adapters;
- return structured output;
- record audit evidence.

The LLM should only re-enter if the skill fails in an unknown way, the user asks for a change, or a natural language explanation is requested.

## 7. MCP Strategy

ERP Agent OS should expose safe skills as MCP-style tools.

It must not expose raw ERP write operations directly.

Do not expose:

- `odoo.write`;
- `odoo.call_method`;
- `odoo.execute_action`;
- unrestricted SQL;
- raw payment execution;
- raw stock validation.

Expose high-level safe tools only.

Examples:

- `safe_validate_sale_order`
- `safe_prepare_purchase_draft`
- `safe_import_products_preflight`
- `safe_explain_access_issue`

Each tool must:

- have a strict input schema;
- have a strict output schema;
- declare permissions;
- call ERPGuard for risky operations;
- produce audit evidence;
- fail closed on unsafe or unknown states.

## 8. Semantic Skill Discovery

Do not load all skills into the LLM context.

The Skill Registry should index skills semantically and retrieve only the top K relevant skills for a given user request.

This reduces token overhead and improves tool selection.

### Why This Matters

If an agent sees too many tools, it wastes tokens and may choose poorly.

ERP Agent OS should:

- index skill names, descriptions, inputs, outputs, examples, permissions, ERP type, and tags;
- retrieve the top K relevant skills;
- include only those skill/tool definitions in the LLM context;
- prefer active and approved skills;
- filter by user permissions and ERP connection;
- keep raw ERP operations unavailable.

Semantic Skill Discovery turns a large skill registry into a compact, relevant toolset for each interaction.

## 9. Relationship With ERPGuard

ERPGuard is not replaced.

ERPGuard is the safety kernel every skill must pass through before execution.

ERPGuard remains responsible for:

- semantic preflight;
- guard evaluation;
- policy decisions;
- risk levels;
- approval requirements;
- fail-closed behavior;
- audit evidence;
- adapter safety boundaries.

ERP Agent OS sits above ERPGuard.

ERPGuard answers:

> Is this ERP action safe, allowed, explainable, and auditable?

ERP Agent OS answers:

> How can a business user create, reuse, discover, and execute safe ERP automations?

## 10. MVP for TFM

The TFM MVP should demonstrate the core loop, not the entire platform.

The MVP should demonstrate:

- create one skill from a template or natural language draft;
- validate it through ERPGuard;
- save it in registry;
- execute it twice;
- show first run may require LLM/design, second run does not;
- show audit trail.

### Suggested MVP Skill

`safe_order_formula_preflight`

Purpose:

Validate whether a sales order can safely continue before manufacturing or confirmation.

MVP flow:

1. User requests a safe order validation automation.
2. System creates or loads a draft skill.
3. ERPGuard validates Formula Guard requirements.
4. Skill is saved to registry.
5. Skill is exposed as an MCP-style local tool.
6. Skill runs against a fake or read-only Odoo sales order.
7. Skill runs a second time through deterministic runtime without LLM reasoning.
8. Audit trail proves what happened.

## 11. Non-Goals

- No full UI yet.
- No marketplace yet.
- No autonomous write actions.
- No SAP/Dynamics full adapter.
- No unrestricted tool calling.

The near-term focus is the core architecture: skill schema, registry, deterministic runtime, ERPGuard validation, audit trail, and safe MCP-style exposure.
