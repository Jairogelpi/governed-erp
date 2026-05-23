from __future__ import annotations

from erpguard.product.agent_workflow_proposal import propose_workflow


def test_read_sales_order_workflow():
    result = propose_workflow("read", "sales_order", "manual")
    assert result.can_execute is False
    assert result.runtime_mode == "advisory_only"
    assert len(result.steps) >= 2
    assert all(s.can_execute is False for s in result.steps)


def test_validate_sales_order_has_guard_step():
    result = propose_workflow("validate", "sales_order", "manual")
    step_types = [s.step_type for s in result.steps]
    assert "run_guard" in step_types


def test_confirm_sales_order_requires_approval():
    result = propose_workflow("confirm", "sales_order", "manual")
    step_types = [s.step_type for s in result.steps]
    assert "request_approval" in step_types


def test_update_entity_uses_generic_update():
    result = propose_workflow("update", "partner", "manual")
    step_types = [s.step_type for s in result.steps]
    assert "run_guard" in step_types
    assert "request_approval" in step_types


def test_send_invoice_workflow():
    result = propose_workflow("send", "invoice", "scheduled")
    assert result.trigger_type == "scheduled"
    step_types = [s.step_type for s in result.steps]
    assert "request_approval" in step_types


def test_workflow_id_unique():
    r1 = propose_workflow("read", "sales_order", "manual")
    r2 = propose_workflow("read", "sales_order", "manual")
    assert r1.workflow_id != r2.workflow_id


def test_advisory_note_in_proposal():
    result = propose_workflow("report", "inventory", "scheduled")
    assert "non-executable" in result.advisory_note
