# ERPGuard

ERPGuard is a semantic safety layer for ERP operations. This repository is currently in Phase 1: the Odoo Preflight Core backend foundation.

## Release Candidate v0.13.0-rc1 — Validated & Accepted

ERPGuard v0.13.0-rc1 is validated and accepted (Sprint 27). The full operator
demo runs end-to-end from a clean state in under 5 minutes. All 12 safety
invariants enforced. 1162+ tests passing.

RC validation docs:

- [docs/release/07_rc_validation_rehearsal.md](docs/release/07_rc_validation_rehearsal.md)
- [docs/release/08_rc_gap_log.md](docs/release/08_rc_gap_log.md)
- [docs/release/09_rc_acceptance_report.md](docs/release/09_rc_acceptance_report.md)

Standalone validation script:

```bash
uvicorn apps.api.main:app --port 8000 &
python scripts/validate_rc_demo.py --base-url http://127.0.0.1:8000
```

## Release Candidate v0.13.0-rc1 — Operator Demo & Evidence Pack

ERPGuard v0.13.0-rc1 closes the Record-to-Skill loop (Sprints 20–26) and packages it as a reproducible operator demo with a full release evidence pack.

Sprint 26 operator evidence endpoints:

- `POST /v1/operator/demo-seed` — seeds the full end-to-end demo scenario
- `POST /v1/operator/evidence-packs` — assembles a release evidence pack
- `GET /v1/operator/evidence-packs/{id}` — retrieves a pack
- `GET /v1/operator/evidence-packs/{id}/safety-report` — 12 enforced safety invariants
- `GET /v1/operator/evidence-packs/{id}/final-report` — complete operator demo report
- `GET /v1/operator/demo-runbook` — 15 documented operations across Sprints 20–26

Demo docs:

- [docs/demo/00_operator_demo_overview.md](docs/demo/00_operator_demo_overview.md)
- [docs/demo/01_end_to_end_scenario.md](docs/demo/01_end_to_end_scenario.md)
- [docs/demo/02_operator_runbook.md](docs/demo/02_operator_runbook.md)
- [docs/demo/03_safety_boundaries.md](docs/demo/03_safety_boundaries.md)
- [docs/demo/04_failure_modes.md](docs/demo/04_failure_modes.md)
- [docs/demo/05_release_evidence_pack.md](docs/demo/05_release_evidence_pack.md)
- [docs/demo/06_tfm_defense_script.md](docs/demo/06_tfm_defense_script.md)

## Release Candidate v0.12.0-rc1

ERPGuard v0.12.0-rc1 is packaged as an operator release candidate.

Release validation endpoints:

- `GET /v1/release/health`
- `GET /v1/release/readiness-report`
- `POST /v1/release/demo-seed`
- `POST /v1/release/operator-smoke`
- `GET /v1/release/safety-boundaries`

Clean install helpers:

- [docs/release/01_install_and_run.md](docs/release/01_install_and_run.md)
- [docs/release/05_clean_install_vps_validation.md](docs/release/05_clean_install_vps_validation.md)
- [docs/release/06_release_fix_log.md](docs/release/06_release_fix_log.md)
- `.env.example`
- `scripts/check_release_install.py`
- `scripts/start_release_candidate.sh`
- `scripts/start_release_candidate.ps1`

