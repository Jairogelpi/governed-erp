from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class OdooFieldMappings(BaseModel):
    product_capacity_ml: str | None = None
    formula_sale_line_id: str | None = None
    formula_fragrance_id: str | None = None
    formula_ml_per_unit: str | None = None
    formula_ml_total: str | None = None


class OdooConnectionCreateRequest(BaseModel):
    name: str
    url: str
    database: str
    username: str
    api_key: str
    formula_model: str | None = None
    capacity_field: str | None = None
    field_mappings: OdooFieldMappings | None = None


class OdooConnectionCreateResponse(BaseModel):
    connection_id: str
    name: str
    erp_type: str
    status: str
    secrets_redacted: bool = True


class OdooConnectionTestResponse(BaseModel):
    connection_id: str
    status: str
    erp_type: str
    server_version: str | None = None
    uid: int | None = None
    read_only_mode: bool = True
    secrets_redacted: bool = True


class OdooDiagnosisSampleLimits(BaseModel):
    sales_orders: int = Field(default=5, ge=0, le=20)
    products: int = Field(default=5, ge=0, le=20)
    custom_fields: int = Field(default=50, ge=0, le=500)


class OdooDiagnosisRequest(BaseModel):
    include_samples: bool = True
    sample_limits: OdooDiagnosisSampleLimits = Field(default_factory=OdooDiagnosisSampleLimits)


class OdooWarning(BaseModel):
    code: str
    severity: str
    message: str


class OdooRawSalesOrderLine(BaseModel):
    id: int | str | None = None
    product_id: int | str | None = None
    product_name: str | None = None
    quantity: float | int | None = None
    price_unit: float | int | None = None


class OdooRawSalesOrderSummaryOrder(BaseModel):
    id: int | str | None = None
    name: str | None = None
    state: str | None = None
    partner: str | None = None
    amount_total: float | int | None = None
    line_count: int | None = None


class OdooRawSalesOrderSummaryResponse(BaseModel):
    connection_id: str
    order_reference: str
    status: str
    read_only_mode: bool = True
    order: OdooRawSalesOrderSummaryOrder
    lines: list[OdooRawSalesOrderLine]
    secrets_redacted: bool = True


class OdooDiagnosisResponse(BaseModel):
    connection_id: str
    status: str
    read_only_mode: bool = True
    odoo: dict[str, Any]
    modules: dict[str, bool]
    models: dict[str, Any]
    fields: dict[str, Any]
    samples: dict[str, Any]
    detected: dict[str, Any]
    warnings: list[OdooWarning]
    next_recommended_action: str
    secrets_redacted: bool = True
