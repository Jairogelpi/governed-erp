from __future__ import annotations

from erpguard.product.agent_process_classifier import classify_process


def test_sales_cycle_classification():
    result = classify_process("confirm", "sales_order")
    assert result.process_category == "sales_cycle"
    assert result.confidence in ("medium", "high")


def test_accounting_cycle_classification():
    result = classify_process("validate", "invoice")
    assert result.process_category == "accounting_cycle"


def test_inventory_management_classification():
    result = classify_process("read", "inventory")
    assert result.process_category == "inventory_management"


def test_purchase_cycle_classification():
    result = classify_process("create", "purchase_order")
    assert result.process_category == "purchase_cycle"


def test_reporting_classification():
    result = classify_process("report", "sales_order")
    assert result.process_category in ("reporting", "sales_cycle")


def test_unknown_falls_back_to_general():
    result = classify_process("unknown", "unknown")
    assert result.process_category == "general"
    assert result.confidence == "low"


def test_candidate_categories_populated():
    result = classify_process("confirm", "sales_order")
    assert len(result.candidate_categories) >= 1
