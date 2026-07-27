# Connector SDK v2 — Phase 5

Reality label: `implemented locally; FakeConnector fixture`.

`erpguard.connectors.sdk` is the framework-neutral plugin boundary. Plugins
declare metadata, authentication schemas, capabilities and read/discovery
methods. Python entry points under `erpguard.connectors` are the only registry
discovery mechanism; the repository currently publishes the `fake` plugin.

FakeConnector is deterministic and non-networking. It can test a connection,
return a stable fingerprint, describe a small fixture schema and read supplied
identifiers. Its execution plan is always non-executable and its execution
method returns a controlled block. No ERP write or raw ERP execution exists in
Phase 5.

`LegacyAdapterShim` is a deprecated read-only compatibility boundary. It does
not import Odoo or delegate generic writes. Future connectors can be published
as independent packages by exposing an `erpguard.connectors` entry point and
running the contract kit in `tests/contract/connectors`.

Not implemented in this phase: event persistence/OCEL, Odoo Connector v2,
external secret providers, capability execution, permits backed by approval
records, or arbitrary connector operations.
