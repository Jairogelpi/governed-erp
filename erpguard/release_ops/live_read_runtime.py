from __future__ import annotations

import json
from datetime import datetime, timezone

from erpguard.adapters.odoo.config import OdooConfig
from erpguard.adapters.odoo.readonly_client import build_readonly_client
from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import (
    create_blocked_write_evidence,
    create_execution_run_step,
    create_live_read_evidence,
    create_live_read_run,
    get_live_read_execution_request,
    get_live_read_run,
    update_live_read_execution_request_status,
)
from erpguard.release_ops.connection_context import ConnectionContextService
from erpguard.release_ops.live_read_plan import LiveReadPlanService
from erpguard.release_ops.live_read_policy import LiveReadPolicyService
from erpguard.product.models import (
    LiveReadPlanModel,
    LiveReadRunModel,
    WriteCandidateModel,
)

_ALLOW_REAL_ODOO_READS = True
_ALLOW_REAL_ODOO_WRITES = False

_ALLOWED_READ_METHODS = {"search_read", "read", "fields_get", "search_count"}
_FORBIDDEN_WRITE_METHODS = {
    "create", "write", "unlink", "copy",
    "action_confirm", "action_done",
    "button_confirm", "button_validate",
}


def _execute_read_step(client, step) -> tuple[dict, int]:
    """Execute one read step. Returns (result_summary, records_fetched)."""
    try:
        method = step.odoo_method
        model = step.odoo_model
        if method == "search_read":
            records = client.search_read(model, step.domain, step.fields or ["id"], limit=step.limit)
            return {
                "method": "search_read",
                "model": model,
                "records": len(records),
                "sample": records[:2] if records else [],
                "read_only": True,
            }, len(records)
        elif method == "search_count":
            count = client.search_count(model, step.domain)
            return {
                "method": "search_count",
                "model": model,
                "count": count,
                "read_only": True,
            }, count
        elif method == "fields_get":
            result = client.fields_get(model, step.fields or None)
            return {
                "method": "fields_get",
                "model": model,
                "field_count": len(result),
                "read_only": True,
            }, len(result)
        elif method == "read":
            return {"method": "read", "model": model, "read_only": True}, 0
        else:
            return {"error": f"unsupported_method: {method}", "read_only": True}, 0
    except Exception as exc:
        return {"error": str(exc), "read_only": True, "degraded": True}, 0


