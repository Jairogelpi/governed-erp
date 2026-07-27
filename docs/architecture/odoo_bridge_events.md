# Odoo bridge and event ingestion — Phase 8

Reality label: `implemented locally; controlled bridge payloads`.

The bridge boundary accepts validated, read-origin Odoo event payloads and
normalizes them into the Phase 6 canonical OCEL-shaped store. Event keys are
prefixed with `odoo:` and are tenant-scoped, so webhook retries are
idempotent. Correlation IDs are preserved or deterministically derived from
the source event ID. Historical and synthetic labels are mutually exclusive
and are retained in event attributes. Credential-like fields are removed from
event values before persistence.

Controlled endpoints:

- `POST /v1/events/odoo/webhook` ingests one bridge event;
- `POST /v1/events/odoo/poll` ingests a supplied batch and advances the Odoo
  event cursor only after processing the batch.

These endpoints are authenticated through the Phase 3 identity boundary. The
poll endpoint is a controlled ingestion seam, not a network poller. A real
Odoo addon/webhook transport, background polling worker and live staging
integration remain pending work. No write-like event is accepted and no ERP
write or raw ERP execution is added.
