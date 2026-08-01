# Phase 21 — Product Web Application

Operationalizes master spec §21/§22, extended to cover the Decision-to-
Outcome journey (Spec 92) that §22 predates entirely — the backend has had
no UI surface for recommendations, canary policies, outcome reports or
evidence bundles since the day they were built.

## Problem

The only web surface today is `/demo` (`apps/api/routes/demo_dashboard.py`),
an engineering dashboard built incrementally sprint-by-sprint, in Spanish
button labels grafted onto raw JSON panels. It proves the API works; it
does not tell a business story, and a new user cannot use it without
knowing endpoint names and object IDs. §Phase 21's exit criterion is
explicit: a new user must be able to go from connecting an ERP to
executing a governed action without touching YAML or IDs.

## Design

### Technology (§22.1)

React + TypeScript + Vite, a generated API client (`openapi-typescript` +
a thin fetch wrapper, generated from FastAPI's own `/openapi.json` — no
hand-maintained request/response types duplicating the Pydantic schemas
that already exist), component tests (Vitest + Testing Library), no
mandatory heavy design system. Lives at `web/`, built and served as static
assets; the FastAPI app serves them at `/` in `create_public_app`, `/demo`
remains mounted only under the existing internal-surfaces flag (§22.4).

### Navigation (§22.2, extended)

```text
Overview
Connections
Processes
Replays
Deployments
Opportunities        <- new (Spec 92 Workstream A entry point)
Recommendations       <- new
Canary                <- new (Spec 92 Workstream B)
Runs
Outcomes               <- new (Spec 92 Workstream C)
Evidence                <- extended to include Decision-to-Outcome bundles (Spec 92 Workstream D)
Benchmarks             <- Phase 20 report viewer
Settings
```

### Required screens

**Existing pillar (§22.3, unchanged):** Onboarding · Process Overview ·
Variant Explorer · Candidate Builder · Replay · Proof of Improvement ·
Skill Package · Run · Evidence.

**Decision-to-Outcome pillar (new, one screen per Spec 92 API group —
every field listed below is already returned by an existing endpoint,
this phase adds no backend work):**

- **Opportunities** — list from `GET /v1/margin-analyses/{id}/opportunities`;
  detail view shows cause, affected population, conservative/base/
  optimistic impact, confidence band, risk level; a "Create recommendation"
  action opens the Recommendation Builder pre-filled with the opportunity.
- **Recommendation Builder/Review** — create (`POST
  /v1/opportunities/{id}/recommendations`), submit, and — for a *different*
  logged-in user than the creator, enforced by the same rule the API
  already enforces — approve/reject with the content-hash-bound approval
  scope shown verbatim so an approver can see exactly what they're signing
  off on.
- **Action Draft** — pricing-scenario line editor (product/quantity/
  proposed price/cost reference/minimum margin per line), validate,
  plan-run with an optional routing-context toggle ("route through
  canary" checkbox, wired to the same `routing_context` the API accepts),
  live preflight-issue display when the API rejects it.
- **Canary** — policy list/detail/dashboard (`GET
  /v1/canary-policies/{id}/dashboard`): assigned stable/canary cases,
  success/blocked/failed counts, cumulative amount, unexpected side
  effects, estimated opportunity value, the `recommend` field
  (`continue_canary`/`pause_and_investigate`/`eligible_for_promotion`/
  `not_enough_evidence`/`abort`) rendered as an explicit advisory banner,
  never a button that auto-acts on it; routing-decision timeline; incident
  list with resolve action.
- **Outcomes** — measurement plan lifecycle (create → approve → start →
  capture follow-up → evaluate) as a stepper; realized outcome report view
  showing estimated vs. observed side by side, `result_classification`,
  and — literally, so nobody can miss it — the causal-confidence
  disclaimer text `interpretation.py` already emits
  (`observed_change_is_not_a_causal_claim`) rendered next to every
  realized-value number, not buried in a tooltip.
- **Decision Evidence** — `DecisionOutcomeEvidenceBundle` viewer: manifest
  table (resource type / id / reality label / content hash), chain status
  (`sealed`/`complete`/`incomplete` with missing-resource list), a
  "Verify" button hitting `GET .../verify` live and showing
  `stored_hashes_intact`/`live_mismatches`, and a JSON export download —
  this is the screen a thesis committee or an auditor would actually be
  shown.

### Old dashboard (§22.4)

`GET /demo` stays mounted only behind `ERPGUARD_INTERNAL_SURFACES=true`
(unchanged from today), gets a one-line banner ("legacy engineering
dashboard — see the product application"), and is excluded from any
README/demo screenshot from this phase onward.

### Copy language

Spanish business-facing copy, English identifiers/code (matches this
repo's existing convention, e.g. Spec 92's `docs/` are English while the
TFM memory is Spanish) — labels, help text and the causal-disclaimer
string above are all Spanish; API field names, component names and test
names stay English.

## Test plan

- Component tests per screen (Vitest) using the generated client against a
  mocked fetch layer — no live backend needed for these.
- `tests/test_phase21_web_build.py` — `npm run build` (or `vite build`)
  succeeds and produces the expected static asset manifest; asserted from
  Python via subprocess, same pattern the existing Docker-build CI job
  uses, so a broken frontend build fails CI the same way a broken backend
  build does.
- One Playwright E2E (`web/e2e/`) walking the exact §Phase 21 exit-criteria
  path (connect → ingest → variants → replay → proof → compile → execute)
  plus the new decision-to-outcome path (opportunity → recommendation →
  approve → canary → outcome → evidence) against a real running backend
  with the Fake connector, no live Odoo.

## Exit criteria (§Phase 21, extended)

A new user can, without touching YAML or IDs:

```text
connect -> ingest -> inspect variants -> replay candidate -> inspect proof
  -> compile -> execute
```

and, for the decision-to-outcome pillar:

```text
open an opportunity -> build a recommendation -> get it approved
  -> validate an action draft -> execute it (optionally canary-routed)
  -> see the measured outcome -> view the sealed evidence bundle
```

## Out of scope

A design system beyond what §22.1 requires (no mandatory heavy component
library) · real-time push/websocket updates (poll-on-demand is sufficient
for a TFM-scope product) · multi-language i18n beyond the Spanish/English
split already established · mobile-native apps · any new backend
capability — this phase is a pure consumer of the API surface Spec 92 and
earlier phases already shipped.
