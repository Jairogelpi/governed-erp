from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class OutcomeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ObservedMetrics(OutcomeModel):
    net_revenue: Decimal | None
    gross_margin: Decimal | None
    gross_margin_percent: Decimal | None
    currency: str | None
    metric_definition_version: str
    cost_coverage_rate: float = 1.0
