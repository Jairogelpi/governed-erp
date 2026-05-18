# 15 Universal ERP Connection And UI Automation Fallback

**Status:** Strategic connection and automation fallback spec  
**Date:** May 18, 2026  
**Relationship to ERP Agent OS:** Defines how ERP Agent OS connects to any ERP when direct API access is incomplete, unavailable, or unsafe.  
**Relationship to ERPGuard:** ERPGuard remains the mandatory safety kernel for risky ERP actions in every connector mode.

## Purpose

ERP Agent OS must connect to many ERPs with different levels of openness. Some ERPs expose clean APIs. Some expose partial APIs. Some expose MCP servers. Some only support CSV import/export. Some business-critical workflows are only reachable through a browser UI or desktop client.

This spec defines a layered universal connection strategy:

1. Native API adapter.
2. MCP adapter.
3. CSV/import-export adapter.
4. Browser DOM automation.
5. Desktop/vision computer-use automation.
6. Human-in-the-loop fallback.

## Core Thesis

If the ERP exposes a reliable API, use it. If not, ERP Agent OS should safely automate the ERP through its interface, like a human, but convert that learned interaction into a reusable, guarded, auditable skill that can run later with minimal or zero LLM tokens.

The goal is not free-form browser autonomy. The goal is to learn or define a process once, verify it through ERPGuard, compile it into a deterministic skill, and execute it later with strong evidence and fail-closed checks.

## 1. Universal Connector Router

Universal Connector Router chooses the best available connection mode for each ERP, object, action, and environment.

Supported connector modes:

- `native_api`;
- `mcp`;
- `csv_import_export`;
- `browser_dom`;
- `desktop_vision`;
- `human_assisted`.

The router should choose the safest, most deterministic, and most auditable connector mode available.

Priority order:

1. Use `native_api` when the ERP exposes reliable APIs for the required objects and operations.
2. Use `mcp` when a trusted MCP server exposes suitable high-level capabilities.
3. Use `csv_import_export` when data exchange is supported but APIs are missing or incomplete.
4. Use `browser_dom` when the ERP is web-based and actions can be automated with stable DOM, accessibility, labels, roles, and text selectors.
5. Use `desktop_vision` only when browser DOM automation is not enough.
6. Use `human_assisted` when automation confidence is insufficient or the action is too risky.

Connector selection must consider:

- ERP type and version;
- available APIs;
- available MCP servers;
- export/import capabilities;
- web or desktop deployment model;
- authentication method;
- object coverage;
- read/write capability;
- sandbox availability;
- risk level;
- audit evidence quality;
- deterministic repeatability;
- human approval requirements.

## 2. Connection Decision Tree

Connection setup should follow this flow:

```text
User connects ERP
-> detect API/MCP availability
-> inspect login/auth
-> test read capabilities
-> test write capabilities only in sandbox/manual mode
-> choose safest connector mode
```

Detailed decision tree:

1. User starts ERP connection setup.
2. System identifies ERP vendor, version, deployment type, and access method.
3. System checks whether a native adapter exists.
4. System checks whether reliable API credentials or OAuth can be configured.
5. System checks whether an MCP server exists and whether it exposes safe high-level capabilities.
6. System checks whether CSV/export/import is supported for target objects.
7. System checks whether the ERP is accessible through browser automation.
8. System checks whether a desktop/vision fallback is required.
9. System performs read-only tests first.
10. System tests write capabilities only in sandbox, demo data, or manual mode.
11. System computes connector confidence and risk.
12. System selects the safest connector mode.
13. System records connector evidence and limitations.

The router should prefer read-only verification until the user explicitly enables controlled write workflows. R3+ operations must still pass through ERPGuard and approval before any real ERP state change.

## 3. Native Adapter Path

Native adapters are the preferred path.

Use native APIs where available for:

- Odoo;
- ERPNext;
- SAP;
- Microsoft Dynamics;
- NetSuite;
- Sage;
- Oracle Fusion;
- Zoho;
- Holded;
- other ERPs with reliable API coverage.

Native adapter responsibilities:

- authenticate safely;
- inspect schema and metadata;
- read objects;
- map native objects to canonical ERP objects;
- inspect permissions where possible;
- simulate or infer impact where possible;
- execute controlled actions only after ERPGuard and approvals;
- normalize native errors;
- collect audit evidence.

Native adapters should expose capabilities explicitly:

```yaml
capabilities:
  read_sales_order: true
  read_products: true
  inspect_permissions: partial
  simulate_confirm_sales_order: false
  execute_confirm_sales_order: controlled
  supports_transactions: false
```

ERP Agent OS should never assume an adapter can perform an action just because the ERP has an API. Capability discovery must be explicit and tested.

