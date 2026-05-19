# Sprint 1 - Real Odoo Connection & Diagnosis

**Goal:** Build the first real product piece: a read-only connection to Odoo plus an initial ERP diagnosis.

## Objective

This sprint lets the user connect a real Odoo instance in read-only mode, validate credentials, inspect metadata, detect modules/models/fields, identify likely formula mappings, and receive a usable diagnosis in the API and demo surface.

It does not create skills, execute automations, or write anything to Odoo.

## User Outcome

The user can enter:

- Odoo URL;
- Database;
- Username;
- API Key;
- Formula model;
- Capacity field;
- Formula line field mappings.

Then they can run:

- Test connection;
- Diagnose Odoo;
- Read raw sales order summary.

The system returns a structured read-only diagnosis with warnings and a recommended next action.

## Scope

### Included

- Odoo connection endpoint.
- Odoo connection test endpoint.
- Read-only Odoo diagnosis endpoint.
- Read-only Odoo client wrapper.
- XML-RPC authentication and version check.
- Detection of installed modules.
- Detection of key models.
- Detection of model fields.
- Detection of custom fields.
- Limited sample reads for sales orders and products.
- Initial formula model detection.
- Audit/log entry for diagnosis runs.
- API tests with a fake Odoo client.
- Documentation.
- Minimal `/demo` or API-first surface.

### Excluded

- Confirm sales orders.
- Create, update, delete, or copy records.
- Execute `action_*` methods.
- Create manufacturing orders.
- Create purchases.
- Create invoices.
- MCP.
- Business Memory.
- Agent Builder.
- New Skill Compiler.
- Real browser automation on Odoo.
- Universal multi-ERP automation.

## Security Rule

Zero writes to Odoo.

Only these XML-RPC methods are allowed in the read-only layer:

- `version`
- `authenticate`
- `search_read`
- `read`
- `fields_get`
- `search_count`

Any other method must raise `ReadOnlyViolationError`.

## Recommended Data Shape

The diagnosis response should include:

- `status`
- `erp_type`
- `server_version`
- `uid`
- `read_only_mode`
- detected modules
- detected core models
- detected custom models
- detected custom fields
- sample sales orders
- sample products
- warnings
- next recommended action

## Acceptance Criteria

- A real Odoo connection can be created without exposing the API key.
- A connection test returns version and uid.
- A diagnosis run stays read-only.
- Basic modules and models are detected.
- Custom fields are detected.
- Limited sample reads work.
- Forbidden methods are blocked by code and tests.
- `/demo` or the API shows the diagnosis.
- The test suite passes.
- README and AGENTS are updated.

## No-Goals

This sprint does not implement the broader ERP Agent OS vision.

It only opens the door to real Odoo in a safe, inspectable way before any write capability exists.