Quick clean-install shape:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
bash scripts/start_release_candidate.sh
```

Then validate from another shell:

```bash
python scripts/check_release_install.py --base-url http://127.0.0.1:8000
```

Safety defaults remain locked:

```text
ALLOW_GENERIC_REAL_ODOO_WRITES=false
ALLOW_R3_R4_REAL_WRITES=false
```

## VPS Operations

Sprint 14 adds deployment and operations hardening for running the release candidate as a VPS service.

Deployment docs:

- [docs/deployment/00_vps_deployment.md](docs/deployment/00_vps_deployment.md)
- [docs/deployment/01_systemd_service.md](docs/deployment/01_systemd_service.md)
- [docs/deployment/02_operations_runbook.md](docs/deployment/02_operations_runbook.md)
- [docs/deployment/03_backup_and_restore.md](docs/deployment/03_backup_and_restore.md)
- [docs/deployment/04_update_procedure.md](docs/deployment/04_update_procedure.md)
- [docs/deployment/05_deployment_validation_report.md](docs/deployment/05_deployment_validation_report.md)

Deployment assets:

- `deploy/systemd/erpguard.service`
- `deploy/env/erpguard.env.example`
- `scripts/ops_check.py`
- `scripts/backup_release_db.py`
- `scripts/update_release_candidate.sh`

Recommended VPS paths:

```text
/opt/erpguard/app
/opt/erpguard/.venv
/var/lib/erpguard
/var/lib/erpguard/backups
/etc/erpguard/erpguard.env
/etc/systemd/system/erpguard.service
```

Post-deploy check:

```bash
python scripts/ops_check.py --base-url http://127.0.0.1:8000
```

Backup:

```bash
python scripts/backup_release_db.py
```

Deployment scripts and docs keep generic writes, R3/R4 writes, and write pilots disabled by default.

## Connector & Skill Marketplace

Sprint 15 adds an internal connector and skill-template marketplace foundation.

Marketplace endpoints:

- `GET /v1/marketplace/connectors`
- `GET /v1/marketplace/connectors/{connector_id}`
- `GET /v1/marketplace/skill-templates`
- `GET /v1/marketplace/skill-templates/{template_id}`
- `POST /v1/marketplace/skill-templates/{template_id}/check-requirements`
- `POST /v1/marketplace/skill-templates/{template_id}/install-draft`
- `GET /v1/marketplace/installed`

Implemented connector:

- Odoo

Placeholder connectors:

- Gmail
- Google Calendar
- Google Drive
- WhatsApp
- Slack
- Custom HTTP API

Templates install only as automation drafts. The existing review, validation, compile, approval, and activation gates remain mandatory. No MCP runtime, OAuth production flow, real Gmail/WhatsApp execution, generic ERP writes, or R3/R4 writes are added.

## Safe Agent Builder

Sprint 16 adds a controlled Agent Builder for assembling safe skills from marketplace connectors, templates, allowed steps, and required guards.

Agent Builder endpoints:

- `POST /v1/agent-builder/sessions`
- `GET /v1/agent-builder/sessions/{session_id}`
- `POST /v1/agent-builder/sessions/{session_id}/select-template`
- `POST /v1/agent-builder/sessions/{session_id}/select-connector`
- `POST /v1/agent-builder/sessions/{session_id}/configure-trigger`
- `POST /v1/agent-builder/sessions/{session_id}/configure-inputs`
- `POST /v1/agent-builder/sessions/{session_id}/configure-steps`
- `POST /v1/agent-builder/sessions/{session_id}/configure-guards`
- `POST /v1/agent-builder/sessions/{session_id}/check-requirements`
- `GET /v1/agent-builder/sessions/{session_id}/preview`
- `POST /v1/agent-builder/sessions/{session_id}/save-draft`
- `GET /v1/agent-builder/sessions/{session_id}/timeline`
- `GET /v1/agent-builder/step-library`

Builder output is always:

```text
runtime_mode=dry_run_only
write_actions=false
requires_review=true
requires_compile=true
requires_approval=true
```

The builder blocks forbidden step types such as shell commands, raw Odoo execution, direct HTTP calls, browser automation, and high-risk business actions. Saving creates an `AutomationDraft`; the existing review, compile, approval, and activation flow remains mandatory.

## Connector Credential Vault & OAuth Readiness

Sprint 17 prepares secure connector authorization metadata before any real external connector execution is enabled.

Connector auth endpoints:

- `POST /v1/connectors/auth-profiles`
- `GET /v1/connectors/auth-profiles`
- `GET /v1/connectors/auth-profiles/{profile_id}`
- `POST /v1/connectors/auth-profiles/{profile_id}/test`
- `POST /v1/connectors/auth-profiles/{profile_id}/rotate`
- `POST /v1/connectors/auth-profiles/{profile_id}/revoke`
- `GET /v1/connectors/auth-profiles/{profile_id}/audit`
- `GET /v1/connectors/scopes`

The vault stores only a credential reference and fingerprint in the application database. API responses, simulated test results, and audit events expose redacted metadata only.

Sprint 17 intentionally does not add real OAuth, Gmail/Calendar/Drive/WhatsApp API calls, MCP execution, or new ERP write capability. Connection tests are simulated and report `provider_api_called=false`.

## External Connector Read-Only Pilot

Sprint 18 opens the first external connector in fixture mode: Google Calendar read-only.

External connector endpoints:

- `GET /v1/external-connectors` — list available connectors and their policies
- `GET /v1/external-connectors/google-calendar-readonly/policy` — get read-only policy
- `POST /v1/external-connectors/google-calendar-readonly/test-readiness` — policy check before read
- `POST /v1/external-connectors/google-calendar-readonly/read-calendars` — read calendars (redacted)
- `POST /v1/external-connectors/google-calendar-readonly/read-upcoming-events` — read events (redacted)
- `GET /v1/external-connectors/read-evidence/{evidence_id}` — retrieve read evidence record
- `GET /v1/external-connectors/auth-profiles/{id}/read-evidence` — list evidence for a profile
- `GET /v1/external-connectors/auth-profiles/{id}/signals` — business signals (no PII)
- `GET /v1/external-connectors/auth-profiles/{id}/audit` — audit trail (tokens redacted)

Default mode is fixture — no credentials, no real API calls. Set `USE_REAL_GOOGLE_CALENDAR=true` to enable the real read path (requires OAuth token). Redaction removes attendee emails, organizer/creator emails, hangoutLink, htmlLink, description, and conferenceData from all responses.

Sprint 18 does not create/update/delete calendar events, send emails, read Gmail bodies, ingest Drive content, add MCP execution, add ERP write capability, or enable R3/R4 writes.

## Google Calendar OAuth Authorization

Sprint 19 adds the real OAuth 2.0 consent flow for `calendar.readonly`.

OAuth endpoints:

- `POST /v1/oauth/google-calendar/authorize` — generate authorization URL + CSRF state token
- `GET /v1/oauth/google-calendar/callback?code=...&state=...` — exchange code for token (stored in vault)
- `GET /v1/oauth/google-calendar/status/{profile_id}` — authorization status (no token exposed)
- `GET /v1/oauth/google-calendar/verify-scope/{profile_id}` — confirm only `calendar.readonly` was granted
- `POST /v1/oauth/google-calendar/revoke/{profile_id}` — revoke token and update profile status

Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` env vars for real OAuth. Without them, placeholder mode is active: same flow, same audit trail, mock authorization URL. Tokens are never stored plaintext in the database or returned in any API response — only a vault reference and SHA-256 fingerprint are persisted.

Sprint 19 does not add calendar write, Gmail, Drive, WhatsApp, MCP execution, arbitrary HTTP, or ERP write capability.

## Current Demo Story

Implemented: record once in the Fake ERP demo, validate readiness, compile a reusable skill, inspect the compiled package, run it deterministically, and audit the resulting runs and steps.

Simulated: an approval gate that plans the critical `confirm_sales_order` action, and an approval decision simulation that records approve/reject evidence without executing ERP writes.

Not implemented: real Odoo UI automation, real ERP writes, a full approval workflow, browser-extension capture, MCP, or an LLM-driven builder.

## Sprint 47 Manual Dry-Run Execution Record

Sprint 47 adds the first formal manual dry-run execution record. It creates a persisted dry-run artifact only after preview and token confirmation, and it remains fully non-executing.

New endpoints:

- `POST /v1/operator-console/action-plan/manual-dry-run`
- `GET /v1/operator-console/action-plan/manual-dry-run/{run_id}`
- `GET /v1/operator-console/action-plan/manual-dry-run-audit`

Example request:

```json
{
  "version_id": "ui_skill_ver_...",
  "token_id": "tok_...",
  "actor": {
    "type": "user",
    "id": "operator_1",
    "display_name": "Operator"
  },
  "source_plan_id": "aplan_...",
  "source_step_number": 4,
  "mode": "dry_run",
  "inputs": {
    "order_reference": "SO-VALID"
  },
  "reason": "Operator requested a dry-run evidence record after preview passed."
}
```

Example response:

```json
{
  "run_id": "dryrun_...",
  "version_id": "ui_skill_ver_...",
  "status": "completed",
  "mode": "dry_run",
  "execution_performed": false,
  "simulation_performed": true,
  "erp_writes_performed": false,
  "browser_control_performed": false,
  "mcp_execution_performed": false,
  "llm_runtime_used": false,
  "scheduler_used": false,
  "active_skill_run_created": true,
  "fake_erp_execution_performed": false,
  "odoo_execution_performed": false,
  "evidence_id": "runev_...",
  "audit_recorded": true,
  "result_summary": "Manual dry-run record created. No ERP action was executed.",
  "blocking_reasons": []
}
```

Block A ends before Fake ERP execution. The dry-run record is manual and explicit; it does not trigger Fake ERP, Odoo, browser automation, MCP tools, scheduler jobs, or ERP writes.

## Sprint 48 Controlled Fake ERP Execution

Sprint 48 adds the first controlled execution path, but only inside the local Fake ERP boundary. It requires an explicit operator request, a confirmed token, and a completed manual dry-run record from Sprint 47.

New endpoints:

- `POST /v1/operator-console/action-plan/fake-erp-execution`
- `GET /v1/operator-console/action-plan/fake-erp-execution/{execution_id}`
- `GET /v1/operator-console/action-plan/fake-erp-execution-audit`

Example request:

```json
{
  "version_id": "ui_skill_ver_...",
  "dry_run_id": "dryrun_...",
  "token_id": "tok_...",
  "actor": {
    "type": "user",
    "id": "operator_1",
    "display_name": "Operator"
  },
  "execution_target": "fake_erp",
  "inputs": {
    "order_reference": "SO-VALID"
  },
  "reason": "Operator approved controlled Fake ERP execution after dry-run evidence."
}
```

Example response:

```json
{
  "execution_id": "fexec_...",
  "version_id": "ui_skill_ver_...",
  "dry_run_id": "dryrun_...",
  "status": "completed",
  "execution_target": "fake_erp",
  "execution_performed": true,
  "fake_erp_execution_performed": true,
  "odoo_execution_performed": false,
  "real_erp_execution_performed": false,
  "erp_writes_performed": false,
  "browser_control_performed": false,
  "mcp_execution_performed": false,
  "llm_runtime_used": false,
  "scheduler_used": false,
  "external_http_performed": false,
  "steps_executed": 1,
  "steps_blocked": 0,
  "evidence_pack_id": "fepack_...",
  "audit_recorded": true,
  "result_summary": "Controlled Fake ERP execution completed. No real ERP was touched.",
  "blocking_reasons": []
}
```

Manual dry-run and Fake ERP execution are different artifacts:

- Sprint 47 `manual-dry-run` persists a simulated record and executes nothing.
- Sprint 48 `fake-erp-execution` may execute only explicitly allowlisted `fake_*` operations inside controlled Fake ERP.

The boundary is still strict: no Odoo, no real ERP, no browser automation, no MCP, no scheduler, no external HTTP, and `endpoint_hint` is never executed.

## Sprint 49 Persisted Fake ERP Evidence Pack

Sprint 49 adds a persisted evidence-pack artifact built from a completed Sprint 48 Fake ERP execution. It does not re-run Fake ERP or open any new execution surface.

New endpoints:

- `POST /v1/operator-console/action-plan/fake-erp-evidence-pack`
- `GET /v1/operator-console/action-plan/fake-erp-evidence-pack/{pack_id}`
- `GET /v1/operator-console/action-plan/fake-erp-execution/{execution_id}/evidence-pack`

Example request:

```json
{
  "execution_id": "fexec_..."
}
```

Pack contents:

- result snapshot
- steps snapshot
- safety summary
- audit snapshot
- `dry_run_id` reference
- actor and inputs snapshot

The pack is generated only from a completed Fake ERP execution. It does not:

- re-run Fake ERP
- reopen the runtime
- call Odoo
- touch real ERP systems
- use browser automation
- call MCP tools
- use a scheduler
- call external HTTP
- execute `endpoint_hint`

## Sprint 50 Manual Fake ERP Regression Suite

Sprint 50 adds a manual regression layer on top of Sprint 48 and Sprint 49. A regression case stores deterministic expected outcomes, then a manual regression run explicitly reuses the controlled Fake ERP execution path and the persisted evidence-pack path to compare expected vs actual.

New endpoints:

- `POST /v1/operator-console/fake-erp-regression/cases`
- `GET /v1/operator-console/fake-erp-regression/cases/{case_id}`
- `POST /v1/operator-console/fake-erp-regression/run`
- `GET /v1/operator-console/fake-erp-regression/runs/{regression_run_id}`
- `GET /v1/operator-console/fake-erp-regression/audit`

Example case request:

```json
{
  "version_id": "ui_skill_ver_...",
  "dry_run_id": "dryrun_...",
  "name": "SO-VALID regression",
  "execution_target": "fake_erp",
  "inputs": {
    "order_reference": "SO-VALID"
  },
  "expected_outcomes": {
    "status": "completed",
    "steps_executed": 1,
    "steps_blocked": 0,
    "execution_target": "fake_erp"
  }
}
```

Example run request:

```json
{
  "case_id": "fregcase_...",
  "token_id": "tok_...",
  "actor": {
    "type": "user",
    "id": "operator_1",
    "display_name": "Operator"
  },
  "reason": "Operator requested manual Fake ERP regression run."
}
```

The regression layer remains tightly bounded:

- manual only
- no scheduler
- no autonomous loop
- no Odoo
- no real ERP
- no browser automation
- no MCP
- no LLM runtime
- no external HTTP
- no `endpoint_hint` execution

Sprint 50 compares only deterministic artifacts already produced by controlled Fake ERP execution and persisted evidence. It does not create any new execution surface beyond the existing Sprint 48 path.

## Sprint 51 Universal ERP Adapter Contract

ERPGuard core now speaks neutral ERP operation contracts. Odoo, SAP, Dynamics, Holded, NetSuite, custom REST, and other platforms are future adapters, not core assumptions.

Sprint 51 adds a product-layer contract only:

- neutral operation types such as `read_object`, `search_objects`, `inspect_schema`, `preview_write`, `create_object`, and `confirm_document`
- neutral object types such as `partner`, `product`, `sale_order`, `invoice`, and `manufacturing_order`
- safety tiers and placeholder adapter identifiers
- serializable request/result/evidence/error/safety-flags objects
- helper functions for blocked results, contract-only success results, safety defaults, and read-like vs write-like inference