## 4. MCP Adapter Path

MCP adapters are useful when a trusted MCP server already exposes ERP capabilities.

ERP Agent OS may connect to an MCP server when:

- the server is trusted;
- the available tools are inspectable;
- schemas are strict;
- permissions are clear;
- outputs are structured;
- raw dangerous operations can be blocked or wrapped;
- audit metadata can be captured.

MCP servers should be treated as connector sources, not as final authority.

ERP Agent OS must expose only safe high-level skills to downstream agents. It should not expose raw write operations such as:

- `odoo.write`;
- `execute_kw`;
- `sql.execute`;
- `post_invoice` without guard context;
- `validate_stock_picking` without guard context;
- `delete_records`;
- `change_permissions`.

Safe MCP exposure should look like:

```text
safe_sales_order_preflight
safe_prepare_purchase_draft
safe_import_products_preflight
safe_explain_access_issue
safe_order_formula_guard
```

If an MCP server exposes raw tools, ERP Agent OS should wrap them behind ERPGuard, skill permissions, and deterministic workflows before making them available as safe tools.

## 5. CSV/Import-Export Path

CSV/import-export is the fallback for ERPs with weak APIs but usable file exchange.

This path supports:

- exporting records for analysis;
- validating files before import;
- generating corrected import files;
- detecting duplicate records;
- checking required columns;
- mapping relationships;
- creating preflight reports;
- producing import-ready files for human review.

CSV/import-export adapter responsibilities:

- detect export formats;
- parse CSV, XLSX, XML, or vendor-specific files;
- map columns to canonical fields;
- validate data types;
- validate relationships;
- detect duplicates;
- produce import reports;
- generate safe import files;
- retain file hashes and evidence.

For write-like imports, ERP Agent OS must not blindly upload files. It must run ERPGuard preflight and require human approval for risky imports.

CSV/import-export is especially useful for:

- product imports;
- customer imports;
- supplier imports;
- price list updates;
- inventory adjustments;
- opening balances;
- migration checks.

## 6. Browser Automation Path

Browser DOM automation is the preferred UI automation fallback for web ERPs.

Use Playwright as the preferred UI automation engine.

Selector priority:

1. Stable DOM selectors.
2. Accessibility roles.
3. Labels.
4. Text selectors.
5. URL and route context.
6. Form field names and placeholders.
7. Accessibility tree.
8. Screenshots and visual matching.
9. Coordinates as last resort.

Coordinates are brittle and should only be used when all semantic selector strategies fail. Coordinate-based actions must have low confidence and should require additional verification or human confirmation.

Browser automation responsibilities:

- login through approved auth flows;
- navigate to known pages;
- identify records;
- read page state;
- fill forms;
- click safe buttons;
- detect modals and errors;
- capture screenshots;
- capture DOM snapshots;
- verify before/after state;
- stop on uncertainty.

Browser automation must prefer deterministic Playwright scripts over repeated LLM reasoning. The LLM may help create or repair scripts, but repeated execution should run without LLM by default.

## 7. Desktop/Vision Path

Desktop/vision automation is the fallback when browser DOM automation is not enough.

Use computer-use style automation only when:

- the ERP is desktop-only;
- the browser DOM is inaccessible;
- selectors are unavailable;
- the UI is rendered through canvas, remote desktop, Citrix, or VDI;
- the workflow cannot be reached through API, MCP, CSV, or browser DOM.

Every desktop/vision action must produce evidence:

- screenshot before the action;
- screenshot after the action;
- detected UI elements;
- intended action;
- confidence score;
- timestamp;
- user/session context;
- result verification.

R3+ actions require human approval before execution. Financial, stock, security, payment, deletion, and posting actions require stricter approval and ERPGuard preflight.

Desktop/vision automation should be considered less reliable than native API, MCP, CSV, or browser DOM. It must fail closed when state is uncertain.

## 8. UI Recorder

UI Recorder lets a human demonstrate a process once.

The recorder captures:

- DOM events;
- screenshots;
- labels;
- roles;
- URLs;
- route changes;
- form fields;
- field values where safe;
- clicked buttons;
- selected records;
- before/after states;
- modals and errors;
- outcomes.

The recorder should avoid storing secrets. Passwords, API keys, session tokens, and personal sensitive values must be redacted or excluded.

Recording flow:

1. Human starts recording.
2. Human performs the process once in a safe environment.
3. Recorder captures events and evidence.
4. System identifies stable selectors and page states.
5. System proposes a UI skill draft.
6. Human reviews the draft.
7. ERPGuard evaluates risks and guards.
8. The skill moves into validation and testing.

UI Recorder turns human know-how into a reusable automation asset.

## 9. UI Skill Compiler

