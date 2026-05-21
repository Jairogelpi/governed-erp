from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import (
    create_blocked_write_evidence,
    create_execution_run,
    create_execution_run_step,
    get_execution_request,
    get_execution_run,
    get_latest_skill_version,
    get_skill,
    list_execution_runs_for_request,
    list_execution_runs_for_skill,
)
from erpguard.product.execution_gate import ExecutionGateService
from erpguard.product.execution_request import ExecutionRequestService
from erpguard.product.models import (
    BlockedWriteEvidenceModel,
    ExecutionRunModel,
    SimulatedExecutionPlanModel,
    SimulatedExecutionStepModel,
    WriteCandidateModel,
)

_ALLOW_REAL_ODOO_WRITES = False
_FORBIDDEN_REAL_METHODS = {
    "create", "write", "unlink", "copy",
    "action_confirm", "action_done",
    "button_confirm", "button_validate",
}


def _build_write_candidate(model: str, method: str, args: dict) -> WriteCandidateModel:
    return WriteCandidateModel(
        model=model,
        method=method,
        args=args,
        blocked=True,
        blocked_reason="ALLOW_REAL_ODOO_WRITES=false",
    )


def _build_plan_from_skill(skill_id: str, version_row) -> SimulatedExecutionPlanModel:
    """Build a simulated execution plan from the skill's test cases and package."""
    pkg = json.loads(version_row.skill_package_json) if version_row else {}
    test_cases = pkg.get("test_cases", [])
    workflow_steps = pkg.get("workflow_steps", [])

    steps: list[SimulatedExecutionStepModel] = []
    blocked_count = 0

    # Represent workflow steps as read steps
    for i, ws in enumerate(workflow_steps):
        step_id = f"step_{i + 1:02d}"
        description = ws.get("description", ws.get("name", f"Step {i + 1}"))
        step_type = ws.get("type", "read")

        # Detect if this step resembles a write attempt
        write_candidate = None
        is_write = any(m in description.lower() for m in _FORBIDDEN_REAL_METHODS)
        if is_write:
            method_found = next((m for m in _FORBIDDEN_REAL_METHODS if m in description.lower()), "write")
            write_candidate = _build_write_candidate(
                model=ws.get("model", "unknown.model"),
                method=method_found,
                args=ws.get("args", {}),
            )
            blocked_count += 1

        steps.append(
            SimulatedExecutionStepModel(
                step_id=step_id,
                step_type="write_blocked" if is_write else step_type,
                description=description,
                status="blocked" if is_write else "simulated",
                inputs=ws.get("inputs", {}),
                simulated_output=ws.get("simulated_output", {"dry_run": True}),
                write_candidate=write_candidate,
            )
        )

    # If no workflow steps, synthesize from test cases
    if not steps and test_cases:
        for i, tc in enumerate(test_cases):
            step_id = f"step_{i + 1:02d}"
            decision = tc.get("expected_decision", "allow")
            steps.append(
                SimulatedExecutionStepModel(
                    step_id=step_id,
                    step_type="dry_run_check",
                    description=f"Simulated check: {tc.get('name', step_id)}",
                    status="simulated",
                    inputs=tc.get("inputs", {}),
                    simulated_output={"decision": decision, "dry_run": True},
                    write_candidate=None,
                )
            )

    if not steps:
        steps.append(
            SimulatedExecutionStepModel(
                step_id="step_01",
                step_type="dry_run_check",
                description="Simulated execution (dry-run only, no Odoo writes)",
                status="simulated",
                inputs={},
                simulated_output={"dry_run": True, "result": "ok"},
                write_candidate=None,
            )
        )

    plan_id = f"plan_{uuid4().hex[:16]}"
    return SimulatedExecutionPlanModel(
        plan_id=plan_id,
        skill_id=skill_id,
        steps=steps,
        total_steps=len(steps),
        blocked_write_candidates=blocked_count,
        can_execute_real_writes=False,
        real_erp_writes_enabled=False,
    )


