# Phase 16.5 — Decision Intelligence Foundation

## Outcome

Phase 16.5 replaces the legacy module/field opportunity scanner as the source
of economic truth. It extracts a bounded, read-only analytical dataset from
Odoo, seals it as an immutable snapshot, evaluates data quality before making
margin claims and computes versioned period metrics and an exact margin
bridge.

This phase does not create recommendations and does not write to Odoo.

## Read-only extraction

The first vertical reads:

- posted customer invoices and refunds;
- invoice lines;
- sales orders and lines for source completeness;
- products and customers;
- company and currency metadata;
- stock valuation layers where available.

Only `version`, `authenticate`, `fields_get`, `search_count` and
`search_read` are reachable through the injected Odoo read transport.
`account.move` and `account.move.line` are required sources. Sales,
master-data and valuation sources are optional, but their availability and
missing fields remain visible in the extraction manifest.

Every model read is bounded. A truncated extraction is retained as evidence
but blocks analytical conclusions.

## Immutable analytical snapshot

`AnalyticalSnapshot` stores:

- tenant, connection and company scope;
- current and comparison periods;
- source models, requested/available fields and domains;
- source and retrieved row counts;
- bounded source rows and canonical analytical lines;
- currency and cost provenance;
- source hash and metric-definition version;
- creation actor and timestamp.

Snapshots, quality reports and analyses reject update and delete operations.
The raw extraction payload is not returned by the public API.

## Cost truth

Cost evidence is explicit per invoice line:

1. the latest `stock.valuation.layer` at or before the invoice date is
   preferred and labelled `high` reliability;
2. current `standard_price` is a disclosed `low`-reliability fallback and is
   never represented as historical cost;
3. absence of both is labelled `missing`.

Cost coverage is revenue-weighted. If it falls below the requested threshold,
revenue remains available but cost of sales, gross margin and the margin
bridge are blocked.

## Data Quality Gate

The versioned report checks:

- duplicate invoice-line grain;
- posted invoice/refund scope;
- currency consistency;
- revenue-field coverage;
- cost coverage and historical reliability;
- refund reversal reconciliation;
- product-link coverage;
- extreme quantities and prices;
- possible duplicate customer identities;
- required-field availability;
- extraction truncation.

The result includes checks, errors, warnings, coverage rates, confidence grade
and explicit blocking issues. Mixed currencies block aggregation until a
versioned conversion layer exists.

## Canonical metrics

Metric version `margin-truth/1.0.0` defines:

- gross and net revenue;
- refunds;
- cost of sales;
- gross margin and gross margin percent;
- effective discount and percent;
- units and average price;
- revenue per customer;
- product and customer margin segments.

Every metric carries its definition, version, filters, sources, unit,
coverage and relevant warnings.

## Margin bridge

The comparison decomposes the change from prior to current gross margin into:

```text
previous margin
+ volume effect
+ price effect
+ mix effect
+ discount effect
+ cost effect
+ refund effect
= current margin
```

The implementation is deterministic. Mix is the explicit residual economic
effect after the directly measured components, and the final residual must be
within the requested tolerance.

## API

```text
POST /v1/decision-intelligence/snapshots
GET  /v1/decision-intelligence/snapshots/{snapshot_id}
POST /v1/decision-intelligence/snapshots/{snapshot_id}/margin-analysis
GET  /v1/decision-intelligence/analyses/{analysis_id}
```

Repeated analysis of the same immutable snapshot returns the same persisted
analysis and content hash.

## Persistence

Migration `0019_decision_intelligence` creates:

- `analytical_snapshots`;
- `analytical_data_quality_reports`;
- `margin_analyses`.

## Demonstrated fixture

The sanitized evidence in
[`docs/demo/phase16_5_decision_intelligence_evidence.json`](../demo/phase16_5_decision_intelligence_evidence.json)
freezes:

```text
read-only Odoo extraction
→ immutable snapshot
→ cost coverage = 100%
→ comparison margin = 270 EUR
→ current margin = 588 EUR
→ bridge residual = 0
→ repeated analysis returns identical evidence
→ ERP writes = 0
```

It also freezes the fail-closed path: missing costs leave net revenue visible
while gross margin and the bridge remain unavailable.

## Exit criteria

- real Odoo-facing extraction uses only the read transport;
- exact source rows, manifest, scope and hash are persisted;
- refunds reduce revenue and reverse cost;
- cost source and reliability are explicit;
- insufficient coverage blocks margin claims;
- metric definitions are versioned and self-describing;
- product and customer drivers are returned;
- the bridge balances inside a declared tolerance;
- evidence is tenant-scoped, immutable and reproducible;
- no ERP write, recommendation or execution authority is added.