UI Skill Compiler converts a recording into a deterministic UI skill package.

Generated artifacts:

- `workflow.yaml`;
- `selectors.yaml`;
- `guards.yaml`;
- `tests/`;
- `screenshots/`;
- `mcp_tool_definition.json`.

### `workflow.yaml`

Defines the step sequence, required inputs, page transitions, waits, checks, and expected outputs.

### `selectors.yaml`

Defines primary and fallback selectors for each UI element.

Selector entries should include:

- role;
- label;
- text;
- DOM selector;
- URL context;
- frame context;
- confidence;
- fallback strategy.

### `guards.yaml`

Defines ERPGuard checks that must pass before risky UI actions.

### `tests/`

Contains replay tests against fake pages, sandbox ERPs, or recorded fixtures.

### `screenshots/`

Stores evidence screenshots for training, testing, repair, and audit.

### `mcp_tool_definition.json`

Defines the safe tool exposed by MCP Gateway. It must describe the compiled UI skill, not raw browser control.

UI Skill Compiler must produce deterministic scripts that can run without the LLM unless a repair path is triggered.

## 10. Screen State Verifier

Screen State Verifier checks UI state before and after every UI step.

Before each step, verify:

- correct page;
- correct record;
- expected state;
- required fields are visible;
- target button or field exists;
- no unexpected modal or error is present.

After each step, verify:

- expected result;
- expected state transition;
- no unexpected modal;
- no unexpected validation error;
- no navigation to an unknown page;
- no incorrect record selected;
- no silent failure.

Verification sources:

- DOM snapshot;
- URL;
- page title;
- breadcrumbs;
- labels;
- accessibility tree;
- text content;
- screenshot;
- adapter/API readback where available.

If state is uncertain, the runtime must stop and request human assistance or trigger the Repair Agent in a safe non-writing mode.

## 11. Repair Agent

The Repair Agent uses the LLM only when UI automation fails.

Repair triggers:

- selector changed;
- button moved;
- modal appeared;
- field renamed;
- page changed;
- workflow step timed out;
- expected state did not appear;
- accessibility role changed;
- form validation changed.

Repair process:

1. Stop the current run.
2. Capture screenshot and DOM evidence.
3. Classify the failure.
4. Ask the LLM to propose a selector or workflow repair.
5. Test repair in sandbox, dry-run, or human-assisted mode.
6. Create a new skill version or patch proposal.
7. Require approval before active skill mutation.

The Repair Agent must not silently continue risky execution after a UI failure. Repair is a controlled design-time or maintenance activity, not a license for autonomous production changes.

## 12. Token Economics

First learning and repair may use LLM tokens.

Repeated UI skill execution should use deterministic Playwright or automation runtime with no LLM unless failure.

Cost model:

```text
learning_tokens + repair_tokens + explanation_tokens
<
tokens_spent_by_generic_agent_reinterpreting_ui_on_every_run
```

The desired pattern is:

```text
human demonstration once
-> LLM-assisted compilation once
-> deterministic replay many times
-> LLM repair only on failure
```

Token usage is acceptable when it creates or repairs reusable automation assets. Token usage is wasteful when every repeated execution requires the LLM to rediscover the same screen flow.

## 13. Safety Rules

Safety rules apply to every connector mode.

- No critical submit, confirm, post, pay, delete, permission change, stock validation, or manufacturing finalization without ERPGuard preflight and human approval.
- No raw browser autonomy for financial, stock, or security actions.
- Always log screenshots and DOM evidence for UI automation.
- Always log connector mode and confidence.
- Stop if state is uncertain.
- Stop if the wrong record is detected.
- Stop if an unexpected modal or error appears.
- Stop if a selector becomes ambiguous.
- Redact secrets from recordings, screenshots, logs, and audit evidence where possible.
- Use sandbox or manual mode for write capability tests.
- Prefer read-only diagnosis before any write-like workflow.
- Require R3+ approval before production execution.

ERPGuard remains the authority for semantic safety. UI automation is only a transport layer and must not bypass guards, approvals, or audit requirements.

## 14. MVP Implication

Do not implement full UI automation yet.

Next future MVP:

1. Create a local Fake ERP web page.
2. Record a simple browser workflow.
3. Compile it into a UI skill.
4. Rerun it with Playwright without LLM.
5. Audit every step.

The initial UI automation MVP should avoid production ERPs and avoid critical write actions. It should prove the loop:

```text
human demonstration
-> recording
-> UI skill compilation
-> deterministic replay
-> evidence capture
-> audit retrieval
```

Only after this local fake ERP workflow is reliable should ERP Agent OS consider browser automation against real ERP sandboxes.

This is a documentation-only spec. It does not require runtime code changes.
