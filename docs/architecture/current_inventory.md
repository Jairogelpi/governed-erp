# ERPGuard Evolution current inventory

**Inventory date:** 2026-07-27  
**Baseline commit:** `e483f5c5f272139c65a02ebc32ab11f5e323b6a4` (`feat: add visual table form extraction`)  
**Reality label:** `real` for this inventory artifact; it records repository facts, not product claims.

## Purpose

This document freezes the repository shape before the ERPGuard Evolution migration. Counts are measured from the baseline checkout and are intentionally approximate indicators of structural concentration, not architectural quality metrics.

## Measured shape

| Area | Baseline observation | Interpretation |
| --- | ---: | --- |
| API route modules | 69 Python modules under `apps/api/routes` | Public/internal/legacy boundaries are not yet consolidated. |
| SQLAlchemy model classes | 139 classes in `erpguard/db/models.py` | Persistence models remain concentrated in one monolithic module. |
| Repository functions | 369 top-level functions in `erpguard/db/repositories.py` | Persistence access remains concentrated in one monolithic module. |
| Product modules | 269 Python modules under `erpguard/product` | Product services have grown incrementally and overlap in lifecycle concepts. |
| Persistence | SQLAlchemy with SQLite-compatible defaults | Formal migration tooling is not yet the baseline architecture. |
| Web experience | Existing `/demo` dashboard with inline HTML/JavaScript | It is an engineering/operator demo, not the Phase 21 product web journey. |
| Connector surface | Fake, read-only Odoo foundations, credential/setup and capability contracts | Odoo write vertical is not complete. |
| Baseline regression suite | 2705 passed, 2 skipped, 2 warnings | `python -m pytest` at the pinned baseline; browser-dependent skips are known and non-failing. |

## Phase 0 verification after freeze artifacts

`python -m pytest` completed with **2707 passed, 2 skipped, 2 warnings** in 224.40 seconds. The increase from 2705 to 2707 is the two Phase 0 artifact contract tests; no existing runtime tests changed.

## Existing capabilities to preserve

- FastAPI API and health surface.
- SQLAlchemy persistence and existing repository compatibility.
- Canonical ERP objects, risk engine, policy engine, preflight and Formula Guard.
- Skill registry/versioning, recording sessions, compiler and deterministic Fake ERP runtime.
- Approval, action planning, audit/evidence and controlled execution boundaries.
- Connector setup, credential-reference concepts, capability registry and Odoo read-only foundations.
- Release/install scripts, safety documentation and the existing regression suite.

## Structural liabilities frozen for migration

- The `/demo` dashboard is monolithic and should not receive new product areas except compatibility links or redirects.
- API route ownership is distributed across approximately 69 modules.
- Models and repositories are concentrated in two large modules.
- Multiple generations of Odoo connection/read-only paths coexist.
- SQLite remains the practical default and formal migrations are not yet present.
- Identity and tenant enforcement are incomplete relative to the target architecture.
- Several surfaces are fixture, simulated, advisory or shell-only and must not be presented as live ERP execution.
- Historical sprint documentation is mixed with product entry points.

## Boundary rules for the next phase

Phase 0 introduces no runtime replacement and no new product surface. Phase 1 may address truthfulness/version alignment only. No process mining, replay, candidate branching, connector SDK v2, migrations, identity, or ERP write implementation is included in this freeze.
