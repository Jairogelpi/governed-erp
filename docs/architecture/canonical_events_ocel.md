# Canonical events and OCEL — Phase 6

Reality label: `implemented locally; FakeConnector-generated fixture data`.

Phase 6 adds tenant-scoped canonical objects, canonical events and ingestion
cursors. OCEL 2-shaped JSON can be imported into those tables and exported
again. The event key is unique within a tenant, so importing the same batch
twice creates no duplicate event or object rows. Cursors are scoped by tenant,
connector and stream.

The API is protected by the Phase 3 identity boundary:

- `POST /v1/events/ocel/import` — operator/admin import;
- `GET /v1/events/ocel/export` — viewer/admin export;
- `POST /v1/events/fake-generate` — deterministic local fixture generator;
- `PUT/GET /v1/events/cursors` — tenant-scoped cursor storage.

No Odoo transport, event webhook, polling worker, OCEL persistence from a real
ERP, raw ERP execution or ERP write is included. Real connector ingestion is
Phase 8 work; Odoo read transport remains Phase 7.
