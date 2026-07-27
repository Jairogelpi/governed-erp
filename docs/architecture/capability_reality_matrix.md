# ERPGuard Evolution capability reality matrix

**Baseline:** `e483f5c5f272139c65a02ebc32ab11f5e323b6a4`  
**Inventory date:** 2026-07-27

The labels below are evidence labels, not marketing claims:

- `real`: implemented and exercised against the repository’s current runtime or controlled local persistence.
- `staging_only`: allowed only in an explicitly controlled staging path.
- `fixture`: operates on fixed or synthetic data.
- `simulated`: models a future behavior without performing it.
- `advisory`: produces review information but does not authorize an effect.
- `planned`: specified but not implemented.
- `blocked`: intentionally prevented by a safety boundary.

| Capability | Reality label | Baseline evidence / boundary |
| --- | --- | --- |
| FastAPI health and API surface | `real` | Existing API and health tests. |
| SQLAlchemy persistence | `real` | Existing model/repository/API tests; SQLite-compatible baseline. |
| Canonical ERP object mapping | `real` | Canonical model and adapter tests. |
| Formula Guard and preflight | `real` | Existing policy, preflight and audit tests. |
| Skill registry/versioning | `real` | Existing skill registry, versioning and inspector tests. |
| Recording-to-skill compiler | `real` | Controlled Fake ERP recording/compiler tests. |
| Deterministic Fake ERP runtime | `fixture` | Runs against the Fake ERP surface and local records. |
| Approval planning and decision simulation | `simulated` / `advisory` | Produces safe plans and decisions; does not perform real ERP confirmation. |
| Operator action governance | `advisory` / `blocked` | Planning, validation and audit exist; real ERP writes remain disabled. |
| Odoo connection/diagnosis foundations | `staging_only` | Read-only adapter and controlled diagnosis paths exist; live availability depends on configured staging. |
| Odoo business reads | `staging_only` | Allowlisted read mappings exist; not a general Odoo model/query API. |
| Odoo quotation draft creation | `planned` | Required by the master spec’s later Phase 16; not part of Phase 0. |
| Odoo order confirmation | `blocked` | No raw ERP execution and no governed confirmation runtime in this phase. |
| Process event ingestion/OCEL | `planned` | Master spec Phase 6; not implemented by Phase 0. |
| Variant discovery | `planned` | Master spec Phase 10; not implemented by Phase 0. |
| Historical replay | `planned` | Master spec Phase 12; not implemented by Phase 0. |
| Proof of Improvement | `planned` | Master spec Phase 13; not implemented by Phase 0. |
| Process-to-Skill compiler v2 | `planned` | Master spec Phase 14; current compiler is the pre-migration controlled MVP. |
| Signed single-use execution permits | `planned` | Master spec Phase 15; current tokens/plans are not claimed as v2 permits. |
| Identity and tenant enforcement | `planned` | Master spec Phase 3; incomplete at baseline. |
| PostgreSQL/Alembic migration foundation | `planned` | Master spec Phase 2; absent from Phase 0 baseline. |
| Autonomous promotion, marketplace, second ERP connector, generic MCP | `blocked` | Explicit non-goals for the TFM path. |

## Safety invariant

No capability in this matrix authorizes an agent to call a raw ERP method. Any future effectful operation must remain behind the ERPGuard safety kernel and receive its own phase evidence.

