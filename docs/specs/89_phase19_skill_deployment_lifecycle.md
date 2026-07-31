# Phase 19 — Skill Deployment Lifecycle (spec 18.4)

## Problem

`SkillPackage.status` only ever moved `compiled -> approved`, once, then was
frozen. Phase 18/18.1 shadow evidence can recommend `eligible_for_canary`,
but nothing consumed that recommendation — there was no way to actually
promote a package to canary, promote canary to active, or roll an active
package back. There was also no formal "active version" for a process: the
closest thing, `ShadowDeployment.active_version`, is a label recording what
was active *during a comparison run*, not a live pointer.

## Design

The active version is derived, not stored as a mutable pointer column: it is
whichever `SkillPackage` row has `status == "active"` for a given
`(tenant_id, process_key)`. `SkillDeploymentService` enforces there is at
most one. The full history of promotions/rollbacks/deprecations is an
append-only `skill_deployment_events` table (same immutable-evidence idiom
as `shadow_deployments` and friends).

## State machine

```
compiled -> approved -> canary -> active -> rolled_back
                                     ^  |
                                     |  v
                                   deprecated   (superseded by a newer
                                                  promotion; re-promotable to
                                                  active if a later rollback
                                                  restores it)
```

Only `rolled_back` is terminal — `SkillPackage`'s `before_update` listener
rejects any further status change out of it, and rejects any change at all
to content columns (`package_json`,
`validation_result_json`, `package_hash`, `candidate_id`, `proof_id`,
`process_key`, `candidate_version`, `connector_id`) regardless of status.

## Operations (`erpguard/domain/deployment/service.py`)

- **`promote_to_canary`** — `approved -> canary`. Requires a
  `ShadowDeployment` whose `dashboard()` recommendation is
  `eligible_for_canary` (reuses `ShadowService.dashboard`, the same
  advisory computation Phase 18.1 exposes on its own dashboard endpoint —
  this phase is the first thing that actually gates on it).
- **`promote_to_active`** — `canary -> active`. If another package for the
  same process is currently `active`, it is deprecated (not rolled back —
  `rolled_back` is reserved for a package pulled because something was
  actually wrong with it).
- **`rollback`** — `active -> rolled_back`. Walks `skill_deployment_events`
  for the process to find the package that was active immediately before
  the one being rolled back, and restores it to `active` if it's still
  `deprecated`. No predecessor → the process ends up with no active
  package at all (an explicit, visible state, not silently defaulting to
  anything).

## API (`apps/api/routes/public_v1/skill_packages.py`)

- `POST /v1/skills/{skill_id}/promote-canary` — `{shadow_deployment_id, reason}`
- `POST /v1/skills/{skill_id}/promote-active` — `{reason}`
- `POST /v1/skills/rollback` — `{process_key, reason}`
- `GET /v1/processes/{process_key}/active-skill`

## Out of scope

Wiring the active pointer into actual skill execution. The runtime that
executes skills today (`Skill`/`SkillVersion` in `erpguard/db/models.py`,
served by `apps/api/routes/public_v1/skills.py`) is a separate legacy
demo-run system, not the governed candidate→proof→`SkillPackage` chain this
phase operates on. Connecting "the active `SkillPackage` for this process"
to "what actually executes" is future work.
