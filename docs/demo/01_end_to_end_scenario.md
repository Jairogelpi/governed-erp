# End-to-End Demo Scenario

**Scenario:** Fake ERP Formula Review — Full Operator Demo  
**ERP target:** `http://127.0.0.1:8000/fake-erp` (local only)  
**Operator:** `demo_operator`

## Prerequisites

1. Server running: `uvicorn apps.api.main:app --port 8000`
2. All tests passing: `python -m pytest -q`
3. Open `http://127.0.0.1:8000/demo` in a browser

---

## Step 1 — Record browser process (Sprint 21)

**Endpoint:** `POST /v1/record-to-skill/sessions`

```json
{ "name": "Demo — Fake ERP Formula Review",
  "target_base_url": "http://127.0.0.1:8000" }
```

Then open the Fake ERP recorder overlay and interact with:
- Sales orders search (`SO-VALID`)
- Order detail navigation
- Formula tab click
- Formula review action

Or inject synthetic events:

```json
POST /v1/record-to-skill/sessions/{id}/events
{ "event_type": "fill", "selector": "[data-testid='order-search']", "value": "SO-VALID" }
```

Finish: `POST /v1/record-to-skill/sessions/{id}/finish`

---

## Step 2 — Generate skill draft (Sprint 20)

**Endpoint:** `POST /v1/record-to-skill/sessions/{id}/draft`

Returns `draft_id`. The draft is non-executable until compiled and approved.

---

## Step 3 — Compile deterministic skill (Sprint 20)

**Endpoint:** `POST /v1/record-to-skill/drafts/{id}/compile`

Returns `skill_id` + `compiled_skill_id`. No LLM involved. Selectors validated at compile time.

---

## Step 4 — Verified fail-closed replay (Sprint 22)

**Endpoint:** `POST /v1/record-to-skill/skills/{id}/verified-replay`

Runs against Fake ERP. Pre/post page state verified. Step not executed if check fails. No automatic repair.

---

## Step 5 — Create version → promote → approve → activate (Sprint 23)

```
POST /v1/skills/versions              → draft
POST /v1/skills/versions/{id}/promote → candidate
POST /v1/skills/versions/{id}/approve → approved
POST /v1/skills/versions/{id}/activate → active (immutable)
```

Active versions cannot be mutated. Rollback is a lifecycle switch only.

---

## Step 6 — Manual run (Sprint 24)

**Endpoint:** `POST /v1/skills/versions/{id}/run`

Only active versions can run. Deterministic replay through the verified stack. Full step audit stored.

---

## Step 7 — Create schedule → activate → tick (Sprint 25)

```
POST /v1/skills/versions/{id}/schedules   interval_seconds=60
POST /v1/skills/schedules/{id}/activate
POST /v1/skills/schedules/tick            (manual trigger only)
```

Tick evaluates due active schedules, acquires lock, runs dedup check, dispatches through the active runner, updates `next_run_at`, and audits every step.

---

## Step 8 — Assemble evidence pack (Sprint 26)

**Endpoint:** `POST /v1/operator/evidence-packs`

Pass the `seed_result` from Step 1–7. The evidence pack collects:
- Safety invariant report (12 invariants, all enforced)
- Runbook summary (15 operations documented)
- Sprint coverage (7 sprints, all verified)
- Test evidence (1000+ tests passing)

Then:
- `GET /v1/operator/evidence-packs/{id}/safety-report`
- `GET /v1/operator/evidence-packs/{id}/final-report`

---

## Quick-start (automated)

```bash
# Seed the full scenario in one call
POST /v1/operator/demo-seed  {"operator": "demo_operator"}

# Then assemble the evidence pack
POST /v1/operator/evidence-packs  {"seed_result": <seed output>}

# Get the final report
GET /v1/operator/evidence-packs/{pack_id}/final-report
```
