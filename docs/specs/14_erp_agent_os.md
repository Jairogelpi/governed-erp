# 14 ERP Agent OS Strategic Vision

**Status:** Parent product positioning spec  
**Date:** May 18, 2026  
**Relationship to ERPGuard:** ERPGuard remains the safety kernel. ERP Agent OS is now the parent product built around ERPGuard.

ERP Agent OS is a universal platform where business users create ERP automations in natural language; the system verifies them through ERPGuard, compiles them into reusable skills, stores them in a Skill Registry, exposes them as safe MCP-style tools, and executes repeated runs with zero or minimal LLM tokens.

The differentiation centers on four pillars:

1. Minimum token cost.
2. Universal multi-ERP architecture.
3. Extreme ease of use for non-programmers.
4. Deep ERP integration through adapters and semantic guards.

## 1. Product Thesis

AI should be used to create and modify automations, not to pay token cost on every repeated execution.

ERP Agent OS turns natural-language ERP automation requests into reusable, validated, approved, deterministic skills. The LLM is valuable at design time: understanding intent, asking clarifying questions, drafting workflows, suggesting field mappings, generating tests, repairing broken mappings, and explaining failures. Repeated operational runs should not require the LLM to reason from scratch.

The product thesis is:

```text
Use AI to create the automation once.
Use deterministic runtime to execute it many times.
Use ERPGuard to verify that it is safe before it touches the ERP.
```

ERPGuard remains the mandatory safety kernel inside this larger product. It checks semantic ERP risk, evaluates guards, applies policies, blocks unsafe actions, requests approval when needed, and records audit evidence.

## 2. Architecture

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

### Business User

The business user describes the desired ERP automation in natural language. They should not need to understand YAML, Python, MCP, Odoo XML-RPC, SAP APIs, workflow engines, or policy DSL internals.

### ERP Agent Builder

ERP Agent Builder is the conversational creation layer. It understands the business request, asks clarification questions, proposes an automation, explains expected behavior, and sends the structured draft through the rest of the platform.

### Process Builder

Process Builder converts the user intent into a structured workflow draft: triggers, inputs, steps, conditions, expected outputs, required ERP objects, required guards, and approval points.

### ERPGuard Safety Kernel

ERPGuard verifies the proposed automation and every risky run. It provides canonical model validation, semantic guard evaluation, risk classification, approval requirements, fail-closed behavior, and audit evidence.

### Skill Compiler

Skill Compiler converts a validated process into a reusable skill package with schemas, policies, guards, permissions, tests, examples, MCP tool metadata, and audit configuration.

### Skill Registry

Skill Registry stores skill versions, lifecycle state, ownership, approval metadata, permissions, examples, semantic metadata, and audit links.

### Semantic Skill Discovery

Semantic Skill Discovery retrieves the relevant approved skills for a user request or runtime context without loading the full registry into the LLM context.

### MCP Gateway

MCP Gateway exposes approved ERP skills as MCP-style tools. It does not expose raw ERP methods by default.

### Deterministic Runtime

Deterministic Runtime executes approved skills without LLM reasoning on every run. It validates inputs, loads the skill version, calls ERPGuard, uses ERP adapters, produces structured outputs, and writes audit events.

### ERP Adapter

ERP Adapter translates canonical ERP objects, fields, capabilities, permissions, and actions into the native ERP implementation.

## 3. Differentiation

### n8n, Make, Zapier

n8n, Make, and Zapier automate workflows and integrations.

ERP Agent OS compiles safe ERP skills. It understands ERP semantics through canonical objects, adapters, and guards. It does not only move data between apps; it verifies whether an ERP operation should be allowed, warned, blocked, or routed through approval.

Key difference:

```text
n8n automates workflows.
ERP Agent OS compiles safe ERP skills.
```

### UiPath and Power Automate

UiPath and Power Automate automate tasks, screens, scripts, and enterprise workflows.

ERP Agent OS focuses on semantically safe ERP automation. Its core artifact is not a bot or a flow, but a reusable ERP skill with guards, permissions, tests, audit configuration, and deterministic runtime behavior.

### SAP Joule and Microsoft Copilot

SAP Joule and Microsoft Copilot are powerful vendor-specific ERP assistants.

ERP Agent OS is vendor-neutral. It starts with Odoo, then ERPNext, then partial SAP, Dynamics, and NetSuite adapters. The universal layer is the skill model, safety kernel, registry, MCP gateway, deterministic runtime, and canonical ERP model. ERP depth comes from adapters and packs.

