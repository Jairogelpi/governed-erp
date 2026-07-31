from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from erpguard.domain.decision_intelligence.metrics import cost, gross, margin, net
from erpguard.domain.decision_intelligence.types import AnalyticalLine, MarginBridgeResult


ZERO = Decimal("0")


def _scope(lines: list[AnalyticalLine], start: str, end: str) -> list[AnalyticalLine]:
    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)
    return [
        line for line in lines if start_date <= date.fromisoformat(line.invoice_date) <= end_date
    ]


def _product_rates(
    lines: list[AnalyticalLine],
) -> dict[int, tuple[Decimal, Decimal, Decimal]]:
    grouped: dict[int, list[AnalyticalLine]] = defaultdict(list)
    for line in lines:
        if line.product_id is not None and line.move_type == "out_invoice":
            grouped[line.product_id].append(line)
    result: dict[int, tuple[Decimal, Decimal, Decimal]] = {}
    for product_id, product_lines in grouped.items():
        quantity = sum((abs(line.quantity) for line in product_lines), ZERO)
        if not quantity:
            continue
        list_price = sum((gross(line) for line in product_lines), ZERO) / quantity
        net_price = sum((net(line) for line in product_lines), ZERO) / quantity
        unit_cost = sum((cost(line) or ZERO for line in product_lines), ZERO) / quantity
        result[product_id] = (list_price, net_price, unit_cost)
    return result


def calculate_margin_bridge(
    lines: list[AnalyticalLine],
    *,
    comparison_start: str,
    comparison_end: str,
    current_start: str,
    current_end: str,
    tolerance: Decimal = Decimal("0.01"),
) -> MarginBridgeResult:
    previous = _scope(lines, comparison_start, comparison_end)
    current = _scope(lines, current_start, current_end)
    previous_margin = sum((margin(line) or ZERO for line in previous), ZERO)
    current_margin = sum((margin(line) or ZERO for line in current), ZERO)

    previous_sales = [line for line in previous if line.move_type == "out_invoice"]
    current_sales = [line for line in current if line.move_type == "out_invoice"]
    previous_rates = _product_rates(previous_sales)
    current_rates = _product_rates(current_sales)
    previous_quantity = sum((abs(line.quantity) for line in previous_sales), ZERO)
    current_quantity = sum((abs(line.quantity) for line in current_sales), ZERO)
    previous_sales_margin = sum((margin(line) or ZERO for line in previous_sales), ZERO)
    base_margin_per_unit = previous_sales_margin / previous_quantity if previous_quantity else ZERO
    volume_effect = (current_quantity - previous_quantity) * base_margin_per_unit

    current_quantity_by_product: dict[int, Decimal] = defaultdict(lambda: ZERO)
    for line in current_sales:
        if line.product_id is not None:
            current_quantity_by_product[line.product_id] += abs(line.quantity)
    price_effect = discount_effect = cost_effect = ZERO
    for product_id, quantity in current_quantity_by_product.items():
        current_list, current_net, current_cost = current_rates[product_id]
        base_list, base_net, base_cost = previous_rates.get(
            product_id,
            (current_list, current_net, current_cost),
        )
        price_effect += quantity * (current_list - base_list)
        discount_effect += quantity * ((current_net - current_list) - (base_net - base_list))
        cost_effect -= quantity * (current_cost - base_cost)

    previous_refund_margin = sum(
        (margin(line) or ZERO for line in previous if line.move_type == "out_refund"),
        ZERO,
    )
    current_refund_margin = sum(
        (margin(line) or ZERO for line in current if line.move_type == "out_refund"),
        ZERO,
    )
    refund_effect = current_refund_margin - previous_refund_margin
    delta = current_margin - previous_margin
    mix_effect = delta - (
        volume_effect + price_effect + discount_effect + cost_effect + refund_effect
    )
    explained = previous_margin + sum(
        (
            volume_effect,
            price_effect,
            mix_effect,
            discount_effect,
            cost_effect,
            refund_effect,
        ),
        ZERO,
    )
    residual = current_margin - explained
    return MarginBridgeResult(
        previous_margin=previous_margin,
        price_effect=price_effect,
        volume_effect=volume_effect,
        mix_effect=mix_effect,
        discount_effect=discount_effect,
        cost_effect=cost_effect,
        refund_effect=refund_effect,
        current_margin=current_margin,
        explained_margin=explained,
        residual=residual,
        tolerance=tolerance,
        balanced=abs(residual) <= tolerance,
    )
