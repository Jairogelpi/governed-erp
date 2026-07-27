# ADR-0001: Incremental ERPGuard Evolution migration

- **Status:** accepted
- **Date:** 2026-07-27
- **Decision owners:** ERPGuard repository maintainers
- **Baseline:** `e483f5c5f272139c65a02ebc32ab11f5e323b6a4`

## Context

The repository contains a verified ERPGuard implementation with a large accumulated API, product and persistence surface. The ERPGuard Evolution master specification defines a bounded-context architecture, canonical events, process evolution and a governed Odoo vertical, but explicitly prohibits a destructive rewrite and requires compatibility during migration.

## Decision

Migrate incrementally inside the existing monorepo:

1. Add new bounded-context modules beside the current implementation.
2. Introduce compatibility imports and explicit API boundaries.
3. Move one domain at a time only after tests and ownership are established.
4. Keep legacy routes operational behind a future feature flag until replacement is proven.
5. Delete legacy paths only after two consecutive phases no longer depend on them.
6. Preserve ERPGuard as the mandatory safety kernel for every future effectful connector operation.

Phase 0 itself is documentation and evidence only. It adds no runtime architecture and no ERP execution.

## Alternatives rejected

- **Greenfield rewrite:** rejected because it would discard verified behavior and violate the migration contract.
- **Big-bang file move:** rejected because it would obscure ownership, compatibility and regression failures.
- **Immediate real Odoo writes:** rejected because the required permits, identity, migrations, postconditions and evidence are later phases.
- **Generic raw ERP capability:** rejected because it violates the safety kernel and the master spec’s explicit prohibition.

## Consequences

Positive:

- Existing verified behavior remains the compatibility baseline.
- Each later phase can be reviewed, tested and rolled back independently.
- Architectural deviations are recorded instead of silently accumulating.

Costs:

- Temporary duplication and compatibility adapters are expected.
- Legacy modules remain until replacement evidence exists.
- The repository will not match the target tree immediately.

## Verification required for future deviations

Every architectural deviation from the master specification must add or update an ADR, state its compatibility/deprecation mapping, and include focused and full regression evidence.

