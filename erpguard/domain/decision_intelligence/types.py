from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


METRIC_DEFINITION_VERSION = "margin-truth/1.0.0"


class AnalyticalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CostEvidence(AnalyticalModel):
    source: Literal[
        "stock_valuation_layer",
        "current_standard_price",
        "missing",
    ]
    reliability: Literal["high", "low", "none"]
    unit_cost: Decimal | None = None
    as_of: str | None = None
    warning: str | None = None


class AnalyticalLine(AnalyticalModel):
    invoice_line_id: int
    move_id: int
    move_type: Literal["out_invoice", "out_refund"]
    move_state: str
    invoice_date: str
    company_id: int
    company_name: str
    currency_id: int
    currency: str
    partner_id: int
    partner_name: str
    product_id: int | None = None
    product_name: str | None = None
    quantity: Decimal
    price_unit: Decimal
    discount_percent: Decimal = Decimal("0")
    price_subtotal: Decimal
    reversed_entry_id: int | None = None
    cost: CostEvidence


class ExtractionDataset(AnalyticalModel):
    lines: list[AnalyticalLine]
    source_rows: dict[str, list[dict[str, Any]]]
    manifest: dict[str, Any]
    row_counts: dict[str, int]
    currency: str | None


class QualityCheck(AnalyticalModel):
    code: str
    dimension: Literal[
        "completeness",
        "uniqueness",
        "validity",
        "consistency",
        "integrity",
        "timeliness",
        "volume",
    ]
    severity: Literal["critical", "high", "medium", "low"]
    status: Literal["passed", "warning", "failed"]
    affected_count: int = 0
    affected_rate: float = 0.0
    message: str


class DataQualityResult(AnalyticalModel):
    checks: list[QualityCheck]
    errors: list[str]
    warnings: list[str]
    cost_coverage_rate: float
    revenue_coverage_rate: float
    duplicate_rate: float
    refund_reconciliation_rate: float
    confidence_grade: Literal["A", "B", "C", "blocked"]
    blocking_issues: list[str]


class MetricValue(AnalyticalModel):
    metric: str
    value: Decimal | None
    unit: str
    definition: str
    definition_version: str = METRIC_DEFINITION_VERSION
    filters: dict[str, Any]
    sources: list[str]
    coverage_rate: float
    warnings: list[str] = Field(default_factory=list)


class SegmentMetric(AnalyticalModel):
    segment_id: str
    segment_name: str
    net_revenue: Decimal
    cost_of_sales: Decimal | None
    gross_margin: Decimal | None
    gross_margin_percent: Decimal | None


class PeriodMetrics(AnalyticalModel):
    period_start: str
    period_end: str
    values: dict[str, MetricValue]
    products: list[SegmentMetric]
    customers: list[SegmentMetric]


class MarginBridgeResult(AnalyticalModel):
    previous_margin: Decimal
    price_effect: Decimal
    volume_effect: Decimal
    mix_effect: Decimal
    discount_effect: Decimal
    cost_effect: Decimal
    refund_effect: Decimal
    current_margin: Decimal
    explained_margin: Decimal
    residual: Decimal
    tolerance: Decimal
    balanced: bool