The contract lives in `erpguard/product/erp_adapter_contract.py` and performs no real ERP calls.

Sprint 51 explicitly does not implement:

- adapter registry
- policy API
- Odoo/SAP/Dynamics/Holded/NetSuite adapters
- custom REST execution
- external HTTP
- real credentials
- browser automation
- MCP
- scheduler
- real ERP writes
- Fake ERP runtime changes

## Sprint 52 ERP Adapter Capability Registry

Sprint 52 builds on the universal contract from Sprint 51 and adds a neutral capability registry. ERPGuard can now reason about placeholder adapters and declared capabilities without connecting to any real ERP.

New pieces:

- placeholder adapter identities for `fake_erp`, `odoo_placeholder`, `holded_placeholder`, `sap_placeholder`, `dynamics_placeholder`, `netsuite_placeholder`, and `custom_rest_placeholder`
- declared capabilities by `adapter_id + operation_type + object_type`
- advisory-only capability lookup
- advisory-only capability check with requested-field validation against declared allowlists
- read-only endpoints for adapter listing, capability listing, and capability checks

Capability declaration is not execution:

- placeholders are not real adapters
- supported capability is not executable capability
- Sprint 52 never connects to Odoo, SAP, Dynamics, Holded, NetSuite, custom REST, or any external HTTP endpoint

Requested field checks remain contract-only in Sprint 52:

- requested field inside allowlist -> capability stays supported
- requested field outside allowlist -> `supported=false` and `blocking_reasons=["requested_field_not_supported:<field>"]`

All Sprint 52 responses remain advisory:

- `is_advisory_only=true`
- `will_execute=false`
- `can_execute=false`
- all external execution safety flags remain false

## Sprint 53 ERP Adapter Safety Policy

Sprint 53 adds the policy layer on top of the universal contract and the capability registry.

The distinction is now explicit:

- capability: the adapter declares that it can represent or support an operation
- policy: ERPGuard decides whether that operation is eligible, previewable, blocked, or still non-executable in the current phase

Block C remains contract-only:

- no real ERP connections
- no external HTTP
- no credentials used
- no browser automation
- no MCP
- no scheduler
- no real ERP writes

Policy behavior in Block C:

- `read_only` -> eligible, previewable, never executable
- `preview_only` -> eligible, previewable, requires confirmation, never executable
- `sandbox_write` -> representable for `fake_erp`, still never executable
- `controlled_write` -> blocked
- `high_risk_write` -> blocked
- `forbidden` -> blocked

Requested fields are still validated only against declared allowlists. Sprint 53 does not yet evaluate actor trust, tenant policy, execution readiness, write authorization, or any connector onboarding flow.

This keeps real ERP execution blocked while building the future bridge toward URL+credential Connector Autopilot on top of a neutral any-ERP policy model.

## Sprint 54 Connector Setup Session

Sprint 54 starts Block D, Connector Autopilot, with the first customer-facing onboarding object: a connector setup session.

The thesis-facing intent is:

```text
I want to connect this ERP using URL + credentials.
```

Sprint 54 captures only the safe shell of that intent:

- connector name
- ERP URL
- normalized ERP URL host
- environment type: `sandbox`, `staging`, `production`, or `unknown`
- submitting operator
- optional opaque `credential_ref` for a future vault phase
- status and blocking reasons
- setup audit events

Connector setup endpoints:

- `POST /v1/operator-console/connectors/setup-session`
- `GET /v1/operator-console/connectors/setup-session/{session_id}`
- `GET /v1/operator-console/connectors/setup-sessions`
- `GET /v1/operator-console/connectors/setup-session-audit`

Setup session states:

- `awaiting_credentials` when no `credential_ref` exists
- `ready_for_fingerprint` only when an opaque future `credential_ref` exists
- `blocked` when the URL is invalid, the scheme is unsafe, or raw credential fields are detected
- `draft` is reserved for shell lifecycle representation

Safety boundaries:

- no credential vault implementation
- no raw password, API key, token, secret, credential, or credentials are persisted
- no external HTTP calls
- no ERP login
- no fingerprinting
- no schema inspection
- no capability generation
- no connector activation
- no real ERP adapter
- no browser automation
- no MCP
- no scheduler
- no ERP writes

Every setup response preserves the critical safety flags:

```text
will_connect=false
external_http_performed=false
credentials_stored=false
raw_credentials_seen=false
```

If a caller sends raw credential-shaped fields defensively, the session is blocked with `raw_credentials_not_allowed_in_sprint_54`; raw values are not echoed or stored.

## Confirmed Read-Only Action Dispatcher

Sprint 45 adds the first real operator dispatch path, but only for internal read-only handlers. The server requires a confirmed token, re-checks dispatch eligibility immediately before execution, selects the handler by `action_key`, persists the dispatch result, and records execution audit evidence.

Dispatch endpoints:

- `POST /v1/operator-console/action-plan/dispatch`
- `GET /v1/operator-console/action-plan/dispatch-results/{dispatch_id}`
- `GET /v1/operator-console/action-plan/dispatch-execution-audit`
- `GET /v1/operator-console/action-plan/dispatchable-actions`

Sprint 45 dispatches only these internal advisory actions: `check_governance_gaps`, `search_skills`, `reuse_suggestions`, `inspect_lifecycle`, and `recommend_next_step`.

Sprint 45 explicitly does not execute endpoint hints, call Odoo, write ERP data, control browsers, call MCP tools, use LLM runtime replay, mutate skill or lifecycle state, activate candidates, record approval decisions, create activation requests, or chain into other actions automatically.

The flow is intentionally small and defensible: record -> readiness -> compile -> inspect -> run -> audit -> safe plan -> simulated decision.

The core product evidence lives in the runtime features and frozen JSON artifacts, while the last two stages are simulation layers that demonstrate safety boundaries.

No real Odoo calls are made in this repository yet.

The MVP stops at a controlled demo and audit trail.

The next step after this story is consolidation, not more feature growth.

This README is written to explain what exists today, what is simulated for the demo, and what remains intentionally out of scope.

