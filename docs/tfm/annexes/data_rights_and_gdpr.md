# Data rights and GDPR analysis (Spec 95 Sec 39.2)

This is an honest inventory of what personal data actually flows through
this codebase, written from reading the code, not from a compliance
template. It is a TFM annex, not a legal opinion -- if this project is
ever deployed against a real tenant's live ERP data, get an actual legal
review before doing so; nothing here substitutes for one.

## What personal data this system touches, and where

| Data | Where | Reality label |
| --- | --- | --- |
| Operator/user email + display name (`IdentityUser`) | `erpguard/db/model_packages/identity.py` | `real` -- test/demo accounts and this repository's own contributors only; no production user base exists. |
| Odoo customer names, order references | Bounded reads via `erpguard/adapters/odoo/*` and the analytical extraction pipeline (`erpguard/application/decision_intelligence/extraction_service.py`) | `staging_only` -- only reachable with an explicitly configured staging connection; the two live Odoo write tests performed this session touched one real third-party customer's staging record. |
| Synthetic/Fake customer and product names | `erpguard/connectors/fake/`, `erpguard/benchmark/fake_erp_store.py`, `erpguard/domain/events/fake_generator.py` | `fixture` -- fabricated, no relation to any real person. |

## The one real customer-name exposure this session, and how it was handled

`docs/demo/backend_rc_live_pricing_scenario_evidence.json` records two
live writes against a real, authorized Odoo 19 staging instance
(`esenssi-aromas-staging-...`). The evidence originally captured the real
staging customer's name; before committing it to this public repository,
the customer name was redacted at the user's explicit instruction (a
`[redacted]`-style placeholder replaces it; the order references and
other structural evidence were kept, since they don't identify anyone).
No credentials (the Odoo password, connection strings) were ever written
to any committed file -- verified by direct inspection before commit, not
assumed.

## Data subject categories

1. **Operators/testers** (`IdentityUser` rows): email + display name,
   created via `POST /internal/dev-tokens` or test fixtures. These are
   test/demo identities, not a real user base; there is no signup flow,
   no password, no way for an actual member of the public to create an
   account today (`issue_token()`'s own docstring: "never from a public
   route").
2. **Staging ERP customers** (Odoo-side, read-only except for the two
   authorized pricing-scenario draft writes): real names/references
   exist only in the connected staging tenant and in the one redacted
   evidence file above -- never in synthetic fixtures, never in the
   ERPRiskBench dataset (`erpguard/benchmark/dataset_generator.py`
   generates purely synthetic customer/product data, seeded
   deterministically, no relation to any real entity).

## Rights and retention

- **Right to erasure / rectification**: not implemented as a product
  feature. `GovernedRecommendation`, `DecisionOutcomeEvidenceBundle` and
  `ExecutionRun` rows are deliberately append-only/sealed-immutable by
  design (tamper-evidence is the point) -- an erasure request against a
  sealed evidence bundle would require a deliberate, audited
  redaction-and-reseal operation this codebase does not currently offer.
  This is a real gap for any future production deployment, not
  something this TFM scope claims to solve.
- **Data minimization**: the analytical snapshot pipeline
  (`erpguard/domain/decision_intelligence/`) reads only the specific
  Odoo fields its metric definitions need (`margin-truth/1.0.0`), not a
  blanket export; extraction manifests record exactly which
  models/fields were read (`docs/architecture/current_inventory.md`).
- **Retention**: no automatic deletion/expiry job exists for any table.
  For a TFM-scope, non-production system operating on test/staging data
  only, this is accepted as a known limitation, not silently ignored.

## Conclusion

This system, as it exists at the end of Phase 22, processes real
personal data in exactly one narrow, explicitly authorized, already-
redacted-where-necessary case (the staging Odoo customer above), and
otherwise operates entirely on synthetic Fake ERP data or the
repository's own test/demo identities. It does not have (and does not
claim to have) production-grade GDPR tooling -- erasure, consent
management, data-subject-access-request handling, or retention policies
are all absent. Any future step from "TFM research prototype" to
"handles a real customer's live ERP data in production" would need all
of the above before it could honestly be called compliant.
