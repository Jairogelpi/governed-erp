# Variant discovery — Phase 10

Reality label: `implemented locally; canonical event fixture driven`.

Variant discovery projects tenant-scoped canonical events into case traces by
canonical object, normalizes event names, groups equal sequences, and computes
case counts and elapsed duration. The API exposes variant summaries and a
selected case trace:

- `GET /v1/variants?object_type=sale_order`;
- `GET /v1/variants/cases/{case_id}`;
- `GET /v1/variants/dashboard`.

The first dashboard is intentionally a small read-only HTML surface. It does
not create candidates, alter processes, replay data or execute ERP actions.
Variant discovery uses existing canonical events; real Odoo staging data is
not required for the local fixture tests.