class ExecutionRuntimeService:
    def __init__(self, session) -> None:
        self.session = session

    def execute(self, execution_request_id: str) -> ExecutionRunModel:
        req_row = get_execution_request(self.session, execution_request_id)
        if req_row is None:
            raise ObjectNotFoundError(f"Execution request '{execution_request_id}' not found.")

        skill_id = req_row.skill_id
        inputs = json.loads(req_row.inputs_json)

        # Gate check
        gate = ExecutionGateService(self.session)
        policy_result = gate.check(skill_id, req_row.skill_version_id, inputs)
        if not policy_result.passed:
            violation_msgs = "; ".join(v.message for v in policy_result.violations)
            raise ValueError(f"Execution policy blocked: {violation_msgs}")

        # Mark request running
        req_svc = ExecutionRequestService(self.session)
        req_svc.mark_running(execution_request_id)

        # Build plan
        version_row = get_latest_skill_version(self.session, skill_id)
        plan = _build_plan_from_skill(skill_id, version_row)

        # Persist execution run
        plan_dict = plan.model_dump()
        run_row = create_execution_run(
            self.session,
            execution_request_id=execution_request_id,
            skill_id=skill_id,
            status="running",
            plan_json=json.dumps(plan_dict, default=str),
            result_json=json.dumps({}),
            blocked_write_count=plan.blocked_write_candidates,
        )
        run_id = run_row.id

        # Persist each step + blocked write evidence
        for idx, step in enumerate(plan.steps):
            create_execution_run_step(
                self.session,
                execution_run_id=run_id,
                step_index=idx,
                step_id=step.step_id,
                step_type=step.step_type,
                status=step.status,
                input_json=json.dumps(step.inputs, default=str),
                output_json=json.dumps(step.simulated_output, default=str),
            )
            if step.write_candidate is not None:
                create_blocked_write_evidence(
                    self.session,
                    execution_run_id=run_id,
                    execution_request_id=execution_request_id,
                    skill_id=skill_id,
                    attempted_model=step.write_candidate.model,
                    attempted_method=step.write_candidate.method,
                    attempted_args_json=json.dumps(step.write_candidate.args, default=str),
                    blocked_reason=step.write_candidate.blocked_reason,
                )

        # Finalize run
        result = {
            "dry_run": True,
            "can_execute_real_writes": False,
            "real_erp_writes_enabled": False,
            "blocked_write_candidates": plan.blocked_write_candidates,
            "steps_simulated": len(plan.steps),
        }
        run_row.status = "completed"
        run_row.result_json = json.dumps(result, default=str)
        run_row.finished_at = datetime.now(timezone.utc)
        self.session.commit()
        self.session.refresh(run_row)

        req_svc.mark_completed(execution_request_id)

        return self._to_model(run_row, plan)

    def get(self, run_id: str) -> ExecutionRunModel:
        run_row = get_execution_run(self.session, run_id)
        if run_row is None:
            raise ObjectNotFoundError(f"Execution run '{run_id}' not found.")
        plan_dict = json.loads(run_row.plan_json)
        plan = SimulatedExecutionPlanModel.model_validate(plan_dict)
        return self._to_model(run_row, plan)

    def list_for_skill(self, skill_id: str) -> list[ExecutionRunModel]:
        rows = list_execution_runs_for_skill(self.session, skill_id)
        return [self.get(r.id) for r in rows]

    def list_for_request(self, execution_request_id: str) -> list[ExecutionRunModel]:
        rows = list_execution_runs_for_request(self.session, execution_request_id)
        return [self.get(r.id) for r in rows]

    def _to_model(self, run_row, plan: SimulatedExecutionPlanModel) -> ExecutionRunModel:
        return ExecutionRunModel.model_validate(
            {
                "run_id": run_row.id,
                "execution_request_id": run_row.execution_request_id,
                "skill_id": run_row.skill_id,
                "status": run_row.status,
                "plan": plan.model_dump(),
                "result": json.loads(run_row.result_json),
                "can_execute_real_writes": False,
                "real_erp_writes_enabled": False,
                "blocked_write_count": run_row.blocked_write_count,
                "created_at": run_row.created_at.isoformat(),
                "finished_at": run_row.finished_at.isoformat() if run_row.finished_at else None,
            }
        )