## Sprint 55 Connector Credential Vault Contract

Sprint 55 seals raw credentials into a vault reference only, never returning or persisting raw secrets.

Credential vault endpoints:

- `POST /v1/operator-console/connectors/credentials/seal` — seal password/api_key/token into a `cred_` reference
- `GET /v1/operator-console/connectors/credentials/{credential_ref}/metadata` — get redacted metadata
- `POST /v1/operator-console/connectors/credentials/{credential_ref}/revoke` — revoke credential
- `GET /v1/operator-console/connectors/credentials/audit` — audit trail

Safety invariants:

- `raw_secret_returned=false`, `raw_secret_logged=false`, `llm_accessible=false`
- `external_http_performed=false`, `login_attempted=false`, `fingerprint_performed=false`
- `schema_inspection_performed=false`, `read_only_activation_performed=false`, `erp_write_performed=false`
- Only SHA-256 fingerprint + last 4 chars stored; no raw secret persisted
- Setup session transitions to `credential_mode=vault_reference_only` and `status=ready_for_fingerprint`

## Sprint 56 ERP Fingerprinting Plan

Sprint 56 creates a plan-only fingerprinting artifact from a setup session + sealed credential reference. No real discovery is performed.

Fingerprinting plan endpoints:

- `POST /v1/operator-console/connectors/setup-session/{session_id}/fingerprinting-plan` — create plan
- `GET /v1/operator-console/connectors/fingerprinting-plan/{fingerprint_plan_id}` — get plan
- `GET /v1/operator-console/connectors/fingerprinting-plans` — list plans
- `GET /v1/operator-console/connectors/fingerprinting-audit` — audit trail

Plan-only heuristics detect adapter candidates (Odoo, Holded, SAP, Dynamics, NetSuite, custom_rest, unknown) from URL host and connector name patterns. Manual hints reinforce candidates. All planned checks are `plan_only` — no network call, no login, no schema inspection, no capability generation.

Safety invariants:

- `will_connect=false`, `external_http_performed=false`, `login_attempted=false`
- `fingerprint_performed=false`, `schema_inspection_performed=false`
- `capability_generation_performed=false`, `read_only_activation_performed=false`
- `credentials_exposed=false`, `raw_secret_accessed=false`

## Sprint 57 Safe Discovery Plan & Read-Only Surface Model

Sprint 57 creates a safe discovery plan and static read-only surface model from a Sprint 56 fingerprinting plan. It is still plan/model only.

Safe discovery endpoints:

- `POST /v1/operator-console/connectors/fingerprinting-plan/{fingerprint_plan_id}/safe-discovery-plan` - create safe discovery plan
- `GET /v1/operator-console/connectors/safe-discovery-plan/{discovery_plan_id}` - get plan and surface model
- `GET /v1/operator-console/connectors/safe-discovery-plans` - list plans
- `GET /v1/operator-console/connectors/safe-discovery-audit` - audit trail

The read-only surface model contains static object candidates, field candidates, and permission-surface candidates for the selected adapter type. Adapter templates cover Odoo, Holded, SAP, Dynamics, NetSuite, custom REST, and unknown systems without contacting any ERP.

The blocked write surface model marks all write-like operations as blocked:

- `create_object`
- `update_object`
- `delete_object`
- `post_document`
- `confirm_document`
- `reconcile_payment`
- `produce_manufacturing_order`

Plan-only boundary:

- `will_connect=false`, `external_http_performed=false`, `login_attempted=false`
- `schema_inspection_performed=false`, `permission_inspection_performed=false`, `sample_data_read=false`
- `capability_generation_performed=false`, `read_only_activation_performed=false`, `erp_write_performed=false`
- `credentials_exposed=false`, `raw_secret_accessed=false`
- No network, login, schema inspection, permission inspection, ERP reads, capability generation, connector activation, browser automation, MCP, scheduler, real ERP adapter, or writes are performed.

## Sprint 58 Auto Capability Generation from Discovery

Sprint 58 generates an advisory-only capability set from a Sprint 57 safe discovery plan. It is generation-only: capabilities are internal artifacts that can be inspected or policy-checked, not executed.

Generated capability endpoints:

- `POST /v1/operator-console/connectors/safe-discovery-plan/{discovery_plan_id}/generated-capabilities` - generate capabilities
- `GET /v1/operator-console/connectors/generated-capabilities/{capability_set_id}` - get generated capability set
- `GET /v1/operator-console/connectors/generated-capability-sets` - list generated capability sets
- `GET /v1/operator-console/connectors/generated-capability-audit` - audit trail

Generated read-only capabilities are derived only from `read_only_surface.objects` and `read_only_surface.fields`:

- `read_object`
- `search_objects`
- `inspect_schema`
- `inspect_permissions`

Blocked write capabilities are derived from the Sprint 57 blocked write surface:

- `create_object`
- `update_object`
- `delete_object`
- `post_document`
- `confirm_document`
- `reconcile_payment`
- `produce_manufacturing_order`

Generation-only boundary:

- `is_advisory_only=true`, `will_execute=false`, `can_execute=false`, `supports_execution=false`
- `external_http_performed=false`, `login_attempted=false`, `schema_inspection_performed=false`, `permission_inspection_performed=false`, `sample_data_read=false`
- `capability_generation_performed=true` because Sprint 58 creates internal capability artifacts
- `read_only_activation_performed=false`, `erp_write_performed=false`, `credentials_exposed=false`, `raw_secret_accessed=false`
- No ERP connection, login, schema inspection, permission inspection, ERP reads, connector activation, real ERP implementation, browser automation, MCP, scheduler, or writes are performed.

## Sprint 59 Read-Only Connector Activation

Sprint 59 closes Block D by creating a governed internal read-only connector activation artifact from the full Connector Autopilot chain:

`setup_session -> credential_ref -> fingerprinting_plan -> safe_discovery_plan -> generated_capability_set -> human approval -> read_only_connector_activation`

Activation lifecycle:

- Create an activation request from a generated capability set.
- Keep `status=requested` and `requires_human_approval=true`.
- Require an explicit approval actor.
- Create an activation with `status=active_read_only` only after approval.

`active_read_only` does not mean ERPGuard opened a connection to the ERP. It means the internal connector artifact is approved and ready for future read-only adapter work.

