# Active `SkillPackage` → Execution Runtime Wiring

## Problem

Phase 19 added a governed `SkillPackage` lifecycle
(`compiled -> approved -> canary -> active -> rolled_back`) with
`SkillDeploymentService.get_active(tenant_id, process_key)`, but left it
completely unwired: zero call sites outside its own files.

`PermitService` (Phase 15, real-write execution,
`erpguard/domain/execution/permit_service.py`) still only accepted packages
with `status == "approved"`, checked identically at `plan()`, `approve()`,
and `execute()`. This wasn't just a gap — it was a live bug: promoting a
package to `canary` or `active` (Phase 19's whole point) made
`PermitService` reject it with `SkillNotActive`.

## Fix

1. **Eligibility.** All three status checks now test membership in
   `_EXECUTABLE_STATUSES = {"approved", "canary", "active"}` instead of
   equality with `"approved"`. `rolled_back`/`deprecated` remain rejected —
   correct, those states mean "don't run this."
2. **Resolution.** `PermitService.plan()` gained an optional `process_key`
   parameter. Callers may still pass `skill_package_id` explicitly
   (unchanged, all Phase 15 tests keep working); if they omit it and pass
   `process_key` instead, `plan()` resolves the caller's package via
   `SkillDeploymentService.get_active`. No active package →
   `NoActiveSkillForProcess`. Neither given → validation error.

`ExecutionRun.skill_package_id` already records whichever package actually
ran, whether named explicitly or resolved — that's the traceability this
wiring buys: a run's evidence now connects back through Phase 19's
promotion/rollback history for its process.

## API

`POST /v1/runs/plan` — `skill_package_id` is now optional; `process_key` is
a new optional alternative. Exactly one of the two must be supplied.

## Out of scope

Anything beyond eligibility + resolution — no change to approval, kill
switch, governed-confirmation, or execute-time re-verification logic; those
already operate on whatever `ExecutionRun.skill_package_id` was set to.
