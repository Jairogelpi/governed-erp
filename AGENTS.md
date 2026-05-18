# ERPGuard Agent Notes

## Working Rule

- Keep this file updated whenever an agent makes a meaningful repository change.
- Record what changed, why it changed, and verification results.
- Do not store secrets, credentials, or private Odoo data here.

## Project State Before This Session

- Product spec: ERPGuard, a semantic safety layer for ERP operations, starting with Odoo preflight.
- Current implementation: Phase 1 backend foundation with FastAPI, connections API, fake adapter, read-only Odoo adapter skeleton, canonical SalesOrder models, Formula Guard, preflight persistence, and audit retrieval.
- Main working demo: create a fake connection, run Formula Guard preflight, retrieve preflight details, retrieve audit trail.
- Major missing areas from parent spec: simulation, centralized risk engine, approval, controlled execution, UI, Import Guard, Access Rule Guard, Automated Action Guard, full Odoo permission inspection, and complete audit evidence.

## Session Log

### 2026-05-18

- Analyzed `spec_unireacomp_agentflow_compiler.md` and the full repository.
- Identified contract drift between the parent API spec and `apps/api/schemas/preflight.py`.
- Identified that `confirm_sales_order` risk semantics were not enforced centrally.
- Identified that `formula_guard.yaml` applied to `validate_formula` instead of the `confirm_sales_order` preflight path described by the spec.
- Attempted `python -m pip install -e ".[dev]"`; it failed because `setuptools` discovered multiple top-level packages (`apps`, `erpguard`, `policies`) without explicit package discovery configuration.
- Updated `pyproject.toml` with explicit setuptools package discovery for `apps*` and `erpguard*` so editable installs do not accidentally treat `policies/` as a Python package.
- Re-ran `python -m pip install -e ".[dev]"`; it completed successfully.
- Ran baseline tests with `ERPGUARD_DATABASE_URL=sqlite:///C:/Users/EQUIPO/AppData/Local/Temp/opencode/erpguard_next_step.db`; result: `92 passed`.
- Added a minimal centralized risk engine in `erpguard/core/risk_engine.py` for default action risk, canonical object lookup, risk ordering, and approval-required decisions for R3+ actions.
- Updated `policies/odoo/formula_guard.yaml` so Formula Guard applies to `confirm_sales_order`, while `validate_formula` remains a read-only canonical action in code.
- Expanded preflight request/response schemas toward the parent contract: `canonical_object`, `native.record_id`, `options`, `blocking_issues`, `predicted_impact`, and `approval_required`.
- Updated preflight, policy, persistence, and audit tests for the `confirm_sales_order` path and added direct tests for the new risk engine.
- Updated `README.md` to show the current `confirm_sales_order` preflight request shape and current implemented scope.
- Ran full tests with `ERPGUARD_DATABASE_URL=sqlite:///C:/Users/EQUIPO/AppData/Local/Temp/opencode/erpguard_next_step.db`; result: `99 passed`. Re-ran after cleanup with the same result.
- Rewrote `docs/specs/14_erp_agent_os.md` as the strategic target-product spec for ERP Agent OS: five differentiation pillars, user journey, architecture, full component map, skill package format, lifecycle, token economics, MCP strategy, guard strategy, universal ERP strategy, relationship to current ERPGuard code, MVP path, and non-goals. No runtime code changes were made for this update.
- Added `docs/specs/15_universal_erp_connection_and_ui_automation.md` defining the layered universal ERP connector strategy: native API, MCP, CSV/import-export, browser DOM automation, desktop/vision automation, and human-assisted fallback. The spec covers connector routing, decision tree, UI recording, UI skill compilation, screen-state verification, repair agent, token economics, safety rules, and a future fake ERP browser automation MVP. No runtime code changes were made for this update.
- Added `docs/specs/15_record_to_skill_engine.md` defining the Record-to-Skill Engine strategy: record once inside any ERP UI, capture evidence and intent, generalize variables, compile safe reusable UI skills, protect critical actions with ERPGuard, and replay deterministically with minimal or zero LLM tokens. No runtime code changes were made for this update.
- Added `docs/specs/16_automation_opportunity_scanner.md` defining the Automation Opportunity Scanner + ROI Engine strategy: analyze business data after ERP connection, detect automation opportunities, estimate ROI, prioritize recommendations, and launch safe skill creation from high-value items. No runtime code changes were made for this update.
- Added `docs/specs/00_current_direction.md` to freeze the product direction around ERP Agent OS, Record-to-Skill, ERPGuard, and universal API-or-UI automation. No runtime code changes were made for this update.
- Added `docs/specs/17_mvp_record_to_skill_fake_erp.md` to define the first buildable MVP: Fake ERP Web, recording, deterministic skill runtime, Formula Guard, Skill Registry, and audit evidence. No runtime code changes were made for this update.
- Implemented the Skill Registry MVP: added `Skill`, `SkillVersion`, `SkillRun`, and `SkillRunStep` database models; repository helpers for create/list/get/version/run persistence; `POST /v1/skills`, `GET /v1/skills`, and `GET /v1/skills/{skill_id}` endpoints; and README examples. Verified with `pytest` (`110 passed`).
- Implemented the deterministic Skill Run endpoint: `POST /v1/skills/{skill_id}/run`, optional `GET /v1/skills/{skill_id}/runs/{skill_run_id}`, persisted run/step records, Formula Guard execution through the existing policy engine, hardcoded MVP token economics, and README/test coverage. Verified with focused tests and `pytest`.
- Implemented the Playwright browser runtime MVP for Fake ERP Web: added `erpguard/runtime/browser_runtime.py`, `POST /v1/skills/{skill_id}/run-ui`, browser runtime and UI endpoint tests, and README examples. Verified with `pytest` (`117 passed, 6 skipped`) because Playwright browser binaries were unavailable in this environment, so the browser tests skipped cleanly.
- Implemented the Recording Session MVP: added `RecordingSession` and `RecordingEvent` database models, repository helpers, `POST /v1/recordings`, `GET /v1/recordings`, `GET /v1/recordings/{recording_id}`, `POST /v1/recordings/{recording_id}/events`, `POST /v1/recordings/{recording_id}/finish`, repository/API tests, and README examples. No compiler, LLM, MCP, or browser-extension code was added.
- Implemented the Recording-to-Skill Compiler MVP: added `erpguard/compiler/recording_to_skill.py`, `POST /v1/recordings/{recording_id}/compile-skill`, compile API and compiler tests, and README examples. The compiler only supports the Fake ERP formula review flow, generalizes the detected order reference into `{{order_reference}}`, and creates a reusable skill package with `llm_required_for_repeated_runs=false`.