Read-only activation endpoints:

- `POST /v1/operator-console/connectors/generated-capabilities/{capability_set_id}/read-only-activation-request`
- `POST /v1/operator-console/connectors/read-only-activation/{activation_request_id}/approve`
- `GET /v1/operator-console/connectors/read-only-activation/{activation_id}`
- `GET /v1/operator-console/connectors/read-only-activations`
- `GET /v1/operator-console/connectors/read-only-activation-audit`

Sprint 59 safety boundary:

- `external_http_performed=false`, `login_attempted=false`
- `real_erp_connection_established=false`, `real_erp_read_enabled=false`, `real_erp_write_enabled=false`
- `browser_control_performed=false`, `mcp_execution_performed=false`, `scheduler_used=false`
- `credentials_exposed=false`, `raw_secret_accessed=false`
- No Block E, real Odoo, real ERP adapter, network call, login, schema/permission inspection, ERP read, browser automation, MCP, scheduler, write, or raw secret access is introduced.

Block D is now complete as a safe internal artifact pipeline. The next phase should not treat these artifacts as live ERP connectivity until a separate read-only adapter sprint explicitly implements and verifies that boundary.

## Next Phase Candidate

The next possible phase is `v0.8`, framed as a real Odoo read-only adapter plus an Odoo preflight demo.

That phase should stay narrow: connect to Odoo, read a real sales order, map it to the canonical model, run Formula Guard, and show an audited result.

It should not confirm orders, write records, or expand into a broader automation platform.

If pursued, it should be treated as a separate phase with its own evidence freeze and acceptance criteria.

## Sprint 1 - Real Odoo Connection & Diagnosis

This sprint adds the first real Odoo-facing capability: a read-only connection test and diagnosis flow.

The API-first entry points are:

- `POST /v1/odoo/connections`
- `POST /v1/odoo/connections/{connection_id}/test`
- `POST /v1/odoo/connections/{connection_id}/diagnose`
- `GET /v1/odoo/connections/{connection_id}/sales-orders/{order_reference}/raw-summary`

The flow validates credentials, reads the Odoo version and uid, inspects modules/models/fields, detects custom fields, reads limited samples, and returns a read-only diagnosis.

Read-only mode is enforced in code: no Odoo write methods are allowed in this sprint.

Secrets are redacted in API responses.

This sprint is the first practical bridge from the controlled Fake ERP MVP toward the real Odoo preflight phase.

## Local Setup

Create and activate a virtual environment, then install the project in editable mode:

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
```

Run tests:

```bash
python -m pytest
```

Start the API:

```bash
uvicorn apps.api.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000/health
```

Create a connection:

```bash
curl -X POST http://127.0.0.1:8000/v1/connections ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"Odoo Test\",\"erp_type\":\"odoo\",\"config\":{\"url\":\"https://example.odoo.com\",\"database\":\"example-db\",\"username\":\"user@example.com\",\"api_key\":\"secret\"}}"
```

Responses redact `api_key`. Do not commit real Odoo credentials to Git.

Run preflight using a stored connection:

```bash
curl -X POST http://127.0.0.1:8000/v1/preflight ^
  -H "Content-Type: application/json" ^
  -d "{\"connection_id\":\"conn_...\",\"actor\":{\"type\":\"user\",\"native_user_id\":\"6\",\"display_name\":\"Test User\"},\"action\":{\"canonical_action\":\"confirm_sales_order\",\"canonical_object\":\"SalesOrder\",\"native\":{\"model\":\"sale.order\",\"method\":\"action_confirm\",\"record_id\":\"so_formula_mismatch\"}},\"options\":{\"simulate\":true,\"allow_write\":false},\"policy_id\":\"formula_guard\"}"
```

The older `erp_type: "fake"` preflight request is still supported for local development, but `connection_id` is the recommended flow.

Retrieve preflight evidence:

```bash
curl http://127.0.0.1:8000/v1/preflight/pf_...
```

Retrieve the audit trail:

```bash
curl http://127.0.0.1:8000/v1/audit/pf_...
```

Create a skill in the Skill Registry:

```bash
curl -X POST http://127.0.0.1:8000/v1/skills ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"Safe Formula Guard UI Preflight\",\"description\":\"Validates a sales order formula through the Fake ERP flow.\",\"runtime_type\":\"deterministic_browser\",\"llm_required_for_repeated_runs\":false,\"skill_package\":{\"skill_id\":\"safe_formula_guard_ui_preflight\",\"inputs\":{\"order_reference\":\"string\"},\"guards\":[\"formula_guard\"],\"workflow\":[{\"id\":\"open_orders\",\"type\":\"navigate\",\"target\":\"/fake-erp/sales/orders\"},{\"id\":\"search_order\",\"type\":\"fill\",\"selector\":\"[data-testid='order-search']\"},{\"id\":\"open_order\",\"type\":\"click\",\"selector_template\":\"[data-testid='open-order-{{order_reference}}']\"},{\"id\":\"open_formula\",\"type\":\"click\",\"selector\":\"[data-testid='formula-tab']\"},{\"id\":\"review_formula\",\"type\":\"guard\",\"guard\":\"formula_guard\"}]}}"
```

List skills:

```bash
curl http://127.0.0.1:8000/v1/skills
```

Get a skill by id:

```bash
curl http://127.0.0.1:8000/v1/skills/skill_...
```

Run a skill:

```bash
curl -X POST http://127.0.0.1:8000/v1/skills/skill_.../run ^
  -H "Content-Type: application/json" ^
  -d "{\"inputs\":{\"order_reference\":\"SO-FORMULA-MISMATCH\"}}"
```

The repeated run path is deterministic and does not use the LLM.

Run the browser UI runtime:

```bash
curl -X POST http://127.0.0.1:8000/v1/skills/skill_.../run-ui ^
  -H "Content-Type: application/json" ^
  -d "{\"inputs\":{\"order_reference\":\"SO-FORMULA-MISMATCH\"},\"runtime\":{\"base_url\":\"http://127.0.0.1:8000\"}}"
