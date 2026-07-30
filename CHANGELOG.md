# Changelog

## Unreleased — Phase 17 / 17.1

### Added

- Bounded staging-only `sales.order.confirm` with independent exact-scope
  approval and signed single-use permit.
- Immutable order snapshot, automation fingerprint, side-effect budget,
  postcondition evaluation, sealed Evidence Pack and CompensationPlan.
- Migrations `0015_governed_confirmation` and
  `0016_confirmation_side_effect_contract`.
- Sanitized live staging failure/compensation evidence and an
  unexpected-posted-invoice regression.

### Safety

- Confirmation remains false by default.
- The live unexpected invoice was classified `failed`, not successful.
- Manual compensation preserved invoice and linked credit note and verified
  documentary net effect zero.
- No public cancellation, invoice-posting, payment, deletion or generic Odoo
  RPC capability was added.

## 0.14.0 - 2026-07-27

### Added

- Phase 0 baseline freeze artifacts and ADR-0001.
- Canonical package/API/README version metadata.
- `uv.lock`, CI quality gates, Docker install surface and community policy files.
- Public/legacy documentation boundary and deprecation policy.

### Safety

- No raw ERP execution or new ERP write capability was added.

## Historical releases

The previous `0.12.x` and `0.13.x` release-candidate material remains in the legacy documentation set.