Key difference:

```text
Copilots are vendor-specific.
ERP Agent OS is vendor-neutral.
```

### Generic MCP Agents

Generic MCP agents expose tools to an LLM and often require repeated reasoning at runtime.

ERP Agent OS exposes safe ERP skills with schemas, guards, permissions, approvals, and audit evidence. The MCP tool is the compiled skill, not a raw ERP operation.

Key differences:

```text
Generic agents spend tokens repeatedly.
ERP Agent OS compiles deterministic skills.

Generic MCP exposes tools.
ERP Agent OS exposes safe ERP skills with guards.
```

### Generic Agent Security Tools

Generic agent security tools protect prompts, tool calls, or agent policies at a broad level.

ERP Agent OS protects ERP operations semantically. It knows about sales orders, inventory moves, manufacturing, invoices, permissions, formulas, stock, lots, approvals, and audit evidence through ERPGuard and adapters.

## 4. Token Economics

Token economics is a product feature, not an implementation detail.

### First-Run Creation Cost

First-run creation cost is the token cost paid to transform a business request into a validated skill.

It may include:

- understanding the natural-language request;
- asking clarification questions;
- drafting the workflow;
- mapping ERP fields;
- proposing guards;
- generating tests;
- explaining the preview;
- producing the skill package.

This cost is acceptable because it creates a reusable operational asset.

### Repeated Deterministic Execution Cost

Repeated deterministic execution cost is the cost of running an approved skill again.

The target is zero LLM tokens by default. A repeated run should use input validation, deterministic workflow steps, ERPGuard checks, adapter calls, structured outputs, and audit writes.

### Repair Cost

Repair cost is the token cost paid when a skill must be updated because something changed or failed.

Examples:

- an ERP field was renamed;
- an adapter mapping changed;
- a guard needs adjustment;
- a schema changed;
- a test failed;
- a new ERP version behaves differently.

Repair must create a new draft or version. It must not silently mutate an approved active skill.

### Explanation Cost

Explanation cost is the token cost paid when a user asks why something happened.

Examples:

- why a skill blocked a sales order;
- why approval is required;
- what changed between versions;
- how to fix a mapping;
- what an audit trail means.

Explanations must be grounded in ERPGuard evidence, runtime events, and skill metadata.

### Token Break-Even Point

The token break-even point is the number of repeated executions after which compiling a deterministic skill is cheaper than using a generic agent to reason through every run.

```text
first_run_creation_cost + repair_cost + explanation_cost
<
generic_agent_cost_per_run * number_of_repeated_runs
```

ERP Agent OS should reach break-even quickly for recurring ERP processes such as sales order preflight, import checks, access diagnostics, invoice checks, stock checks, and manufacturing readiness checks.

## 5. Skill Package Format

A skill package is a versioned, portable automation artifact.

Required package structure:

```text
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

Defines skill identity, name, version, owner, status, ERP scope, description, lifecycle state, and registry metadata.

### `workflow.yaml`

Defines deterministic steps, branching, preflight calls, adapter calls, outputs, idempotency behavior, and failure handling.

### `policy.yaml`

Defines policy-level decisions, risk thresholds, approval requirements, and fail-closed behavior.

### `guards.yaml`

Lists required semantic guards such as Formula Guard, stock guard, lot traceability guard, import guard, or access rule guard.

### `permissions.yaml`

Defines who can run, approve, modify, publish, deprecate, or inspect the skill.

### `input_schema.json`

Defines strict runtime inputs.

### `output_schema.json`

Defines strict runtime outputs.

### `tests/`

Contains generated and curated test cases for positive, warning, blocking, approval, and error scenarios.

### `examples/`

Contains sample inputs, outputs, previews, and business explanations.

### `mcp_tool_definition.json`

Defines the safe MCP-style tool exposed by the MCP Gateway.

### `audit_config.yaml`

Defines what evidence must be stored at design time and runtime.

## 6. Skill Lifecycle

```text
draft -> generated -> validated -> tested -> previewed -> approved -> published -> active -> deprecated
```

### draft

The business user describes a desired automation or starts from a template.

### generated

ERP Agent Builder and Process Builder produce a structured skill draft.

### validated

The system validates schemas, workflow structure, required guards, policy references, permissions, mappings, and ERP adapter capabilities.

### tested

Generated and curated tests pass against fake adapters, fixtures, and allowed read-only samples.

### previewed

The user sees expected impact before activation. Preview must show expected reads, potential writes, blocks, warnings, approvals, and audit evidence.

### approved

A human approver accepts the skill version with an approval reason.

### published

The skill is stored in the Skill Registry and can be discovered.

### active

The skill can run through Deterministic Runtime and be exposed through the MCP Gateway.

### deprecated

The skill is retained for audit and rollback but should not be used for new runs.

## 7. Ease Of Use

Business users should never need to see YAML, Python, MCP definitions, adapter code, XML-RPC calls, JSON schemas, or policy DSL files.

Business user flow:

1. Describe automation.
2. Answer clarification questions.
3. Preview impact.
4. Run generated tests.
5. Approve.
6. Activate.

The interface should present business concepts:

- what the automation does;
- which ERP records it reads;
- which actions it may perform;
- which risks it checks;
- which approvals it requires;
- which tests passed;
- what will be audited;
- how to turn it off or edit it.

Technical artifacts remain inspectable for developers and consultants, but hidden by default from business users.

## 8. Universal ERP Strategy

ERP Agent OS is universal by architecture and deep by adapter.

### Canonical ERP Model

Skills target canonical ERP objects and actions instead of vendor-native methods.

Examples:

- `SalesOrder`;
- `SalesOrderLine`;
- `Product`;
- `Customer`;
- `InventoryMove`;
- `ManufacturingOrder`;
- `Invoice`;
- `AccessRule`;
- `AutomatedAction`.

Skills should refer to `confirm_sales_order`, not `sale.order.action_confirm()`.

### ERP Adapter SDK

The ERP Adapter SDK defines how each ERP exposes objects, fields, permissions, reads, simulations, controlled actions, native audit, and capability metadata.

### Object Mappings

Object mappings translate native ERP records into canonical objects.

Examples:

- Odoo `sale.order` -> `SalesOrder`;
- Odoo `product.product` -> `Product`;
- ERPNext `Sales Order` -> `SalesOrder`;
- SAP sales document -> `SalesOrder`.

### Field Mapping UI

Field Mapping UI lets consultants map native and custom fields without editing code.

Examples:

- capacity field;
- formula model;
- formula line relation;
- stock location field;
- lot or serial tracking field;
- margin field;
- custom approval field.

### Domain Packs

Domain packs provide reusable skills, guards, mappings, and tests for ERP domains.

Examples:

- sales;
- inventory;
- purchasing;
- manufacturing;
- accounting;
- access control;
- imports.

### Industry Packs

Industry packs provide specialized rules and examples.

Examples:

- fragrance manufacturing;
- food production;
- wholesale distribution;
- field services;
- regulated inventory;
- project-based services.

### Adapter Roadmap

Start with Odoo as the first deep adapter.

Then add ERPNext as the second open-source adapter to validate universal design.

Then add partial adapters for SAP, Dynamics, and NetSuite focused on read-only preflight, mappings, and selected high-value guards before any broad write support.

## 9. Relationship With Existing Code

Current ERPGuard code becomes the first safety kernel.

Current mapping:

- Formula Guard becomes the first reusable skill/guard.
- Fake adapter remains the test adapter.
- Odoo adapter becomes the first real adapter.
- Current canonical SalesOrder models become the first canonical ERP model slice.
- Current preflight service becomes the first deterministic runtime path for guarded skill runs.
- Current policy loader and policy engine become the first guard metadata and decision layer.
- Current audit retrieval becomes the first evidence trail.

This strategy does not replace ERPGuard. It elevates ERPGuard into the safety kernel of ERP Agent OS.

## 10. MVP Direction

The next MVP after the current preflight core should add the smallest useful skill loop.

Scope:

- Skill model.
- Skill Registry.
- Convert Formula Guard preflight into first skill.
- `POST /v1/skills`.
- `GET /v1/skills`.
- `POST /v1/skills/{skill_id}/run`.
- Deterministic runtime using current preflight service.

The first skill should wrap the current Formula Guard preflight flow and prove that the platform can:

- register a skill;
- expose it as a safe runtime operation;
- run it against the fake adapter;
- run it against the Odoo adapter when configured;
- produce the same ERPGuard decision and audit evidence;
- repeat execution without LLM involvement.

No code is required by this document. It defines product direction for the next implementation plan.

## Acceptance Boundary

This is a documentation-only strategic positioning update. It must not require runtime code changes.
