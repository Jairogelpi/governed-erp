# Roadmap

The active sequence is defined by
`docs/specs/84_erpguard_evolution_master_spec.md`, extended by
`docs/specs/92_governed_decision_to_outcome_backend_rc.md` for the current
delivery.

**Completed:** Phases 0–19 (baseline freeze through identity, migrations,
connector SDK, canonical events, variant discovery, process candidates,
historical replay, Proof of Improvement, the skill compiler, execution
permits, governed confirmation, shadow mode, decision intelligence,
opportunity/ROI sizing, and the skill deployment lifecycle) plus Spec 92's
four backend workstreams:

- **Workstream A** — governed recommendation → approval → bounded action
  draft → the `sales.quote.create_pricing_scenario_draft` Odoo capability.
- **Workstream B** — operational canary router: deterministic routing,
  safety pauses, promotion hardening.
- **Workstream C** — outcome measurement and realized ROI, gated and
  non-causal.
- **Workstream D** — sealed, hash-chained decision-to-outcome evidence
  bundle.

**Next (not started):** the product web experience, complete business
onboarding, the visual decision/evidence journey, the ERPRiskBench
experiment suite, TFM statistical results, the final public README/demo
videos, a security/release review, and the `v1.0.0-tfm` freeze — see Spec
92 Sec 30.

**Known backend gaps carried forward:** net ROI with implementation cost
(Spec 92 Sec 10.6), the canary dashboard's `estimated_opportunity_value`
(always `null`), and a live Odoo staging run of the pricing-scenario
capability (never performed in this environment — see
`docs/demo/backend_rc_live_pricing_scenario_evidence.json`).

Real ERP writes, autonomous promotion, and generic raw ERP capabilities
remain outside scope for every phase above — see each spec's "Out of
scope" section for the exact boundary.
