# 14 ERP Agent OS Strategic Vision

**Status:** Parent-level product direction child spec  
**Date:** May 18, 2026  
**Relationship to ERPGuard:** ERPGuard remains the safety kernel. The parent product is now ERP Agent OS.

ERP Agent OS is a universal platform where business users create ERP automations in natural language; the system verifies them through ERPGuard, compiles them into reusable skills, stores them in a Skill Registry, exposes them as safe MCP-style tools, and executes repeated runs with zero or minimal LLM tokens.

The core category is:

> ERP automations created with natural language, converted into safe skills, and executed with minimum token cost.

## 1. Product Thesis

AI should be used to create and modify automations, not to pay token cost on every repeated execution.

Most agentic ERP workflows spend tokens every time they run:

```text
user request
-> LLM reasoning
-> tool selection
-> tool execution
-> result interpretation
-> tokens again on the next run
```

ERP Agent OS should work differently:

```text
first run / creation
-> LLM helps design the automation
-> ERPGuard verifies safety
-> Skill Compiler produces a reusable skill
-> Skill Registry stores it

repeated runs
-> deterministic runtime executes the skill
-> ERPGuard validates risky operations
-> ERP adapter performs governed ERP access
-> zero or minimal LLM tokens
```

The commercial promise is:

> Use AI to design the automation. Do not pay AI every time the same process repeats.

ERPGuard is the safety kernel inside this platform. It verifies whether an ERP action or workflow is safe, allowed, explainable, and auditable. ERP Agent OS adds the higher-level lifecycle: create, verify, compile, publish, execute cheaply, and audit.

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

### Layering Principle

ERP Agent OS must be universal by architecture and deep by adapter.

Universal layer:

- skill format;
- workflow runtime;
- policy and guard engine;
- audit store;
- MCP Gateway;
- Semantic Skill Registry;
- natural language builder;
- deterministic skill runtime.

ERP-specific layer:

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

The universal layer defines what a safe ERP skill is. The adapter layer translates that skill into each ERP's native objects, fields, permissions, and process semantics.

### Core Flow

1. A business user describes an automation in natural language.
2. ERP Agent Builder clarifies intent, missing fields, and business constraints.
3. Process Builder converts the request into a structured workflow draft.
4. ERPGuard Safety Kernel checks risk, permissions, invariants, approvals, and failure behavior.
5. Skill Compiler converts the approved workflow into a reusable skill package.
6. Skill Registry stores the skill, version, tests, examples, permissions, and metadata.
7. Semantic Skill Discovery retrieves only the most relevant skills for future requests.
8. MCP Gateway exposes approved skills as safe MCP-style tools.
9. Deterministic Runtime executes compiled skills without repeated LLM reasoning.
10. ERP Adapter maps canonical actions and objects to the target ERP.
11. Audit Store records design, approval, execution, decisions, and evidence.

## 3. Differentiation

ERP Agent OS is differentiated by four pillars:

1. Minimum token cost.
2. Universal multi-ERP architecture.
3. Extreme ease of use for non-programmers.
4. Deep ERP integration through adapters and semantic guards.

### Against n8n, Make, and Zapier

n8n, Make, and Zapier automate workflows by connecting applications and APIs.

ERP Agent OS compiles safe ERP skills.

The difference is not only workflow automation. ERP Agent OS understands ERP semantics, validates actions through ERPGuard, packages automations as reusable skills, exposes them safely through MCP-style tools, and records audit evidence.

### Against UiPath and Power Automate

UiPath and Power Automate are strong automation platforms, especially for enterprise workflows, RPA, and Microsoft ecosystems.

ERP Agent OS is focused on agent-created ERP skills with deterministic repeated execution. The system uses natural language to create automations, verifies them against ERP-specific safety rules, and runs approved skills without needing the LLM to reason through every execution.

### Against SAP Joule and Microsoft Copilot

SAP Joule and Microsoft Copilot are powerful but vendor-specific or ecosystem-specific.

ERP Agent OS is vendor-neutral. It starts with Odoo, then expands through ERPNext and partial SAP, Dynamics, and NetSuite adapters. The skill model remains portable even when the adapter implementation is ERP-specific.

### Against Generic MCP Agents

Generic MCP agents expose tools to an LLM.

ERP Agent OS exposes safe ERP skills with guards.

It should not expose raw tools such as:

- `odoo.write`;
- `odoo.call_method`;
- `odoo.execute_action`;
- unrestricted SQL;
- raw stock validation;
- raw payment execution.

It should expose high-level safe tools such as:

- `safe_validate_sale_order`;
- `safe_prepare_purchase_draft`;
- `safe_import_products_preflight`;
- `safe_explain_access_issue`.

### Against Generic Agent Security Tools

