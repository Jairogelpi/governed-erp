# Roadmap

The active sequence is defined by
`docs/specs/84_erpguard_evolution_master_spec.md`, extended by
`docs/specs/92_governed_decision_to_outcome_backend_rc.md`,
`docs/specs/93_phase20_erpriskbench_and_experiments.md`,
`docs/specs/94_phase21_product_web_application.md` and
`docs/specs/95_phase22_tfm_delivery_and_release_freeze.md` for the
current delivery.

**Completed:** Phases 0–19 (baseline freeze through identity, migrations,
connector SDK, canonical events, variant discovery, process candidates,
historical replay, Proof of Improvement, the skill compiler, execution
permits, governed confirmation, shadow mode, decision intelligence,
opportunity/ROI sizing, and the skill deployment lifecycle); Spec 92's four
backend workstreams; Spec 93 (Phase 20 — ERPRiskBench); Spec 94 (Phase 21 —
Product Web Application):

- **Workstream A** — governed recommendation → approval → bounded action
  draft → the `sales.quote.create_pricing_scenario_draft` Odoo capability.
- **Workstream B** — operational canary router: deterministic routing,
  safety pauses, promotion hardening.
- **Workstream C** — outcome measurement and realized ROI, gated and
  non-causal.
- **Workstream D** — sealed, hash-chained decision-to-outcome evidence
  bundle.
- **Phase 20 (ERPRiskBench)** — deterministic 120-case synthetic benchmark
  comparing `fixed_workflow` / `direct_tool_agent` / `erpguard_candidate`
  against Sec 28.3's 14 metrics.
- **Phase 21 (Product Web Application)** — React + TypeScript SPA
  (`web/`) covering both the existing pillar (onboarding through execution
  evidence) and the decision-to-outcome pillar (opportunities through
  sealed evidence), served by `create_public_app` behind
  `ERPGUARD_SERVE_FRONTEND=true`; the old `/demo` engineering dashboard
  stays internal-only and now banners to the new app.

- **Phase 22 (TFM Delivery and Release Freeze, Spec 95)** — packaging and
  evidence only, no new product capability: `scripts/validate_demo_install.py`
  + `docker-compose.demo.yml` (clean-install acceptance against Fake
  ERP), `scripts/export_benchmark_report.py` (a real, citable
  `BenchmarkRun` for the TFM memory), the `release-checks` CI job
  (dependency scan, SBOM, benchmark smoke test, docs link check),
  `docs/tfm/annexes/` (the Sec 39.2 annex set), and a first
  `docs/tfm/memoria_draft.md` draft. Found and fixed one real
  installability bug in the process (`erpguard.db.session.init_db()` was
  missing four model-package imports) -- see
  `docs/tfm/annexes/installation.md`.

**Next (not started):** the thesis author's own review of
`docs/tfm/memoria_draft.md` and the five-minute demo video (script at
`docs/demo/five_minute_demo_script.md`), and cutting the `v1.0.0-tfm` tag
once both are actually ready — a deliberate manual step, not automated
by this phase.

**Backend RC status:** no known gaps remain in Spec 92's backend scope. Net
ROI with implementation cost (Sec 10.6) and the canary dashboard's
`estimated_opportunity_value` (Sec 9.8) are both implemented. The Sec 19/20
live Odoo staging runs of the pricing-scenario capability (direct-to-stable
and genuinely canary-routed) have been performed and verified — see
`docs/demo/backend_rc_live_pricing_scenario_evidence.json`. CI gates (Sec
21) are fully green, including a secret scan that did not exist before this
delivery.

Real ERP writes, autonomous promotion, and generic raw ERP capabilities
remain outside scope for every phase above — see each spec's "Out of
scope" section for the exact boundary.
