from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class FakeERPExecutedStep:
    step_number: int
    step_name: str
    operation: str
    input_snapshot: dict
    expected_effect: str
    actual_fake_effect: str
    executed: bool
    execution_target: str
    real_erp_touched: bool
    odoo_touched: bool
    browser_control_performed: bool
    mcp_execution_performed: bool
    llm_runtime_used: bool
    external_http_performed: bool
    status: str
    error: str | None
    started_at: str
    finished_at: str


@dataclass(frozen=True)
class FakeERPExecutionRuntimeResult:
    step_count: int
    steps_executed: int
    steps_blocked: int
    steps: list[FakeERPExecutedStep] = field(default_factory=list)
    result_summary: str = ""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_controlled_fake_erp_runtime(*, allowlisted_steps: list[dict], inputs: dict) -> FakeERPExecutionRuntimeResult:
    steps: list[FakeERPExecutedStep] = []
    executed = 0

    for step in allowlisted_steps:
        started_at = _now_iso()
        operation = str(step.get("operation") or "")
        step_name = str(step.get("step_name") or f"step_{step.get('step_number', 0)}")
        order_reference = str(inputs.get("order_reference") or "unknown")
        actual_effect = f"{operation} executed against Fake ERP fixture for {order_reference}"
        steps.append(
            FakeERPExecutedStep(
                step_number=int(step.get("step_number") or 0),
                step_name=step_name,
                operation=operation,
                input_snapshot=dict(inputs),
                expected_effect=f"Fake ERP operation {operation} should complete deterministically.",
                actual_fake_effect=actual_effect,
                executed=True,
                execution_target="fake_erp",
                real_erp_touched=False,
                odoo_touched=False,
                browser_control_performed=False,
                mcp_execution_performed=False,
                llm_runtime_used=False,
                external_http_performed=False,
                status="completed",
                error=None,
                started_at=started_at,
                finished_at=_now_iso(),
            )
        )
        executed += 1

    summary = "Controlled Fake ERP execution completed. No real ERP was touched."
    return FakeERPExecutionRuntimeResult(
        step_count=len(allowlisted_steps),
        steps_executed=executed,
        steps_blocked=0,
        steps=steps,
        result_summary=summary,
    )
