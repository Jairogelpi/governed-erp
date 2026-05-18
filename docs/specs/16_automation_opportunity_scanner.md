# 16 Automation Opportunity Scanner And ROI Engine Strategic Spec

**Status:** Strategic product spec
**Date:** May 18, 2026
**Relationship to ERP Agent OS:** Defines the discovery layer that turns ERP connectivity into visible business value.
**Relationship to ERPGuard:** ERPGuard remains the mandatory safety kernel for any recommendation that becomes an automation, especially for risky or write-capable actions.

## 1. Product Statement

Connect your ERP. We find what to automate, estimate the value, and help you create safe skills.

The Automation Opportunity Scanner and ROI Engine make ERP Agent OS business-buyable by identifying valuable automation candidates automatically after ERP connection. Instead of waiting for the business owner to describe every workflow, the system analyzes business data, detects bottlenecks and error patterns, estimates ROI, ranks opportunities, and offers a safe path to create a skill from each recommendation.

This layer is the bridge between connection and adoption. It turns raw ERP access into an actionable roadmap that a business owner can understand without thinking in MCP tools, skill YAML, or policy DSL.

## 2. Why This Matters

Business owners do not think in MCP, skills, or policy DSL. They think in time saved, errors avoided, bottlenecks, risk reduction, and control.

If the product only waits for the user to request an automation, it misses the biggest value source: the system already has enough read-only evidence to suggest where work is repetitive, fragile, delayed, or error-prone. The platform should surface those opportunities automatically and translate them into concrete business outcomes.

This matters because the first impression of the product is not just whether it can automate something. It is whether it can immediately show the user where the value is, why it matters, and how to safely act on it.

## 3. Architecture

```text
ERP Connection
-> Business Snapshot
-> Process Signals Extractor
-> Automation Opportunity Scanner
-> ROI Engine
-> Recommendation Cards
-> Skill Creation Flow
-> Skill Registry
-> Metrics Dashboard
```

The architecture separates observation from recommendation and recommendation from execution.

The Business Snapshot collects read-only evidence from the ERP. The Process Signals Extractor converts that evidence into candidate signals such as stagnation, repetition, errors, missing data, and control bottlenecks. The Automation Opportunity Scanner groups those signals into opportunities. The ROI Engine scores and prioritizes them. Recommendation Cards present the result in business language. Skill Creation Flow turns a chosen recommendation into a guarded automation draft. The Skill Registry stores the resulting skill. The Metrics Dashboard measures realized value over time.

## 4. Business Snapshot

The Business Snapshot is the read-only analytical view of the connected ERP.

It should analyze at least:

- sales orders;
- invoices;
- inventory moves;
- manufacturing orders;
- purchases;
- CRM opportunities;
- automated actions;
- access rules;
- imports;
- custom fields;
- error logs where available.

The snapshot should be broad enough to reveal operational patterns but constrained enough to remain safe, explainable, and cheap to refresh. It is not a deep crawl of every system detail. It is a value-seeking diagnostic layer that looks for signs of repetition, exception handling, delay, risk, and data quality issues.

## 5. Opportunity Detectors

The first Odoo MVP should begin with a small set of high-signal detectors.

Initial Odoo MVP detectors:

- invalid or missing formulas;
- sales orders stuck in stage or status;
- manufacturing blocked by missing components;
- products requiring lots but missing traceability;
- repeated import or data quality errors;
- automated action failures;
- access or permission issues;
- CRM opportunities without follow-up;
- invoices or orders with inconsistent fields.

Each detector should produce a structured finding with a record set, a human-readable reason, a rough severity estimate, and a recommendation hint. The detectors should be designed to identify likely automation candidates, not just raw anomalies.

## 6. ROI Scoring

The ROI Engine turns detected opportunities into a business-prioritized queue.

Simple scoring formula:

```text
automation_score = frequency * estimated_manual_minutes * cost_per_hour
```

The score should also consider:

- estimated_error_cost;
- risk_reduction_score;
- implementation_difficulty;
- operational_risk.

The goal is not exact finance-grade accounting. The goal is a consistent, explainable priority model that helps the user decide what to automate first. High-frequency, high-friction, high-error-cost, low-risk opportunities should rise to the top. Low-frequency or high-risk cases should be deprioritized or routed into a guarded review path.

Scores should remain transparent. The user should be able to see why an opportunity was ranked highly and what assumption drove the estimate.

## 7. Recommendation Card

Each opportunity should be presented as a recommendation card that a business user can act on immediately.

Each card should include:

- title;
- affected records;
- examples;
- estimated hours saved;
- risk reduction;
- difficulty;
- recommended skill;
- suggested guard;
- create automation button.

The recommendation card should read like a business insight, not an engineering report. It should explain what was found, why it matters, and what the next safe action is.

## 8. One-Click Skill Creation

From each recommendation, the user can click:

Create automation

This should open the ERP Agent Builder with prefilled context from the recommendation, including the detected records, the target process, the likely guard requirements, and the relevant business snapshot evidence.

The handoff should be tight. The user should not need to re-describe the problem from scratch. The recommendation should become the starting point for skill creation, review, and approval.

## 9. Dashboard

The dashboard should communicate realized value and open opportunities in plain business terms.

It should show:

- automations active;
- hours saved;
- errors prevented;
- approvals requested;
- tokens avoided;
- top new opportunities.

The dashboard should help answer two questions: what value has already been delivered, and what should be automated next. The metrics should support operational management, not vanity reporting.

## 10. MVP Scope

For the first MVP, use FakeERP/Odoo read-only data and implement only the minimum set of high-value signals.

Implement only:

- formula opportunity detector;
- stuck sales order detector;
- access issue detector placeholder;
- recommendation cards as API JSON.

The MVP should demonstrate the discovery loop, not the full end-to-end automation lifecycle. It should prove that the system can inspect connected data, surface useful opportunities, rank them, and hand them into the skill creation flow in a structured way.

## 11. Non-Goals

This layer explicitly does not aim to provide:

- exact financial ROI guarantees;
- full process mining;
- automatic activation without approval;
- write actions;
- replacement of ERP consultant judgment.

The scanner should inform decision-making, not replace it. Its role is to surface the best opportunities, explain them clearly, and make the next safe automation step obvious.

## 12. Strategic Summary

The Automation Opportunity Scanner and ROI Engine make ERP Agent OS immediately valuable after connection.

By detecting likely automation candidates, estimating business impact, and routing the best opportunities into safe skill creation, the product becomes easier to buy, easier to justify, and easier to expand. This layer is the difference between a tool that can automate and a platform that can show the business where automation will pay off.