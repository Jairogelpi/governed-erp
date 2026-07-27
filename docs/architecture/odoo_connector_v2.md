# Odoo Connector v2 read path — Phase 7

Reality label: `implemented locally; staging integration pending`.

The `odoo` entry point now exposes an SDK v2 plugin with read-only metadata,
customer/product/quote reads, schema discovery, permissions capability
declaration, and stable fingerprinting. It supports two transport seams:

- `LegacyXmlRpcReadTransport`, wrapping the existing allowlisted XML-RPC client;
- `Json2ReadTransport`, allowing a JSON-2 caller to be injected without
  coupling the plugin to HTTP or storing raw credentials.

The plugin accepts only a `credential_ref` in `ConnectorContext`; callers must
resolve credentials outside the plugin. All write-like capabilities, event
pulling and execution remain blocked. The live Odoo smoke is intentionally not
run in this local validation; staging credentials and network access are still
required.

Phase 8 remains responsible for bridge/event ingestion. No ERP write or raw
ERP execution is part of this connector.