```

Create a recording session:

```bash
curl -X POST http://127.0.0.1:8000/v1/recordings ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"Review order formula from Fake ERP\",\"description\":\"User demonstrates how to open a sales order and review formula data.\",\"erp_type\":\"fake\",\"target_base_url\":\"http://127.0.0.1:8000\",\"actor\":{\"type\":\"user\",\"id\":\"user_1\",\"display_name\":\"Test User\"}}"
```

Add a recording event:

```bash
curl -X POST http://127.0.0.1:8000/v1/recordings/recording_.../events ^
  -H "Content-Type: application/json" ^
  -d "{\"event_type\":\"click\",\"url\":\"http://127.0.0.1:8000/fake-erp/sales/orders\",\"page_title\":\"Fake ERP Sales Orders\",\"element_role\":\"link\",\"element_text\":\"Open SO-FORMULA-MISMATCH\",\"selector\":\"[data-testid='open-order-SO-FORMULA-MISMATCH']\",\"before_text_snapshot\":\"Sales Orders...\",\"after_text_snapshot\":\"Order SO-FORMULA-MISMATCH...\"}"
```

Compile a recording into a skill:

```bash
curl -X POST http://127.0.0.1:8000/v1/recordings/recording_.../compile-skill ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"Recorded Fake ERP Formula Review\",\"description\":\"Compiled from a demonstrated Fake ERP formula review flow.\",\"runtime_type\":\"deterministic_browser\"}"
```

Run the demo recorder:

```bash
curl -X POST http://127.0.0.1:8000/v1/recordings/demo-fake-erp-formula-flow ^
  -H "Content-Type: application/json" ^
  -d "{\"base_url\":\"http://127.0.0.1:8000\",\"order_reference\":\"SO-FORMULA-MISMATCH\",\"actor\":{\"type\":\"user\",\"id\":\"user_1\",\"display_name\":\"Test User\"}}"
```

Run the full MVP demo orchestrator:

```bash
curl -X POST http://127.0.0.1:8000/v1/demo/full-record-to-skill-flow ^
  -H "Content-Type: application/json" ^
  -d "{\"base_url\":\"http://127.0.0.1:8000\",\"record_order_reference\":\"SO-FORMULA-MISMATCH\",\"valid_order_reference\":\"SO-VALID\",\"invalid_order_reference\":\"SO-FORMULA-MISMATCH\",\"actor\":{\"type\":\"user\",\"id\":\"user_1\",\"display_name\":\"Test User\"}}"
