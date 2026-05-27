from __future__ import annotations

import json
from dataclasses import dataclass

from erpguard.db.repositories import create_manual_dry_run_evidence


@dataclass(frozen=True)
class ManualDryRunEvidenceResult:
    evidence_id: str
    run_id: str


def _parse_steps(steps_json: str) -> list[dict]:
    try:
        data = json.loads(steps_json or "[]")
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def persist_manual_dry_run_evidence(
    *,
    run_id: str,
    version_id: str,
    skill_id: str,
    actor: dict,
    mode: str,
    inputs: dict,
    preview_reference_id: str | None,
    source_plan_id: str | None,
    source_step_number: int | None,
    gate_result: dict,
    steps_json: str,
    session,
) -> ManualDryRunEvidenceResult:
    raw_steps = _parse_steps(steps_json)

    simulated_steps: list[dict] = []
    would_execute_steps: list[dict] = []
    blocked_steps: list[dict] = []

    for idx, step in enumerate(raw_steps, start=1):
        name = str(step.get("name") or step.get("description") or step.get("step_id") or f"step_{idx}")
        execution_target = "none"
        item = {
            "step_number": idx,
            "name": name,
            "would_execute": True,
            "executed": False,
            "execution_target": execution_target,
            "safety_note": "Dry-run only. Step was not executed.",
        }
        simulated_steps.append(item)
        would_execute_steps.append(item)

    safety_summary = {
        "execution_performed": False,
        "erp_writes_performed": False,
        "browser_control_performed": False,
        "mcp_execution_performed": False,
        "llm_runtime_used": False,
        "fake_erp_execution_performed": False,
        "odoo_execution_performed": False,
        "scheduler_used": False,
    }

    row = create_manual_dry_run_evidence(
        session,
        run_id=run_id,
        version_id=version_id,
        skill_id=skill_id,
        actor_json=json.dumps(actor),
        mode=mode,
        inputs_json=json.dumps(inputs),
        preview_reference_id=preview_reference_id,
        source_plan_id=source_plan_id,
        source_step_number=source_step_number,
        gate_result_json=json.dumps(gate_result),
        simulated_steps_json=json.dumps(simulated_steps),
        would_execute_steps_json=json.dumps(would_execute_steps),
        blocked_steps_json=json.dumps(blocked_steps),
        safety_summary_json=json.dumps(safety_summary),
    )
    return ManualDryRunEvidenceResult(evidence_id=row.id, run_id=row.run_id)
