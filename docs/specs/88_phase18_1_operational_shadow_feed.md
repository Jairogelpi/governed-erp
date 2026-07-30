# Phase 18.1 — Operational Shadow Feed

## Outcome

Phase 18.1 connects effects-free Shadow Mode to the persisted canonical
event store. Every OCEL, Odoo webhook or bounded Odoo poll ingestion now
projects affected canonical objects into applicable shadow deployments.
Reference and candidate definitions evaluate the same reconstructed trace;
neither decision is routed back to the ERP.

The existing `active_version` database field remains compatibility naming.
The API also exposes it as `reference_version`. A promoted active pointer
does not exist until Phase 19.

## Canonical trace

The operational feed reconstructs each case from:

- canonical event ID and key;
- normalized event type and original timestamp;
- ingestion source and correlation ID;
- historical and synthetic markers;
- relational object links and qualifiers;
- canonical object state and event business attributes;
- extraction mode and variant ID.

Sensitive business attributes are not copied into provenance. Provenance
stores a deterministic hash for the business portion of each event.

The derived idempotency scope is:

```text
deployment_id + case_id + canonical_trace_hash
```

Reingesting the same trace reuses existing evidence. A new event or changed
canonical projection produces a new immutable evaluation. Metrics use only
the latest trace for each case.

## Feed activation

Canonical ingestion invokes the feed synchronously after its event
transaction commits. A feed failure cannot invent an ERP effect and is
recorded in an append-only `ShadowFeedRun`.

Operators can also backfill or retry:

```text
POST /v1/deployments/{deployment_id}/feed/process
```

with an optional bounded list of case IDs. This is continuous with respect
to calls entering the existing ingestion seams. It is not a new webhook
server, scheduler or autonomous Odoo poller.

## Deferred outcome reconciliation

Evaluation and observed outcome are separate append-only records:

```text
POST /v1/deployments/{deployment_id}/cases/{case_result_id}/outcomes
```

An outcome records its idempotency key, payload, optional normalized decision
status, provenance, observation timestamp, source event IDs, actor and hash.
Provenance is closed to `manual`, `canonical_event`, `odoo`, `fixture` or
`synthetic`. Source events must belong to the tenant and link to the same
canonical object as the evaluated case.

## Metrics and advisory eligibility

Only `canonical_feed` evaluations count toward canary eligibility. Manual
Phase 18 cases remain visible but cannot inflate operational evidence.

The dashboard exposes canonical/operational coverage, agreement and a 95%
Wilson interval, decision coverage, latest-review coverage, reviewer-label
rates, outcome reconciliation and accuracy, accuracy interval, variant
distribution and observation-window completion.

`eligible_for_canary` is returned only when all deployment-specific checks
pass:

```text
minimum operational case count
AND agreement threshold
AND minimum decision coverage
AND no unresolved unsafe_candidate
AND minimum review coverage
AND minimum outcome reconciliation
AND observation window completed
```

The response includes `recommendation_is_advisory=true`. It creates no
canary, active pointer, traffic routing, promotion approval or rollback.

## Persistence

Migration `0018_operational_shadow_feed` adds deployment eligibility
criteria, canonical trace/provenance fields, append-only outcome observations
and append-only feed runs.

## Demonstrated path

The sanitized evidence in
[`docs/demo/phase18_1_operational_shadow_feed_evidence.json`](../demo/phase18_1_operational_shadow_feed_evidence.json)
freezes:

```text
canonical Odoo-sourced events ingested
→ matching shadow deployment found
→ real timestamps and provenance reconstructed
→ reference/candidate evaluated
→ identical retry deduplicated
→ later outcome reconciled with Odoo provenance
→ operational metrics updated
→ recommendation remains advisory
→ ERP writes = 0
```

## Exit criteria

- canonical ingestion automatically feeds applicable shadow deployments;
- trace sequence, timestamps, IDs, sources and links are preserved;
- idempotency is derived from the canonical trace;
- outcomes arrive later with explicit provenance;
- latest operational cases drive eligibility metrics;
- manual cases cannot qualify a candidate for canary;
- unresolved unsafe review blocks eligibility;
- evidence remains append-only;
- no connector write, permit, execution, promotion or rollback is added.
