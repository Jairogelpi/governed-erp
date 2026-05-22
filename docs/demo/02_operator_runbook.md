# Operator Runbook

**Product:** ERPGuard — ERP Agent OS  
**Sprint chain:** 20–26

This runbook documents every operator-accessible operation in the Record-to-Skill loop.

---

## Operations

### 1. Create Recording Session
- **Endpoint:** `POST /v1/record-to-skill/sessions`
- **Sprint:** 21
- **Preconditions:** Fake ERP server running at `target_base_url`
- **Safety:** Fake ERP only. No real Odoo browser opened.

### 2. Capture Browser Events
- **Endpoint:** `POST /v1/record-to-skill/sessions/{id}/events`
- **Sprint:** 21
- **Preconditions:** Active recording session
- **Safety:** Only known Fake ERP selectors accepted. No coordinate fallback.

### 3. Finish Recording Session
- **Endpoint:** `POST /v1/record-to-skill/sessions/{id}/finish`
- **Sprint:** 21
- **Preconditions:** At least one recorded event
- **Safety:** Idempotent — safe to call multiple times.

### 4. Generate UI Skill Draft
- **Endpoint:** `POST /v1/record-to-skill/sessions/{id}/draft`
- **Sprint:** 20
- **Preconditions:** Finished recording session with ≥1 event
- **Safety:** Draft is non-executable until compiled and approved.

### 5. Compile UI Skill
- **Endpoint:** `POST /v1/record-to-skill/drafts/{id}/compile`
- **Sprint:** 20
- **Preconditions:** Valid skill draft
- **Safety:** Deterministic only — no LLM. Selectors validated at compile time.

### 6. Verified Fail-Closed Replay
- **Endpoint:** `POST /v1/record-to-skill/skills/{id}/verified-replay`
- **Sprint:** 22
- **Preconditions:** Compiled UI skill
- **Safety:** Pre/post page state verified. Fail-closed: step not executed if check fails. No automatic repair. No LLM fallback.

### 7. Create Skill Version
- **Endpoint:** `POST /v1/skills/versions`
- **Sprint:** 23
- **Preconditions:** Compiled skill
- **Safety:** Versions are immutable once active.

### 8. Promote Version to Candidate
- **Endpoint:** `POST /v1/skills/versions/{id}/promote`
- **Sprint:** 23
- **Preconditions:** Version in `draft` status, promotion readiness checks passed
- **Safety:** Lifecycle transition only — no execution.

### 9. Approve Skill Version
- **Endpoint:** `POST /v1/skills/versions/{id}/approve`
- **Sprint:** 23
- **Preconditions:** Version in `candidate` status
- **Safety:** Human operator approval required. Recorded in lifecycle audit.

### 10. Activate Skill Version
- **Endpoint:** `POST /v1/skills/versions/{id}/activate`
- **Sprint:** 23
- **Preconditions:** Approved version
- **Safety:** Active versions are immutable. Only one version active per skill.

### 11. Manual Active Skill Run
- **Endpoint:** `POST /v1/skills/versions/{id}/run`
- **Sprint:** 24
- **Preconditions:** Active version (`is_active=True`), Fake ERP target
- **Safety:** Deterministic replay only. No LLM at runtime. No background worker. Full step audit stored.

### 12. Create Skill Schedule
- **Endpoint:** `POST /v1/skills/versions/{id}/schedules`
- **Sprint:** 25
- **Preconditions:** Active version
- **Safety:** Minimum interval enforced at 60s. No cron daemon created.

### 13. Manual Scheduler Tick
- **Endpoint:** `POST /v1/skills/schedules/tick`
- **Sprint:** 25
- **Preconditions:** Active schedule with `next_run_at ≤ now`
- **Safety:** Manual trigger only — no autonomous execution. Dedup window enforced. Execution lock acquired per schedule. All steps audited.

### 14. Assemble Evidence Pack
- **Endpoint:** `POST /v1/operator/evidence-packs`
- **Sprint:** 26
- **Preconditions:** At least one completed skill run
- **Safety:** Read-only assembly — no new executions triggered.

### 15. Get Operator Runbook
- **Endpoint:** `GET /v1/operator/demo-runbook`
- **Sprint:** 26
- **Preconditions:** None
- **Safety:** Static read-only — no side effects.

---

## Kill Switches

| Switch | Effect |
|--------|--------|
| `global_kill_switch` | Halts all execution |
| `runtime_execution_kill_switch` | Halts skill runs |
| `write_pilot_kill_switch` | Halts write pilots |

---

## Safety Flags

| Flag | Default | Note |
|------|---------|------|
| `ALLOW_GENERIC_REAL_ODOO_WRITES` | `false` | Must stay false for demo |
| `ALLOW_R3_R4_REAL_WRITES` | `false` | Hardcoded off |
| `ALLOW_R2_REAL_WRITE_PILOT` | `false` | Off by default |
| `ALLOW_R1_REAL_WRITE_PILOT` | `false` | Off by default |
