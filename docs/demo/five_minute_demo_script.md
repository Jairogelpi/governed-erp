# Five-minute demo script (Spec 95 Sec 39.3 / Sec 39.4)

This is a runbook for recording the TFM defense video -- not the video
itself, which this phase cannot produce. Timing budget per the master
spec: the demo block is **1:25-3:20** (115 seconds) for all 14 steps
below, inside an overall 5-minute video.

## Why steps 8-9 and 11-14 use pre-recorded evidence, not a live take

Steps 8-9 (real Odoo draft, block/approval) and 11-14 (opportunity
through sealed evidence) touch the one real, authorized Odoo 19 staging
instance this project has credentials for. Performing a second live write
on camera would mean either reusing the same idempotency key (proving
nothing new) or creating a fresh real staging record purely for a video
take -- neither is worth the risk or the noise. Both evidence files below
were captured under the same non-repudiation discipline every other real
write in this project follows (real credentials, out-of-band, never
committed; sanitized before commit):

- `docs/demo/backend_rc_live_pricing_scenario_evidence.json` -- two real
  writes, one direct-to-stable, one genuinely canary-routed.
- `docs/demo/backend_rc_decision_to_outcome_evidence.json` -- a full
  lifecycle evidence bundle (fixture-backed, not live-Odoo, for the parts
  of the chain the live test above doesn't itself cover end-to-end).

Show these files on screen (or the Decision Evidence screen in the
product web app, Spec 94, pointed at data seeded from them) rather than
performing a live write during recording.

## Sequence

| # | Step | ~Seconds | Source |
| - | --- | --- | --- |
| 1 | Connect Odoo | 5 | Live (staging connection, read-only) |
| 2 | Import/seed process history | 5 | Live (Fake ERP or OCEL import) |
| 3 | Show variants | 10 | Live (`/variants` screen or `/v1/variants`) |
| 4 | Compare baseline and candidate | 10 | Live (replay comparison) |
| 5 | Run replay | 10 | Live |
| 6 | Show Proof of Improvement | 10 | Live |
| 7 | Compile skill | 5 | Live |
| 8 | Create real Odoo draft | 10 | **Pre-recorded** (`backend_rc_live_pricing_scenario_evidence.json`) |
| 9 | Show block/approval for confirmation | 10 | **Pre-recorded** (same file) |
| 10 | Show Evidence Pack and duplicate prevention | 10 | Live (execution evidence screen) |
| 11 | Show a margin opportunity and its governed recommendation | 5 | **Pre-recorded** (`backend_rc_decision_to_outcome_evidence.json`) |
| 12 | Show independent approval and canary-routed execution | 10 | **Pre-recorded** (same file) |
| 13 | Show the realized outcome report and its non-causal disclaimer | 10 | **Pre-recorded** (same file) |
| 14 | Show the sealed, verified Decision-to-Outcome evidence bundle | 5 | **Pre-recorded** (same file) |

Total: ~115 seconds, matching the 1:25-3:20 budget. The remaining ~185
seconds of the 5-minute video (0:00-1:25 and 3:20-5:00) are the
introduction/problem framing and the closing (results summary,
limitations, close) -- outside this script's scope; see
`docs/tfm/memoria_draft.md` sections 1.0 and 1.5 (`resumen ejecutivo`,
`problema y objetivos`) for the framing content to adapt into narration.

## Operator checklist before recording

- [ ] Fresh clean-install validated (`scripts/validate_demo_install.py`
      green) so the live segments (1-7, 10) aren't performing against
      stale or broken demo state.
- [ ] Both pre-recorded evidence files open and ready to screen-share for
      steps 8-9 and 11-14.
- [ ] Product web app built and served (`ERPGUARD_SERVE_FRONTEND=true`)
      so live segments show the actual product screens, not raw JSON.
