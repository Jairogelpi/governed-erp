from __future__ import annotations

from erpguard.product.agent_intent_analyzer import analyze_intent


def test_detect_read_sales_order():
    result = analyze_intent("List all sales orders that are still in draft")
    assert result.action_type == "read"
    assert result.target_entity == "sales_order"
    assert result.confidence == "high"
    assert result.is_advisory_only is True
    assert result.can_execute is False


def test_detect_validate_formula():
    result = analyze_intent("Validate the formula for this quotation before confirming")
    assert result.action_type == "validate"
    assert result.target_entity == "sales_order"
    assert result.confidence == "high"


def test_detect_confirm_action():
    result = analyze_intent("Confirm the customer order after approval")
    assert result.action_type == "confirm"
    assert result.confidence in ("medium", "high")


def test_detect_send_invoice():
    result = analyze_intent("Send the invoice by email to the customer")
    assert result.action_type == "send"
    assert result.target_entity == "invoice"
    assert result.confidence == "high"


def test_detect_scheduled_trigger():
    result = analyze_intent("Every day at 8 AM check all draft sales orders")
    assert result.trigger_type == "scheduled"


def test_detect_event_driven_trigger():
    result = analyze_intent("When a sales order is confirmed, send an email")
    assert result.trigger_type == "event_driven"


def test_unknown_request_low_confidence():
    result = analyze_intent("do something with the thing")
    assert result.confidence == "low"
    assert result.is_advisory_only is True
    assert result.can_execute is False


def test_matched_keywords_populated():
    result = analyze_intent("Search for all invoices from last month")
    assert len(result.matched_keywords) > 0


def test_report_action():
    result = analyze_intent("Generate a summary report of all payments")
    assert result.action_type == "report"
    assert result.target_entity == "payment"
