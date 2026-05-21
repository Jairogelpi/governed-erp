from __future__ import annotations

import json

from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import get_operator_session, list_operator_session_events
from erpguard.product.operator_flow_state import FLOW_STEPS, step_index


class OperatorSummaryService:
    def __init__(self, session) -> None:
        self.session = session

    def summarize(self, session_id: str) -> dict:
        row = get_operator_session(self.session, session_id)
        if row is None:
            raise ObjectNotFoundError(f"Operator session '{session_id}' not found.")
        events = list_operator_session_events(self.session, session_id)
        known_ids = json.loads(row.known_ids_json)

        completed_steps = [ev.step for ev in events if ev.status == "ok"]
        errored_steps = [ev.step for ev in events if ev.status == "error"]
        current_idx = step_index(row.current_step)
        total_steps = len(FLOW_STEPS) - 1  # exclude "completed"

        progress_pct = int((current_idx / max(total_steps, 1)) * 100)

        return {
            "session_id": session_id,
            "status": row.status,
            "current_step": row.current_step,
            "progress_pct": progress_pct,
            "steps_completed": len(completed_steps),
            "steps_total": total_steps,
            "known_ids": _safe_known_ids(known_ids),
            "completed_steps": completed_steps,
            "errored_steps": errored_steps,
            "safety_invariants": {
                "can_execute_real_writes": False,
                "real_erp_writes_enabled": False,
                "approved_for_real_execution": False,
                "allow_generic_real_odoo_writes": False,
                "allow_r3_r4_real_writes": False,
            },
        }


def _safe_known_ids(known_ids: dict) -> dict:
    _SENSITIVE = frozenset({"password", "api_key", "token", "secret", "credential"})
    return {k: v for k, v in known_ids.items() if k.lower() not in _SENSITIVE}
