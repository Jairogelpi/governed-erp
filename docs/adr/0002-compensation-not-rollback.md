# ADR-0002: Compensation instead of destructive rollback

- **Status:** accepted
- **Date:** 2026-07-30
- **Decision owners:** Governed ERP repository maintainers

## Context

An authorized Phase 17 staging confirmation triggered a posted invoice
outside the approved effects. ERPGuard rejected clean success. Deleting an
accounting event would destroy evidence and misrepresent what occurred.

## Decision

Effectful ERP operations use compensation when business history must remain:

- posted source documents are never deleted to manufacture clean history;
- a posted invoice is neutralized by a linked posted credit note;
- logistics are cancelled only while uncompleted;
- dependency order and fresh reads are mandatory;
- compensation requires separate explicit approval;
- original and compensating records remain in the Evidence Pack;
- a violated run remains `failed` after compensation.

Compensation proves a neutralized business effect. It does not rewrite the
original run as successful and is not called rollback.

## Consequences

- Accounting and operational evidence remains auditable.
- Residual documents are expected and reported.
- Some effects may not be safely compensable; the operator must stop.
- Phase 17.1 models the plan but adds no compensation execution.

## Rejected alternatives

- Deleting the invoice: destroys accounting evidence.
- Resetting every record to draft: downstream workflows may have progressed.
- Marking the run successful after cleanup: the approved budget was violated.
- Generic automatic rollback: ERP dependencies are not universal.
