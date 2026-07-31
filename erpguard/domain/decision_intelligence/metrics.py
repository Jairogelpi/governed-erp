from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Callable

from erpguard.domain.decision_intelligence.types import (
    AnalyticalLine,
    DataQualityResult,
    MetricValue,
    PeriodMetrics,
    SegmentMetric,
)


ZERO = Decimal("0")
HUNDRED = Decimal("100")


METRIC_DEFINITIONS = {
    "gross_revenue": "Signed pre-discount invoice-line revenue, excluding tax; refunds reduce revenue.",
    "net_revenue": "Posted customer invoice-line subtotal excluding tax, with refunds signed negative.",
    "refunds": "Absolute posted customer-refund subtotal excluding tax.",
    "cost_of_sales": "Signed quantity multiplied by the declared per-line cost source; refunds reverse cost.",
    "gross_margin": "Net revenue minus cost of sales.",
    "gross_margin_percent": "Gross margin divided by net revenue.",
    "effective_discount": "Signed gross revenue minus signed net revenue.",
    "effective_discount_percent": "Effective discount divided by signed gross revenue.",
    "units": "Signed absolute invoiced quantity; refunds reduce units.",
    "average_price": "Net revenue divided by signed units.",
    "revenue_per_customer": "Net revenue divided by distinct invoiced customers.",
}


def _in_period(line: AnalyticalLine, start: str, end: str) -> bool:
    value = date.fromisoformat(line.invoice_date)
    return date.fromisoformat(start) <= value <= date.fromisoformat(end)


def _sign(line: AnalyticalLine) -> Decimal:
    return Decimal("-1") if line.move_type == "out_refund" else Decimal("1")


def gross(line: AnalyticalLine) -> Decimal:
    return _sign(line) * line.quantity * line.price_unit


def net(line: AnalyticalLine) -> Decimal:
    return _sign(line) * line.price_subtotal


def units(line: AnalyticalLine) -> Decimal:
    return _sign(line) * line.quantity


def cost(line: AnalyticalLine) -> Decimal | None:
    if line.cost.unit_cost is None:
        return None
    return _sign(line) * line.quantity * line.cost.unit_cost


def margin(line: AnalyticalLine) -> Decimal | None:
    line_cost = cost(line)
    return net(line) - line_cost if line_cost is not None else None


def _metric(
    name: str,
    value: Decimal | None,
    *,
    start: str,
    end: str,
    unit: str,
    quality: DataQualityResult,
    cost_metric: bool = False,
) -> MetricValue:
    coverage = quality.cost_coverage_rate if cost_metric else quality.revenue_coverage_rate
    warnings = quality.warnings if cost_metric else []
    return MetricValue(
        metric=name,
        value=value,
        unit=unit,
        definition=METRIC_DEFINITIONS[name],
        filters={
            "period_start": start,
            "period_end": end,
            "move_state": "posted",
            "move_types": ["out_invoice", "out_refund"],
            "taxes": "excluded",
        },
        sources=["account.move", "account.move.line"],
        coverage_rate=coverage,
        warnings=warnings,
    )


def _segments(
    lines: list[AnalyticalLine],
    key: Callable[[AnalyticalLine], tuple[str, str] | None],
) -> list[SegmentMetric]:
    grouped: dict[tuple[str, str], list[AnalyticalLine]] = defaultdict(list)
    for line in lines:
        segment = key(line)
        if segment is not None:
            grouped[segment].append(line)
    results: list[SegmentMetric] = []
    for (segment_id, segment_name), segment_lines in grouped.items():
        revenue = sum((net(line) for line in segment_lines), ZERO)
        costs = [cost(line) for line in segment_lines]
        complete = all(item is not None for item in costs)
        total_cost = sum((item for item in costs if item is not None), ZERO) if complete else None
        gross_margin = revenue - total_cost if total_cost is not None else None
        margin_percent = (
            gross_margin / revenue * HUNDRED if gross_margin is not None and revenue else None
        )
        results.append(
            SegmentMetric(
                segment_id=segment_id,
                segment_name=segment_name,
                net_revenue=revenue,
                cost_of_sales=total_cost,
                gross_margin=gross_margin,
                gross_margin_percent=margin_percent,
            )
        )
    return sorted(
        results,
        key=lambda item: (
            item.gross_margin if item.gross_margin is not None else Decimal("Infinity"),
            item.segment_name,
        ),
    )


def calculate_period_metrics(
    lines: list[AnalyticalLine],
    *,
    start: str,
    end: str,
    quality: DataQualityResult,
    allow_margin: bool,
) -> PeriodMetrics:
    scoped = [line for line in lines if _in_period(line, start, end)]
    gross_revenue = sum((gross(line) for line in scoped), ZERO)
    net_revenue = sum((net(line) for line in scoped), ZERO)
    refunds = abs(
        sum(
            (net(line) for line in scoped if line.move_type == "out_refund"),
            ZERO,
        )
    )
    total_units = sum((units(line) for line in scoped), ZERO)
    discount = gross_revenue - net_revenue
    customer_count = len({line.partner_id for line in scoped})
    total_cost: Decimal | None
    gross_margin: Decimal | None
    gross_margin_percent: Decimal | None
    if allow_margin:
        total_cost = sum((cost(line) or ZERO for line in scoped), ZERO)
        gross_margin = net_revenue - total_cost
        gross_margin_percent = gross_margin / net_revenue * HUNDRED if net_revenue else None
    else:
        total_cost = gross_margin = gross_margin_percent = None
    values = {
        "gross_revenue": _metric(
            "gross_revenue", gross_revenue, start=start, end=end, unit="currency", quality=quality
        ),
        "net_revenue": _metric(
            "net_revenue", net_revenue, start=start, end=end, unit="currency", quality=quality
        ),
        "refunds": _metric(
            "refunds", refunds, start=start, end=end, unit="currency", quality=quality
        ),
        "cost_of_sales": _metric(
            "cost_of_sales",
            total_cost,
            start=start,
            end=end,
            unit="currency",
            quality=quality,
            cost_metric=True,
        ),
        "gross_margin": _metric(
            "gross_margin",
            gross_margin,
            start=start,
            end=end,
            unit="currency",
            quality=quality,
            cost_metric=True,
        ),
        "gross_margin_percent": _metric(
            "gross_margin_percent",
            gross_margin_percent,
            start=start,
            end=end,
            unit="percent",
            quality=quality,
            cost_metric=True,
        ),
        "effective_discount": _metric(
            "effective_discount", discount, start=start, end=end, unit="currency", quality=quality
        ),
        "effective_discount_percent": _metric(
            "effective_discount_percent",
            discount / gross_revenue * HUNDRED if gross_revenue else None,
            start=start,
            end=end,
            unit="percent",
            quality=quality,
        ),
        "units": _metric("units", total_units, start=start, end=end, unit="units", quality=quality),
        "average_price": _metric(
            "average_price",
            net_revenue / total_units if total_units else None,
            start=start,
            end=end,
            unit="currency_per_unit",
            quality=quality,
        ),
        "revenue_per_customer": _metric(
            "revenue_per_customer",
            net_revenue / customer_count if customer_count else None,
            start=start,
            end=end,
            unit="currency_per_customer",
            quality=quality,
        ),
    }
    return PeriodMetrics(
        period_start=start,
        period_end=end,
        values=values,
        products=_segments(
            scoped,
            lambda line: (
                (str(line.product_id), line.product_name or str(line.product_id))
                if line.product_id is not None
                else None
            ),
        ),
        customers=_segments(
            scoped,
            lambda line: (str(line.partner_id), line.partner_name),
        ),
    )