class LiveReadRuntimeService:
    def __init__(self, session) -> None:
        self.session = session

    def execute(self, execution_request_id: str) -> LiveReadRunModel:
        req_row = get_live_read_execution_request(self.session, execution_request_id)
        if req_row is None:
            raise ObjectNotFoundError(f"Live read execution request '{execution_request_id}' not found.")

        skill_id = req_row.skill_id
        json.loads(req_row.inputs_json)

        # Policy check
        policy = LiveReadPolicyService(self.session)
        policy_result = policy.check(skill_id)
        if not policy_result.passed:
            violation_msgs = "; ".join(v.message for v in policy_result.violations)
            raise ValueError(f"Live read policy blocked: {violation_msgs}")

        # Resolve connection
        ctx_svc = ConnectionContextService(self.session)
        try:
            config_dict, connection_id = ctx_svc.resolve_config(skill_id)
        except (ObjectNotFoundError, ValueError) as exc:
            raise ValueError(f"missing_connection_context: {exc}") from exc

        odoo_config = OdooConfig(**config_dict)

        # Build plan
        plan_svc = LiveReadPlanService(self.session)
        plan = plan_svc.build(skill_id, connection_id)

        # Mark request running
        update_live_read_execution_request_status(self.session, execution_request_id, "running")

        # Persist initial run
        run_row = create_live_read_run(
            self.session,
            execution_request_id=execution_request_id,
            skill_id=skill_id,
            connection_id=connection_id,
            status="running",
            plan_json=json.dumps(plan.model_dump(), default=str),
            result_json=json.dumps({}),
        )
        run_id = run_row.id

        # Build readonly client
        client = build_readonly_client(odoo_config)

        # Execute steps
        real_read_count = 0
        blocked_write_count = 0
        completed_steps = []

        for idx, step in enumerate(plan.steps):
            if step.odoo_method in _FORBIDDEN_WRITE_METHODS:
                # Block it
                write_candidate = WriteCandidateModel(
                    model=step.odoo_model,
                    method=step.odoo_method,
                    args={},
                    blocked=True,
                    blocked_reason="ALLOW_REAL_ODOO_WRITES=false",
                )
                create_blocked_write_evidence(
                    self.session,
                    execution_run_id=run_id,
                    execution_request_id=execution_request_id,
                    skill_id=skill_id,
                    attempted_model=step.odoo_model,
                    attempted_method=step.odoo_method,
                    attempted_args_json=json.dumps({}),
                    blocked_reason="ALLOW_REAL_ODOO_WRITES=false",
                )
                blocked_write_count += 1
                step_status = "blocked"
                real_output = {"blocked": True, "blocked_reason": "ALLOW_REAL_ODOO_WRITES=false"}
                records_fetched = 0
            else:
                result_summary, records_fetched = _execute_read_step(client, step)
                real_read_count += 1
                step_status = "completed"
                real_output = result_summary
                write_candidate = None

                create_live_read_evidence(
                    self.session,
                    live_read_run_id=run_id,
                    execution_request_id=execution_request_id,
                    skill_id=skill_id,
                    step_id=step.step_id,
                    odoo_model=step.odoo_model,
                    odoo_method=step.odoo_method,
                    query_summary_json=json.dumps({
                        "model": step.odoo_model,
                        "method": step.odoo_method,
                        "domain": step.domain,
                        "fields": step.fields,
                        "limit": step.limit,
                    }, default=str),
                    records_fetched=records_fetched,
                    result_summary_json=json.dumps(result_summary, default=str),
                )

            create_execution_run_step(
                self.session,
                execution_run_id=run_id,
                step_index=idx,
                step_id=step.step_id,
                step_type=step.step_type,
                status=step_status,
                input_json=json.dumps({"model": step.odoo_model, "method": step.odoo_method, "domain": step.domain}, default=str),
                output_json=json.dumps(real_output, default=str),
            )

            completed_steps.append(step.model_copy(update={
                "status": step_status,
                "real_output": real_output,
                "write_candidate": write_candidate,
            }))

        # Finalize
        final_plan = plan.model_copy(update={
            "steps": completed_steps,
            "real_read_steps": real_read_count,
            "blocked_write_candidates": blocked_write_count,
        })
        result = {
            "live_read": True,
            "can_execute_real_writes": False,
            "real_erp_writes_enabled": False,
            "allow_real_odoo_reads": True,
            "real_read_count": real_read_count,
            "blocked_write_candidates": blocked_write_count,
            "steps_executed": len(plan.steps),
        }
        run_row.status = "completed"
        run_row.result_json = json.dumps(result, default=str)
        run_row.plan_json = json.dumps(final_plan.model_dump(), default=str)
        run_row.real_read_count = real_read_count
        run_row.blocked_write_count = blocked_write_count
        run_row.finished_at = datetime.now(timezone.utc)
        self.session.commit()
        self.session.refresh(run_row)

        update_live_read_execution_request_status(self.session, execution_request_id, "completed")

        return self._to_model(run_row, final_plan)

    def get(self, run_id: str) -> LiveReadRunModel:
        run_row = get_live_read_run(self.session, run_id)
        if run_row is None:
            raise ObjectNotFoundError(f"Live read run '{run_id}' not found.")
        plan = LiveReadPlanModel.model_validate(json.loads(run_row.plan_json))
        return self._to_model(run_row, plan)

    def _to_model(self, run_row, plan: LiveReadPlanModel) -> LiveReadRunModel:
        return LiveReadRunModel.model_validate(
            {
                "run_id": run_row.id,
                "execution_request_id": run_row.execution_request_id,
                "skill_id": run_row.skill_id,
                "connection_id": run_row.connection_id,
                "status": run_row.status,
                "plan": plan.model_dump(),
                "result": json.loads(run_row.result_json),
                "can_execute_real_writes": False,
                "real_erp_writes_enabled": False,
                "allow_real_odoo_reads": True,
                "real_read_count": run_row.real_read_count,
                "blocked_write_count": run_row.blocked_write_count,
                "created_at": run_row.created_at.isoformat(),
                "finished_at": run_row.finished_at.isoformat() if run_row.finished_at else None,
            }
        )
