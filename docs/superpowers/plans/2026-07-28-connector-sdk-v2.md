# Connector SDK v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a framework-neutral Connector SDK v2 with entry-point discovery, a safe FakeConnector, contract tests, and a read-only legacy adapter shim.

**Architecture:** Keep SDK contracts under `erpguard/connectors/sdk` and keep concrete plugins under `erpguard/connectors/<id>`. The registry loads only the `erpguard.connectors` entry-point group; the FakeConnector implements discovery, metadata, read-only test behavior, and blocked execution without network or ERP access. The legacy shim adapts existing read-only adapter operations but explicitly blocks write-like operations.

**Tech Stack:** Python 3.11+, Pydantic v2, typing Protocols, `importlib.metadata` entry points, pytest, existing ERP adapter contract models.

---

### Task 1: Define SDK contracts

**Files:**
- Create: `erpguard/connectors/sdk/models.py`
- Create: `erpguard/connectors/sdk/plugin.py`
- Create: `erpguard/connectors/sdk/__init__.py`

- [ ] Add validated metadata, feature flags, auth schema, connector context, capability definition, connection result, fingerprint, read result, native plan/result, permit, verification, and normalized error models.
- [ ] Define the `ConnectorPlugin` Protocol with the Phase 5 methods, keeping execution present only as an explicit permit-gated contract.
- [ ] Add safety defaults that mark FakeConnector execution and external access as unavailable.
- [ ] Add focused model validation tests before implementation.

### Task 2: Implement registry and entry-point discovery

**Files:**
- Create: `erpguard/connectors/sdk/registry.py`
- Modify: `pyproject.toml`
- Test: `tests/test_connector_sdk_registry.py`

- [ ] Register the `erpguard.connectors` entry-point group for `fake`.
- [ ] Implement deterministic discovery, duplicate-ID rejection, metadata validation, and lookup by connector ID using `importlib.metadata.entry_points`.
- [ ] Ensure discovery errors are normalized and do not import Odoo modules.
- [ ] Test discovery from the installed entry point, lookup, duplicate handling, and unknown connector rejection.

### Task 3: Add FakeConnector and ConnectorTemplate

**Files:**
- Create: `erpguard/connectors/fake/__init__.py`
- Create: `erpguard/connectors/fake/plugin.py`
- Create: `erpguard/connectors/sdk/template.py`
- Test: `tests/contract/connectors/test_fake_connector.py`

- [ ] Implement FakeConnector with stable metadata, auth schema, read-only connection test, deterministic fingerprint, schema/read responses, and no external calls.
- [ ] Return a blocked/unsupported result for execution and reject missing permits; do not implement ERP writes.
- [ ] Provide a template/base helper that future independent connector packages can follow without Odoo imports.
- [ ] Add contract tests for metadata, no-secret serialization, stable fingerprint, plan/execute separation, unknown capability blocking, and safety flags.

### Task 4: Add legacy read-only adapter shim

**Files:**
- Create: `erpguard/connectors/sdk/legacy_adapter_shim.py`
- Test: `tests/test_connector_sdk_legacy_shim.py`

- [ ] Adapt the existing legacy adapter contract into SDK-shaped read-only results.
- [ ] Preserve read-like operation support and return controlled blocked results for generic/write-like operations.
- [ ] Mark the shim deprecated in its module documentation and add tests proving no write delegation and no raw secret exposure.

### Task 5: Document and verify the phase boundary

**Files:**
- Create: `docs/architecture/connector_sdk_v2.md`
- Modify: `AGENTS.md`

- [ ] Document entry-point discovery, contract surface, FakeConnector reality labels, and legacy shim deprecation.
- [ ] Record focused tests, full regression, Ruff/mypy/lock checks, and exact Phase 6 as the next allowed phase.
- [ ] Run focused contract tests, changed-file static checks, `uv lock --check`, `git diff --check`, and the full suite.
- [ ] Commit only the Phase 5 files with message `feat: add connector sdk v2 contracts`.

