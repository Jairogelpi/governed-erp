# Phase 11.5 Wave C2 — Connector Convergence

Status: implemented as a bounded SDK v2 connection boundary. Legacy connector
setup/auth/credential routes remain available only through the explicit legacy
application and are not part of the default public app.

## Convergence contract

The public connector surface is now backed by the SDK v2 entry-point registry
and `ConnectorRuntime`:

```text
public connector route
  → ConnectorApplicationService
  → tenant-scoped UnifiedConnection
  → ConnectorContext(credential_ref=...)
  → ConnectorRuntime
  → SDK v2 plugin
```

The public surface is:

```text
GET  /v1/connectors
GET  /v1/connectors/{connector_id}
POST /v1/connectors/{connector_id}/test
```

Connector definitions are read from the discovered SDK v2 plugins. A unified
connection can only be created for a connector present in that registry;
unknown connector identifiers are rejected with `connector_not_found`.

## Safety and tenancy

- Connection lookup always filters by both `tenant_id` and `connection_id`.
- The connector in the URL must match `UnifiedConnection.connector_type`.
- Runtime contexts carry `credential_ref`, endpoint and non-secret metadata;
  raw secret material is not passed into the plugin.
- The connection-test boundary does not create an ERP write plan or execute an
  ERP operation. Odoo remains read-only and requires its injected transport
  seam for a live test.
- The old `/v1/connector-setup`, `/v1/connector-auth`,
  `/v1/connector-credentials` and `/v1/unified/connections` route graph is not
  mounted by the default public application.

## Verification

```text
python -m pytest tests/test_phase115_connector_convergence.py -q
python -m pytest tests/test_phase115_consolidation_inventory.py tests/test_phase115_composition_root.py -q
python -m pytest tests/test_connector_sdk_models.py tests/test_connector_sdk_registry.py tests/test_odoo_connector_v2.py -q
```

The focused C2, composition, inventory and SDK/Odoo slices are the relevant
verification for this wave. Full repository regression is intentionally left
to the later consolidation gate and was not run in this continuation.

No connector deletion, replay, candidate activation, autonomous ERP
execution, or ERP write capability was added.
