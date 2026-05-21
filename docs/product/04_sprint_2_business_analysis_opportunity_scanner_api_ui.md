# Sprint 2 - Business Analysis & Opportunity Scanner API/UI

**Goal:** Turn the real Odoo read-only connection into a business analysis layer that can surface recommendations, estimate ROI, and create non-executable automation drafts.

## Objective

This sprint sits on top of Sprint 1.

It does not write to Odoo and it does not execute any automation draft. It reads the existing read-only Odoo connection, builds a business snapshot, derives signals, scans opportunities, scores ROI, and creates dry-run-only automation drafts.

## User Outcome

The user can open the product UI, select an Odoo connection, and run:

- business analysis;
- opportunity scanning;
- ROI review;
- automation draft creation.

The product shows recommendation cards that explain what is worth doing next and why.

## Scope

### Included

- Business snapshot service.
- Business signal derivation service.
- Opportunity scanner service.
- ROI scoring service.
- Skill draft builder service.
- API under `/v1/product`.
- Minimal `/demo` business analysis UI section.
- Persistence for snapshots, scans, opportunities, and drafts.
- Tests for services, API, ROI, scanner, draft builder, and UI.
- README and AGENTS updates.

### Excluded

- Odoo writes.
- `create`, `write`, `unlink`, `copy`, `action_*`, `button_*` calls.
- Executing any automation draft.
- MCP.
- Business Memory.
- Agent Builder.
- Browser automation on Odoo.
- Universal multi-ERP automation.

## Safety Rule

Every flow stays read-only against Odoo.

Drafts must be persisted with:

- `write_actions = false`
- `runtime_mode = dry_run_only`

## Recommended Data Flow

1. Load a read-only Odoo connection.
2. Capture a business snapshot.
3. Derive signals from the snapshot.
4. Scan opportunities.
5. Score ROI.
6. Show recommendation cards.
7. Persist a dry-run automation draft when the user asks for one.

## Recommended API Shape

- `POST /v1/product/connections/{connection_id}/analyze`
- `POST /v1/product/opportunities/{opportunity_id}/draft`
- `GET /v1/product/snapshots/{snapshot_id}`
- `GET /v1/product/scans/{scan_id}`
- `GET /v1/product/drafts/{draft_id}`

## Acceptance Criteria

- Business snapshot persists.
- Signals persist.
- Scans persist.
- Opportunities persist.
- Drafts persist.
- Drafts are non-executable.
- ROI is shown in the UI and API.
- The UI can run analysis and create drafts.
- No Odoo write method is used.
- The existing v0.7 and Sprint 1 behavior remains intact.

## No-Goals

This sprint does not add real ERP execution.

It only adds the business-analysis layer that helps explain where automation should happen next.
