from __future__ import annotations

from erpguard.product.agent_risk_summary import summarize_risk


def test_read_is_low_risk():
    result = summarize_risk("read", "sales_order")
    assert result.overall_risk_level == "low"
    assert result.reversible is True
    assert result.requires_write_pilot is False
    assert result.requires_approval is False


def test_confirm_is_high_risk():
    result = summarize_risk("confirm", "sales_order")
    assert result.overall_risk_level == "high"
    assert result.reversible is False
    assert result.requires_write_pilot is True
    assert result.requires_approval is True


def test_delete_is_high_risk_and_irreversible():
    result = summarize_risk("delete", "partner")
    assert result.overall_risk_level == "high"
    assert result.reversible is False
    assert "not reversible" in " ".join(result.risk_factors).lower()


def test_invoice_adds_financial_risk_factor():
    result = summarize_risk("confirm", "invoice")
    factor_text = " ".join(result.risk_factors).lower()
    assert "financial" in factor_text


def test_advisory_invariants():
    result = summarize_risk("validate", "sales_order")
    assert result.safe_for_advisory_only is True
    assert result.can_execute_in_advisory_mode is False


def test_write_steps_adds_risk_factor():
    result = summarize_risk("update", "product", has_write_steps=True)
    factor_text = " ".join(result.risk_factors)
    assert "write steps" in factor_text
