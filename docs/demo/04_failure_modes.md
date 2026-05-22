# Failure Modes

**Product:** ERPGuard — ERP Agent OS  
**Sprint chain:** 20–26

This document catalogs known failure modes and their handling.

---

## Recording Layer (Sprint 21)

| Failure | Detection | Handling |
|---------|-----------|----------|
| No events recorded | `finish_session` check | Returns `compiler_readiness: not_ready` |
| Unknown selector | Event capture validation | Event rejected with `selector_not_allowed` |
| Session already finished | `finish_session` idempotency | Returns current state, no error |
| Target URL unreachable | Fake ERP health check | Recording session created, events fail at inject time |

---

## Compilation Layer (Sprint 20)

| Failure | Detection | Handling |
|---------|-----------|----------|
| Draft not found | Repository lookup | `404 draft_not_found` |
| No steps to compile | Compiler validation | `compiler_readiness: not_ready` error |
| Invalid selector in step | Compile-time check | Compilation rejected |
| Duplicate step ID | Normalizer | Deduplicated before compile |

---

## Replay Layer (Sprint 22)

| Failure | Detection | Handling |
|---------|-----------|----------|
| Pre-check selector missing | Page state verifier | Step marked `pre_check_failed`, not executed |
| Post-check state mismatch | Post-step verifier | Step marked `post_check_failed`, run stops |
| Modal / error dialog detected | Modal error detector | Step blocked, failure classified |
| Selector no longer stable | Selector stability check | Warning emitted, step may proceed with degraded confidence |
| Target URL unreachable | Playwright error | Run marked `failed`, full evidence stored |

**Fail-closed rule:** If any verification step fails, the replay step is NOT executed. There is no automatic repair or coordinate fallback.

---

## Versioning Layer (Sprint 23)

| Failure | Detection | Handling |
|---------|-----------|----------|
| Invalid lifecycle transition | Transition allowlist | `400 invalid_transition` |
| Version not in correct state | Gate check | `400 gate_failed` with detail |
| Rollback to non-existent version | Repository lookup | `404 version_not_found` |
| Promoting with failed readiness checks | Readiness gate | `400` with blocking checks listed |

---

## Active Runner (Sprint 24)

| Failure | Detection | Handling |
|---------|-----------|----------|
| Version not active | `is_active` check | `400 version_not_active` |
| Non-Fake ERP target | Gate service | `400 target_not_allowed` |
| Run step fails | Replay runtime | Run marked `failed`, step evidence stored |
| Inputs validation error | Input validator | `400 invalid_inputs` |

---

## Scheduler (Sprint 25)

| Failure | Detection | Handling |
|---------|-----------|----------|
| Lock already held | Lock service TTL check | Skip with `skipped_locked` reason |
| Min interval not elapsed | Planner check | Skip with `skipped_min_interval` reason |
| Duplicate inputs within dedup window | Dedup service | Queue entry created as `skipped_dedup` |
| Schedule not active | Gate service | Schedule not in tick list |
| Dispatch failure | Exception catch in tick | `TickFailure` recorded, lock released |
| Schedule version no longer active | Gate re-check | Skip with `gate_failed` reason |

---

## Evidence Pack (Sprint 26)

| Failure | Detection | Handling |
|---------|-----------|----------|
| Pack not found | Repository lookup | `404 evidence_pack_not_found` |
| Demo seed failure (replay chain broken) | Exception catch | `500` with `demo_seed_error` detail |
| Safety invariant violated | Safety report check | `verdict: unsafe` in safety report |

---

## Global Safeguards

- **Kill switch:** `POST /v1/platform/tenants/{id}/kill-switch` — halts all execution immediately
- **Audit export:** All events are exportable for compliance review
- **Secret redaction:** No secrets appear in any API response or audit log
