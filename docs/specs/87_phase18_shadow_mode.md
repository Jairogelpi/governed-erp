# Phase 18 — Shadow Mode

## Outcome

Phase 18 evaluates an immutable candidate process beside the registered
active process on the same incoming case. It stores both decisions, their
differences, an optional observed outcome and append-only human review
labels. It never routes the candidate decision to Odoo or any other source
system.

This is evaluation, not activation. The deployment status is always
`shadow`; promotion, canary routing and rollback remain Phase 19 work.

## Admission contract

`POST /v1/deployments/shadow` accepts only a candidate that is:

- tenant-scoped, submitted and valid;
- based on an existing registered active process definition;
- backed by a Proof of Improvement whose recommendation is exactly
  `eligible_for_shadow`;
- bound to frozen baseline and candidate replays with matching process,
  versions and object type.

The deployment stores the active and candidate versions, proof, object type,
operator, configurable agreement threshold and `no_effects=true`.

## Case evaluation

`POST /v1/deployments/{deployment_id}/cases` accepts a bounded event
sequence, canonical object attributes, a case identifier, an idempotency key
and an optional actual outcome.

The same deterministic Replay Engine evaluates both process definitions.
ERPGuard stores:

- active and candidate statuses;
- decision traces and decision coverage;
- predicted effects and safety violations;
- agreement;
- normalized difference categories;
- optional observed outcome;
- input and deterministic result hashes.

Repeated submission with the same idempotency key and identical content
returns the existing evidence. Reusing the key for different content is
rejected.

## Review and dashboard

Human reviews are append-only and use a closed label vocabulary:
`active_preferred`, `candidate_preferred`, `equivalent`,
`unsafe_candidate`, `needs_investigation` and `insufficient_evidence`.

The dashboard exposes evaluated cases, agreement/disagreement counts,
agreement rate, the deployment-specific threshold, whether that threshold
is met, difference-category counts and reviewer-label counts. Meeting the
threshold does not promote or activate anything.

## No-effects boundary

The Shadow Service imports no connector, Odoo transport, execution permit or
execution runtime. It creates no `ExecutionRun`. Its only writes are the
append-only shadow deployment, case result and review evidence records.

This boundary is covered by both behavioral and static dependency tests.

## Selected example

The frozen example in
[`docs/demo/phase18_shadow_mode_selected_example.json`](../demo/phase18_shadow_mode_selected_example.json)
uses a staged/synthetic incoming quotation with an invalid formula:

```text
active formula guard → failed / block
candidate without that decision → passed
agreement → false
differences → decision_removed, status_changed
actual observed outcome → blocked
reviewer → unsafe_candidate
ERP/source-system writes → 0
```

The example demonstrates why shadow evidence is useful even after a
candidate passed its historical Proof of Improvement: a new incoming case
can expose a previously unseen safety disagreement without giving the
candidate authority to act.

## API

- `POST /v1/deployments/shadow`
- `GET /v1/deployments/{deployment_id}`
- `POST /v1/deployments/{deployment_id}/cases`
- `GET /v1/deployments/{deployment_id}/cases`
- `POST /v1/deployments/{deployment_id}/cases/{case_result_id}/reviews`
- `GET /v1/deployments/{deployment_id}/dashboard`

## Exit criteria

- candidate evaluation has no source-system effect;
- admission requires valid candidate and eligible proof;
- active/candidate differences and actual outcome are persisted;
- evidence and reviews are append-only and tenant-isolated;
- evaluation is deterministic and idempotent;
- agreement threshold is deployment-specific;
- a selected disagreement example is frozen;
- no canary, activation, promotion or rollback path is added.
