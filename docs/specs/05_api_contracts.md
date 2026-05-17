# 05 API Contracts Spec

**Parent spec references:** Sections 8.1, 14, 20, 24, 26.

## Purpose

Define Phase 1 HTTP API contracts. Only backend preflight and read-style contracts are in scope.

## Create Connection

`POST /v1/connections`

```json
{
  "name": "Odoo Test",
  "erp_type": "odoo",
  "config": {
    "url": "https://example.odoo.com",
    "database": "example-db",
    "username": "user@example.com",
    "auth_type": "api_key"
  }
}
```

Response:

```json
{
  "id": "conn_001",
  "name": "Odoo Test",
  "erp_type": "odoo",
  "status": "created"
}
```

## List Connections

`GET /v1/connections`

Returns an array of connection summaries. Secret values must never be returned.

## Preflight

`POST /v1/preflight`

```json
{
  "connection_id": "conn_001",
  "actor": {
    "type": "user",
    "native_user_id": "6",
    "display_name": "Jairo"
  },
  "action": {
    "canonical_action": "confirm_sales_order",
    "canonical_object": "SalesOrder",
    "native": {
      "model": "sale.order",
      "method": "action_confirm",
      "record_id": 40
    }
  },
  "options": {
    "simulate": true,
    "allow_write": false
  }
}
```

Response:

```json
{
  "preflight_id": "pf_001",
  "decision": "block",
  "risk_level": "R3",
  "summary": "The sales order cannot be confirmed because a formula is invalid.",
  "blocking_issues": [],
  "warnings": [],
  "predicted_impact": {},
  "approval_required": false
}
```

## Audit Case

`GET /v1/audit/{case_id}`

Returns the persisted preflight case, invariant results, and audit events.

## Error Contract

```json
{
  "error": {
    "code": "mapping_error",
    "message": "Configured formula field x_sale_formula_line was not found.",
    "details": {}
  }
}
```

## Phase 1 Exclusions

- `POST /v1/execute`
- approval submission endpoints;
- explain endpoint backed by LLM;
- UI-specific endpoints.
