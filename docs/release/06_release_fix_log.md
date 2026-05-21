# Release Fix Log

## Sprint 13 Fixes

### Clean VPS Validation Report

```text
problem: no dedicated clean-install validation report existed for v0.12.0-rc1.
root cause: Sprint 12 packaged the release candidate, but the validation artifact was intentionally left for Sprint 13.
file changed: docs/release/05_clean_install_vps_validation.md
fix applied: added a clean machine/VPS validation report with commands, endpoint results, demo UI result, smoke test result, safety checks, and final status values.
test/validation command: python -m pytest tests/test_release_docs_contract.py -q
```

### Release Fix Log

```text
problem: Sprint 13 fixes needed a durable audit trail.
root cause: release hardening changes span docs, scripts, and environment defaults.
file changed: docs/release/06_release_fix_log.md
fix applied: added this structured log using problem/root cause/file changed/fix applied/test validation command entries.
test/validation command: python -m pytest tests/test_release_docs_contract.py -q
```

### Environment Example Defaults

```text
problem: .env.example used a generic local SQLite file name and did not list release safety flags.
root cause: the previous example predated the release candidate packaging flow.
file changed: .env.example
fix applied: documented the release candidate SQLite path and kept all real-write flags false by default.
test/validation command: python -m pytest tests/test_release_docs_contract.py::test_env_example_documents_safe_defaults_without_secrets -q
```

### Release Startup Scripts

```text
problem: clean operators had to assemble database initialization and uvicorn commands manually.
root cause: Sprint 12 documented API startup but did not provide one-command release helper scripts.
file changed: scripts/start_release_candidate.sh
file changed: scripts/start_release_candidate.ps1
fix applied: added Linux/macOS and PowerShell startup helpers that initialize the DB, enforce safe false defaults, and run uvicorn apps.api.main:app.
test/validation command: python -m pytest tests/test_release_clean_install_contract.py::test_start_scripts_reference_release_api_module_and_health_endpoint -q
```

### Release Install Checker

```text
problem: there was no quick command to check release files and endpoint availability after startup.
root cause: validation was spread across docs and curl commands.
file changed: scripts/check_release_install.py
fix applied: added a stdlib-only checker for release files and optional HTTP checks against the release endpoints plus /demo.
test/validation command: python -m pytest tests/test_release_clean_install_contract.py::test_check_release_install_script_has_help_and_imports_cleanly -q
```

### Install Guide Hardening

```text
problem: the install guide did not yet describe the clean VPS flow, .env.example, helper scripts, or all release endpoints.
root cause: Sprint 12 install docs were intentionally compact for RC packaging.
file changed: docs/release/01_install_and_run.md
fix applied: expanded the guide with clean venv setup, pip install -e ".[dev]", DB init, startup scripts, release endpoint checks, /demo, and the checker command.
test/validation command: python -m pytest tests/test_release_docs_contract.py::test_install_docs_reference_clean_vps_flow_and_release_scripts -q
```

### Repository-Side Release Validation

```text
problem: clean-install hardening needed concrete validation before handoff to a Linux VPS.
root cause: Sprint 13 adds release scripts/docs, so the repo needed a local proof run for install, tests, API startup, endpoints, /demo, and the helper checker.
file changed: docs/release/05_clean_install_vps_validation.md
fix applied: recorded the repository-side validation run, including Python version, test result, uvicorn startup command, endpoint results, /demo result, operator smoke result, and checker result.
test/validation command: python -m pip install -e ".[dev]"; python -m pytest; uvicorn apps.api.main:app --host 0.0.0.0 --port 8000; python scripts/check_release_install.py --base-url http://127.0.0.1:8000
```

## Safety Notes

```text
problem: release validation must not expand product surface.
root cause: Sprint 13 is hardening, not feature delivery.
file changed: no capability file changed for new ERP behavior.
fix applied: kept ALLOW_GENERIC_REAL_ODOO_WRITES=false and ALLOW_R3_R4_REAL_WRITES=false; added contract tests for locked safety boundaries.
test/validation command: python -m pytest tests/test_release_clean_install_contract.py::test_release_safety_boundaries_remain_locked_for_clean_install_contract -q
```