Generic agent security tools protect prompts, tool access, or general execution boundaries.

ERPGuard protects ERP semantics. It understands business objects, process risk, canonical actions, adapter capabilities, formulas, stock, lots, access rules, approvals, and audit evidence.

ERP Agent OS uses that safety kernel to make created automations safe enough to reuse.

## 4. Token Economics

ERP Agent OS should make token cost a design constraint, not an afterthought.

### First-Run Creation Cost

The first creation of a skill may use LLM tokens for:

- understanding the user's natural language request;
- asking clarification questions;
- drafting the process;
- proposing mappings;
- generating tests;
- explaining preview results;
- producing the initial skill package.

This cost is acceptable because it creates a reusable asset.

### Repeated Deterministic Execution Cost

Once approved and published, the skill should execute through deterministic runtime.

Repeated execution should use zero LLM tokens by default.

The runtime should:

- validate inputs;
- load the target ERP object;
- map native records to canonical objects;
- evaluate ERPGuard guards;
- execute allowed workflow steps;
- return structured output;
- write audit events.

### Repair Cost

LLM usage is allowed when the skill cannot run because of a changed ERP schema, missing field, unexpected adapter payload, broken mapping, or unknown runtime failure.

Repair should create a new draft version, not silently mutate the active skill.

### Explanation Cost

LLM usage is allowed when the user asks for a natural language explanation of a decision, failure, or audit trail.

The explanation should be generated from structured evidence, not from raw unrestricted ERP access.

### Token Break-Even Point

The break-even point is reached when:

```text
creation_tokens + occasional_repair_tokens
<
tokens_that_would_have_been_spent_reasoning_through_every_repeated_run
```

For high-frequency ERP processes, deterministic skills should become cheaper quickly. This is a central product advantage.

## 5. Skill Package Format

A skill is a package containing:

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

### skill.yaml

Declares identity, name, description, version, owner, lifecycle state, ERP scope, runtime mode, and whether LLM is required.

Example:

```yaml
skill:
  id: safe_sale_order_preflight
  name: Validar pedido antes de fabricacion
  version: 1.0.0
  status: active
  runtime: deterministic
  llm_required: false

trigger:
  type: manual_or_event
  event: sales_order_created

erp_objects:
  - SalesOrder
  - Product
  - Inventory
  - ManufacturingOrder
```

### workflow.yaml

Defines trigger, workflow steps, branches, expected inputs, outputs, and failure behavior.

Example:

```yaml
workflow:
  - load_sales_order
  - validate_formula
  - check_stock
  - check_lots
  - produce_report
```

### policy.yaml

Declares policy behavior, risk handling, approval requirements, and fail-closed rules.

### guards.yaml

Declares guard dependencies such as:

- `formula_guard`;
- `stock_guard`;
- `lot_traceability_guard`;
- `access_rule_guard`.

### permissions.yaml

Declares required canonical and ERP permissions.

### input_schema.json

Defines runtime input schema.

Example:

```json
{
  "type": "object",
  "required": ["sales_order_id"],
  "properties": {
    "sales_order_id": { "type": "string" }
  }
}
```

### output_schema.json

Defines structured output schema for runtime and MCP responses.

### tests/

Contains generated and curated tests for valid, invalid, edge, permission, and regression scenarios.

### examples/

Contains sample inputs, outputs, ERP fixtures, and audit traces.

### mcp_tool_definition.json

Defines the safe MCP-style tool exposed by the gateway.

### audit_config.yaml

Declares which design-time and runtime events must be recorded.

## 6. Skill Lifecycle

```text
draft -> generated -> validated -> tested -> previewed -> approved -> published -> active -> deprecated
```

### draft

The user describes the automation or selects a template.

### generated

ERP Agent Builder and Process Builder create an initial skill draft.

### validated

Schemas, workflow syntax, policy references, guard references, permissions, and mappings are structurally valid.

### tested

Generated and curated tests pass against fake fixtures and, where allowed, read-only ERP samples.

### previewed

The user sees what the skill would allow, block, read, write, or require approval for.

### approved

A human approves the skill version.

### published

The skill is available in the registry and can be discovered.

### active

The skill can run through deterministic runtime and MCP Gateway.

### deprecated

The skill remains available for audit history but should not be used for new executions.

## 7. Ease of Use

The business user should not see YAML, Python, MCP, adapters, schemas, or DSL internals.

Business user flow:

1. Describe automation.
2. Answer clarification questions.
3. Preview impact.
4. Run generated tests.
5. Approve.
6. Activate.

Example request:

> "Cuando entre un pedido, comprueba si hay formula, stock y lotes. Si falta algo, avisame y no fabriques."

The system should:

- understand the process;
- ask only necessary questions;
- detect ERP objects and fields;
- propose safe mappings;
- show sample orders that would pass or fail;
- explain what would be blocked;
- generate tests;
- request approval;
- activate the skill.

