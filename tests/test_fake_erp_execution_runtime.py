from __future__ import annotations

from erpguard.product.fake_erp_execution_runtime import run_controlled_fake_erp_runtime


def test_runtime_executes_allowlisted_fake_steps_only():
    result = run_controlled_fake_erp_runtime(
        allowlisted_steps=[
            {"step_number": 1, "step_name": "Validate", "operation": "fake_validate_order"},
            {"step_number": 2, "step_name": "Update", "operation": "fake_update_sandbox_status"},
        ],
        inputs={"order_reference": "SO-VALID"},
    )
    assert result.step_count == 2
    assert result.steps_executed == 2
    assert result.steps_blocked == 0
    assert all(step.executed is True for step in result.steps)
    assert all(step.execution_target == "fake_erp" for step in result.steps)


def test_runtime_never_touches_real_erp_browser_mcp_or_http():
    result = run_controlled_fake_erp_runtime(
        allowlisted_steps=[{"step_number": 1, "step_name": "Validate", "operation": "fake_validate_order"}],
        inputs={"order_reference": "SO-VALID"},
    )
    step = result.steps[0]
    assert step.real_erp_touched is False
    assert step.odoo_touched is False
    assert step.browser_control_performed is False
    assert step.mcp_execution_performed is False
    assert step.llm_runtime_used is False
    assert step.external_http_performed is False

