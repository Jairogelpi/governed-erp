# Roadmap

The active sequence is defined by
`docs/specs/84_erpguard_evolution_master_spec.md`, extended by
`docs/specs/92_governed_decision_to_outcome_backend_rc.md`,
`docs/specs/93_phase20_erpriskbench_and_experiments.md` and
`docs/specs/94_phase21_product_web_application.md` for the current
delivery.

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

**Next (not started):** TFM statistical results, the final public
README/demo videos, a security/release review, and the `v1.0.0-tfm`
freeze — see Spec 92 Sec 30.

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