The implementation may store YAML and schemas internally, but the product experience must stay form-driven, preview-driven, and conversational.

## 8. Universal ERP Strategy

ERP Agent OS should not claim complete support for every ERP immediately.

The correct promise is:

> One skill and guard architecture for any ERP, starting with Odoo.

### Canonical ERP Model

Skills should target canonical ERP concepts, not native ERP methods.

Initial canonical objects:

- `SalesOrder`;
- `SalesOrderLine`;
- `Product`;
- `Customer`;
- `Company`;
- `Invoice`;
- `InventoryMove`;
- `ManufacturingOrder`;
- `AccessRule`.

Initial canonical actions:

- `inspect_sales_order`;
- `validate_formula`;
- `confirm_sales_order`;
- `inspect_access_rules`;
- `check_stock`;
- `prepare_purchase_draft`.

Skills should say `confirm_sales_order`, not `sale.order.action_confirm()`.

### ERP Adapter SDK

Each ERP adapter translates canonical objects and actions into native ERP behavior.

Adapter responsibilities:

- schema discovery;
- object mapping;
- field mapping;
- relationship mapping;
- permission inspection;
- safe read/write capability exposure;
- mockability for tests;
- error normalization;
- audit evidence.

### Object Mappings

Adapters must map native ERP records to canonical objects.

Example:

```text
Odoo sale.order -> SalesOrder
Odoo sale.order.line -> SalesOrderLine
Odoo product.product/product.template -> Product
```

### Field Mapping UI

Consultants should configure custom fields without writing code.

Examples:

- product capacity field;
- formula model;
- formula line relation;
- milliliters per unit field;
- lot tracking field;
- custom Studio fields.

### Domain Packs

Domain packs provide reusable mappings and guards for ERP domains such as sales, inventory, manufacturing, purchasing, accounting, and access control.

### Industry Packs

Industry packs provide specialized process knowledge for verticals such as fragrance manufacturing, food production, wholesale distribution, field services, and regulated inventory.

### Adapter Roadmap

1. Odoo first.
2. ERPNext next.
3. SAP, Dynamics, and NetSuite partial adapters later.

The product should remain honest: universal architecture first, deep integration adapter by adapter.

## 9. Relationship With Existing Code

The current ERPGuard implementation becomes the first safety kernel.

Existing modules map into the ERP Agent OS architecture as follows:

- canonical models become the first canonical ERP model foundation;
- Fake adapter remains the deterministic test adapter;
- Odoo adapter skeleton becomes the first real ERP adapter path;
- Formula Guard becomes the first reusable guard and future skill;
- YAML policy loader becomes the first policy metadata layer;
- Policy Engine becomes the first safety decision layer;
- Preflight Service becomes the first deterministic guard execution service;
- Connection API becomes the first ERP connection management layer;
- audit retrieval becomes the first evidence trail.

Formula Guard should evolve from a backend invariant into the first reusable ERP skill/guard package.

The current fake preflight flow is valuable because it proves the safety kernel can evaluate canonical ERP objects without a live ERP dependency.

## 10. MVP Direction

The next MVP after the current preflight core should demonstrate the first skill loop.

Scope:

- Skill model;
- Skill Registry;
- convert Formula Guard preflight into the first skill;
- `POST /v1/skills`;
- `GET /v1/skills`;
- `POST /v1/skills/{skill_id}/run`;
- deterministic runtime using the current preflight service.

### MVP Skill

`safe_order_formula_preflight`

Purpose:

Validate whether a sales order can safely continue before manufacturing or confirmation.

### MVP Flow

1. User creates or loads a Formula Guard skill draft.
2. System validates the skill package.
3. ERPGuard verifies the guard behavior.
4. Skill Registry stores the skill.
5. User runs the skill against a valid fake order.
6. User runs the skill against a formula mismatch fake order.
7. User runs the same skill a second time without LLM reasoning.
8. Audit endpoint shows skill version, input, decision, issues, and evidence.

### API Direction

```http
POST /v1/skills
GET /v1/skills
GET /v1/skills/{skill_id}
POST /v1/skills/{skill_id}/run
```

The first implementation should reuse current preflight service behavior instead of creating a separate execution engine too early.

## 11. Non-Goals

- No full UI yet.
- No marketplace yet.
- No autonomous write actions.
- No SAP/Dynamics/NetSuite full adapter.
- No unrestricted tool calling.
- No raw ERP write operation exposure.
- No arbitrary Python in user-defined guards.
- No live ERP dependency in automated tests.

Near-term work should keep the system narrow: skill schema, registry, deterministic runtime wrapper around preflight, audit trail, and safe MCP-style skill definitions.
