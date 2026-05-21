from __future__ import annotations

import json

from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import get_execution_run, list_execution_run_steps
from erpguard.product.models import ExecutionRunStepModel, ExecutionTimelineModel


class ExecutionTimelineService:
    def __init__(self, session) -> None:
        self.session = session

    def get(self, run_id: str) -> ExecutionTimelineModel:
        run = get_execution_run(self.session, run_id)
        if run is None:
            raise ObjectNotFoundError(f"Execution run '{run_id}' not found.")

        step_rows = list_execution_run_steps(self.session, run_id)
        steps = [
            ExecutionRunStepModel.model_validate(
                {
                    "step_id": r.step_id,
                    "step_type": r.step_type,
                    "status": r.status,
                    "input": json.loads(r.input_json),
                    "output": json.loads(r.output_json),
                    "created_at": r.created_at.isoformat(),
                }
            )
            for r in step_rows
        ]

        return ExecutionTimelineModel.model_validate(
            {
                "run_id": run_id,
                "steps": [s.model_dump() for s in steps],
                "total_steps": len(steps),
                "can_execute_real_writes": False,
                "real_erp_writes_enabled": False,
            }
        )
