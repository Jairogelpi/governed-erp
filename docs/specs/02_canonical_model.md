# 02 Canonical Model Spec

**Parent spec references:** Sections 8.5, 9, 20.2, 20.3, 22, 23, 26.

## Purpose

Define the vendor-neutral data structures used by ERPGuard Phase 1. Native Odoo records must be converted into these models before policy evaluation.

## Phase 1 Models

### Company

```yaml
Company:
  id: string
  native_id: string
  name: string
  currency: string | null
  native_metadata: object
```

### Customer

```yaml
Customer:
  id: string
  native_id: string
  name: string
  email: string | null
  active: boolean
  native_metadata: object
```

### Product

```yaml
Product:
  id: string
  native_id: string
  sku: string | null
  name: string
  active: boolean
  type: enum[stockable, consumable, service, digital, unknown]
  tracking: enum[none, lot, serial, unknown]
  category: string | null
  cost: decimal | null
  sale_price: decimal | null
  uom: string | null
  routes: list[string]
  bom_ids: list[string]
  capacity_ml: decimal | null
  custom_attributes: object
  native_metadata: object
```

### SalesOrderLine

```yaml
SalesOrderLine:
  id: string
  native_id: string
  product: Product
  quantity: decimal
  uom: string | null
  unit_price: decimal
  subtotal: decimal
  tax_ids: list[string]
  route_policy: enum[stock, make_to_order, manufacture, dropship, unknown]
  formula: FormulaSpec | null
  custom_attributes: object
  native_metadata: object
```

### FormulaSpec

Phase 1 introduces this supporting object for Formula Guard.

```yaml
FormulaSpec:
  exists: boolean
  ml_per_unit: decimal | null
  total_ml: decimal | null
  components: list[FormulaComponent]
```

### FormulaComponent

```yaml
FormulaComponent:
  name: string
  product_native_id: string | null
  ml: decimal
```

### SalesOrder

```yaml
SalesOrder:
  id: string
  native_id: string
  reference: string
  company: Company | null
  customer: Customer | null
  state: enum[draft, sent, confirmed, done, cancelled, unknown]
  order_date: datetime | null
  currency: string | null
  total_amount: decimal
  untaxed_amount: decimal | null
  tax_amount: decimal | null
  lines: list[SalesOrderLine]
  invoice_policy: enum[ordered, delivered, milestone, unknown]
  warehouse: object | null
  native_metadata: object
```

## Mapping Requirements

- Preserve native IDs for auditability.
- Preserve unknown or custom fields under `native_metadata` or `custom_attributes`.
- Use `unknown` enum values instead of failing when non-critical native values are unfamiliar.
- Fail closed when required fields for a policy are missing.

## Validation Requirements

- Monetary and quantity values use decimals, not floats.
- Every line must include a product.
- A sales order may have `customer = null`, but `customer_exists` must then fail.
- Formula fields may be absent; Formula Guard decides whether absence is blocking.
