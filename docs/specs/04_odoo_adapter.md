# 04 Odoo Adapter Spec

**Parent spec references:** Sections 8.4, 8.5, 18, 20, 22, 26, 30.

## Purpose

Define the Odoo adapter boundary for ERPGuard Phase 1. The adapter reads Odoo state and maps it into canonical models. Phase 1 must not execute final write actions.

## Adapter Interface

```python
class ERPAdapter:
    def connect(self) -> None: ...
    def healthcheck(self) -> dict: ...
    def get_sales_order(self, native_id: int) -> SalesOrder: ...
```

## Odoo Adapter Minimum Methods

```python
class OdooAdapter(ERPAdapter):
    def connect(self) -> None: ...
    def inspect_model(self, model: str) -> dict: ...
    def inspect_fields(self, model: str) -> dict: ...
    def search_read(self, model: str, domain: list, fields: list) -> list[dict]: ...
    def read(self, model: str, ids: list[int], fields: list[str]) -> list[dict]: ...
    def get_sales_order(self, native_id: int) -> SalesOrder: ...
```

## Phase 1 Odoo Models

- `sale.order`
- `sale.order.line`
- `product.product`
- `product.template`
- `res.partner`
- `res.company`
- custom formula models or custom formula fields when configured

## Formula Mapping

Formula fields are installation-specific. Phase 1 must support configurable field names:

```yaml
formula_mapping:
  line_formula_field: x_sale_formula_line
  product_capacity_field: x_capacity_ml
  formula_total_field: x_formula_total_ml
  formula_ml_per_unit_field: x_formula_ml_per_unit
```

If required configured fields are absent, Formula Guard should return `needs_more_context` or blocking failures depending on policy severity.

## Error Handling

- Connection failure: `adapter_connection_error`.
- Missing record: `not_found`.
- Missing configured field: `mapping_error`.
- Unsupported Odoo version or model: `unsupported`.

## Testing Approach

Core tests use fake adapters and fixture payloads. Live Odoo tests are optional integration tests and must not be required for local unit test success.