```

## Full MVP Demo Evidence

The known-good end-to-end response is stored at [docs/demo/full_record_to_skill_success_response.json](docs/demo/full_record_to_skill_success_response.json).

## Demo Dashboard

Start the API:

```bash
uvicorn apps.api.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000/demo
```

If you want the live browser path to run, install Chromium first:

```bash
python -m playwright install chromium
```

## Human Recording v0.2

Start the API and open the demo dashboard:

```bash
uvicorn apps.api.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000/demo
```

Use the Human Recording v0.2 controls to:

- start a controlled recording session
- open the Fake ERP sales orders page
- perform the formula review flow manually
- finish the recording
- compile it into a skill
- run the compiled skill for `SO-VALID` and `SO-FORMULA-MISMATCH`

The controlled browser path only works when Chromium is installed:

```bash
python -m playwright install chromium
```

## Human Recording v0.2.1 Hardening

The `/demo` dashboard now shows a human recording preview after finish:

- `recording_id`
- recording status
- event count
- ordered event summaries
- captured selectors
- compiler readiness: `ready` or `not_ready`

The recording-to-skill compiler also validates the minimum controlled Fake ERP sequence before creating a skill, so incomplete recordings return clear diagnostics such as `missing_order_search_event`, `missing_formula_tab_event`, or `missing_review_formula_event`.

## Human Recording v0.2.1 Evidence

The frozen v0.2.1 evidence response is stored at [docs/demo/human_recording_v0_2_1_success_response.json](docs/demo/human_recording_v0_2_1_success_response.json).

It was generated from a FastAPI `TestClient` flow that creates a controlled recording, posts the five required Fake ERP events, compiles the recording, and runs the compiled skill for `SO-VALID` and `SO-FORMULA-MISMATCH`.

Verify the current evidence baseline with:

```bash
python -m pytest
```

Expected result for the v0.2.1 evidence freeze environment:

```text
141 passed, 9 skipped, 2 warnings
```

## Teach Mode v0.3

Teach Mode v0.3 keeps the same controlled Fake ERP formula review flow, but renders it as a teach-the-process checklist in `/demo`.

The dashboard now shows the expected teaching steps from start recording through allow/block proof, and uses the readiness API to mark recorded evidence as `observed`, `missing`, or `ready`.

Inspect readiness for a recording:

```bash
curl http://127.0.0.1:8000/v1/recordings/recording_.../readiness
```

The response reports:

- `readiness`: `ready` or `not_ready`
- `event_count`
- step status for `sales_orders_navigation`, `order_search`, `open_order`, `formula_tab`, and `review_formula`
- compiler-compatible diagnostics for missing steps

This is still a controlled Fake ERP demo path. It is not real Odoo UI automation, a browser extension, a free recorder, or an LLM-based flow builder.

## Teach Mode v0.3 Evidence

The frozen Teach Mode v0.3 evidence response is stored at [docs/demo/teach_mode_v0_3_success_response.json](docs/demo/teach_mode_v0_3_success_response.json).

It was generated from a FastAPI `TestClient` flow that creates a controlled recording, adds the five required events, checks readiness, finishes the recording, compiles the skill, and runs `SO-VALID -> allow` plus `SO-FORMULA-MISMATCH -> block`.

Verify the current evidence baseline with:

```bash
python -m pytest
```

Expected result for the Teach Mode v0.3 evidence freeze environment:

```text
148 passed, 9 skipped, 2 warnings
```

## Skill Inspector v0.4

After compiling a skill, inspect the latest version before trusting repeated runs:

```bash
curl http://127.0.0.1:8000/v1/skills/skill_.../inspect
```

The inspector shows the skill name, version, runtime type, inputs, guards, workflow steps, the originating recording id, and a safety summary. The `/demo` dashboard renders the same Skill Inspector v0.4 section automatically after compilation and again after the proof run.

## Skill Inspector v0.4 Evidence

The frozen Skill Inspector v0.4 evidence response is stored at [docs/demo/skill_inspector_v0_4_success_response.json](docs/demo/skill_inspector_v0_4_success_response.json).

It was generated from a FastAPI `TestClient` flow that creates a controlled recording, posts the five required Fake ERP events, checks readiness, finishes the recording, compiles the skill, inspects the compiled skill, and runs `SO-VALID -> allow` plus `SO-FORMULA-MISMATCH -> block`.

Verify the current evidence baseline with:

```bash
python -m pytest
```

Expected result for the Skill Inspector v0.4 evidence freeze environment:

```text
151 passed, 9 skipped
```

The evidence artifact also includes negative controlled error responses for a missing skill and a skill with no latest version.

## Run History / Audit Timeline v0.5

After a compiled skill has been run, inspect the execution history and audit timeline:

```bash
curl http://127.0.0.1:8000/v1/skills/skill_.../runs
curl http://127.0.0.1:8000/v1/skills/skill_.../runs/skill_run_.../timeline
```

The run list shows each execution with its decision, timestamps, input, summary output, and token savings. The timeline shows the ordered `load_skill`, `load_order`, `formula_guard`, and `produce_result` steps so you can audit what happened in a replay.

## Run History / Audit Timeline v0.5 Evidence

The v0.5 evidence freeze captures the live FastAPI `TestClient` proof for the run history and audit timeline layer.

Artifact:

- [docs/demo/run_history_audit_timeline_v0_5_success_response.json](docs/demo/run_history_audit_timeline_v0_5_success_response.json)

It records:

- recording readiness in the ready state;
- skill compilation and inspection;
- a valid run that returns `allow`;
- an invalid run that returns `block`;
- `GET /v1/skills/{skill_id}/runs` returning both runs;
- `GET /v1/skills/{skill_id}/runs/{skill_run_id}/timeline` returning the ordered guard timeline;
- controlled `skill_not_found` and `skill_run_not_found` error responses.

Verification command:

```bash
python -m pytest
```

Observed result:

```text
155 passed, 9 skipped
```

## Approval Gate / Safe Action Plan v0.6

The approval gate adds a dry-run planning endpoint for the critical `confirm_sales_order` action:

```http
POST /v1/skills/{skill_id}/plan-action
```

Request example:

```json
{
  "inputs": {
    "order_reference": "SO-VALID"
  },
  "requested_action": "confirm_sales_order"
}
```

The endpoint does not execute `confirm_sales_order`, does not write to ERP, and does not create a full approval system yet. It only returns a safe plan, the Formula Guard preview, the R3 approval requirement, and proof that execution stopped before any real write.

The `/demo` page includes an Approval Gate / Safe Action Plan v0.6 panel after compile and inspect, so the operator can preview the critical action before trusting it.

## Approval Gate / Safe Action Plan v0.6 Evidence

The v0.6 evidence freeze captures the live FastAPI `TestClient` proof for the approval gate dry-run layer.

Artifact:

- [docs/demo/approval_gate_safe_action_plan_v0_6_success_response.json](docs/demo/approval_gate_safe_action_plan_v0_6_success_response.json)

It records:

- dry-run approval planning for `confirm_sales_order`;
- `approval_required = true` and `risk_level = R3`;
- Formula Guard preview for `SO-VALID` returning `allow`;
- Formula Guard preview for `SO-FORMULA-MISMATCH` returning `block`;
- no `SkillRun` rows created by the planning endpoint;
- controlled `unsupported_action` and `skill_not_found` errors.

Verification command:

```bash
python -m pytest
```

Observed result:

```text
159 passed, 9 skipped
```

## Approval Decision Simulation v0.7

The approval decision simulation endpoint lets you simulate a human approve/reject choice for the critical `confirm_sales_order` path without executing a real ERP write:

```http
POST /v1/skills/{skill_id}/simulate-approval-decision
```

Request example:

```json
{
  "inputs": {
    "order_reference": "SO-VALID"
  },
  "requested_action": "confirm_sales_order",
  "decision": "approve",
  "approver": {
    "type": "user",
    "id": "demo_approver",
    "display_name": "Demo Approver"
  },
  "reason": "Formula preview is clean."
}
```

The endpoint reuses the same critical-action identity, risk level, and Formula Guard preview as v0.6, but it still does not execute `confirm_sales_order`, does not create a real approval workflow, and does not write to ERP.

The `/demo` page includes an Approval Decision Simulation v0.7 panel with simulate-approve and simulate-reject buttons after the safe plan section.

Verification command:

```bash
python -m pytest
```

Observed result:

```text
162 passed, 9 skipped
```

## Optional Odoo Smoke Read

The smoke script is manual only and is not part of the test suite. Set real credentials in your shell, then run:

```bash
set ODOO_URL=https://example.odoo.com
set ODOO_DB=example-db
set ODOO_USERNAME=user@example.com
set ODOO_API_KEY=your-api-key
python scripts/odoo_smoke_read.py
```

It authenticates, prints the Odoo version, and reads one `sale.order` summary without printing secrets.

## Current Scope

Implemented now:

- FastAPI app startup
- `GET /health`
- connection API with redacted secrets
- configuration module
- SQLAlchemy database base/session setup
- initial database models
- fake adapter demo path
- fake ERP web demo surface
- skill registry MVP
- deterministic Skill Run endpoint
- Playwright browser runtime for Fake ERP
- Recording Session API
- Browser Recorder MVP for Fake ERP
- Demo orchestrator endpoint for the current full MVP loop
- Controlled Human Recording v0.2 for the Fake ERP formula review flow
- Controlled Human Recording v0.2.1 hardening with compiler diagnostics and `/demo` preview/readiness
- Teach Mode v0.3 readiness endpoint and `/demo` checklist for the controlled Fake ERP teaching flow
- Skill Inspector v0.4 read-only inspection for compiled Fake ERP skills
- Skill Inspector v0.4 evidence freeze and JSON artifact
- read-only Odoo adapter skeleton
- Formula Guard policy evaluation for `confirm_sales_order`
- preflight persistence and audit retrieval
- minimal centralized risk semantics for canonical action defaults
- pytest foundation

Not implemented yet:

- UI
- LLM features
- ERP write/execution actions
- approval submission flow
- stock/manufacturing simulation
