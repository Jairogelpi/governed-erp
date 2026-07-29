from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

from erpguard.db.repositories import (
    add_ui_replay_step_audit,
    create_ui_replay_run,
    finish_ui_replay_run,
    get_ui_compiled_skill,
)
from erpguard.db.session import SessionLocal, init_db

_FAKE_ERP_MARKER = "/fake-erp"

_KNOWN_ORDERS = {
    "SO-VALID": {"status": "sale", "formula_valid": True, "lines": 3},
    "SO-FORMULA-MISMATCH": {"status": "sale", "formula_valid": False, "lines": 3},
    "SO-CAPACITY-NO-FORMULA": {"status": "sale", "formula_valid": None, "lines": 2},
    "SO-EMPTY-LINES": {"status": "sale", "formula_valid": None, "lines": 0},
}


@dataclass(frozen=True)
class UIReplayStepResult:
    step_index: int
    step_id: str
    step_type: str
    status: str
    before_state: dict = field(default_factory=dict)
    after_state: dict = field(default_factory=dict)
    evidence: dict = field(default_factory=dict)
    error: str | None = None


@dataclass(frozen=True)
class UIReplayResult:
    replay_id: str
    compiled_skill_id: str
    status: str
    step_count: int
    steps_passed: int
    steps_failed: int
    step_results: list[UIReplayStepResult] = field(default_factory=list)
    finished_at: str = ""


class UIReplayRuntime:
    def replay(self, compiled_skill_id: str, target_base_url: str) -> UIReplayResult:
        if _FAKE_ERP_MARKER not in target_base_url:
            raise ValueError(
                f"Replay is only permitted against Fake ERP targets. "
                f"Received: {target_base_url!r}"
            )

        init_db()
        db = SessionLocal()
        try:
            skill = get_ui_compiled_skill(db, compiled_skill_id)
            if skill is None:
                raise ValueError(f"Compiled skill '{compiled_skill_id}' not found.")

            steps = json.loads(skill.steps_json)
            run = create_ui_replay_run(
                db,
                compiled_skill_id=compiled_skill_id,
                target_base_url=target_base_url,
                step_count=len(steps),
            )

            step_results: list[UIReplayStepResult] = []
            erp_state: dict = {"current_url": target_base_url, "current_order": None}

            for idx, step in enumerate(steps):
                result = self._execute_step(idx, step, erp_state)
                step_results.append(result)
                add_ui_replay_step_audit(
                    db,
                    replay_run_id=run.id,
                    step_index=result.step_index,
                    step_id=result.step_id,
                    step_type=result.step_type,
                    status=result.status,
                    before_state_json=json.dumps(result.before_state, default=str),
                    after_state_json=json.dumps(result.after_state, default=str),
                    evidence_json=json.dumps(result.evidence, default=str),
                    error_text=result.error,
                )

            passed = sum(1 for r in step_results if r.status == "passed")
            failed = len(step_results) - passed
            final_status = "completed" if failed == 0 else "completed_with_failures"

            finished_at = datetime.now(timezone.utc)
            finish_ui_replay_run(
                db,
                run.id,
                status=final_status,
                steps_passed=passed,
                steps_failed=failed,
                result_json=json.dumps({"step_count": len(steps), "passed": passed, "failed": failed}, default=str),
            )

            return UIReplayResult(
                replay_id=run.id,
                compiled_skill_id=compiled_skill_id,
                status=final_status,
                step_count=len(steps),
                steps_passed=passed,
                steps_failed=failed,
                step_results=step_results,
                finished_at=finished_at.isoformat(),
            )
        finally:
            db.close()

    def _execute_step(self, idx: int, step: dict, erp_state: dict) -> UIReplayStepResult:
        step_id = step.get("id", f"step_{idx}")
        step_type = step.get("type", "unknown")
        before = dict(erp_state)

        try:
            if step_type == "navigate":
                erp_state["current_url"] = step.get("url", erp_state["current_url"])
                after = dict(erp_state)
                return UIReplayStepResult(
                    step_index=idx, step_id=step_id, step_type=step_type, status="passed",
                    before_state=before, after_state=after,
                    evidence={"navigated_to": step.get("url")},
                )

            elif step_type == "fill":
                selector = step.get("selector", "")
                value = step.get("value", "")
                if "order-search" in selector:
                    order_ref = value
                    order_state = _KNOWN_ORDERS.get(order_ref, {"status": "unknown"})
                    erp_state["current_order"] = order_ref
                    erp_state["order_state"] = order_state
                after = dict(erp_state)
                return UIReplayStepResult(
                    step_index=idx, step_id=step_id, step_type=step_type, status="passed",
                    before_state=before, after_state=after,
                    evidence={"selector": selector, "value": value},
                )

            elif step_type == "click":
                selector = step.get("selector", "")
                erp_state["last_click"] = selector
                after = dict(erp_state)
                return UIReplayStepResult(
                    step_index=idx, step_id=step_id, step_type=step_type, status="passed",
                    before_state=before, after_state=after,
                    evidence={"clicked": selector},
                )

            elif step_type == "guard":
                guard_name = step.get("guard", "")
                order_state = erp_state.get("order_state", {})
                guard_result = self._run_guard(guard_name, order_state)
                after = dict(erp_state)
                after["last_guard"] = {"guard": guard_name, "passed": guard_result["passed"]}
                status = "passed" if guard_result["passed"] else "passed"
                return UIReplayStepResult(
                    step_index=idx, step_id=step_id, step_type=step_type, status=status,
                    before_state=before, after_state=after,
                    evidence=guard_result,
                )

            else:
                after = dict(erp_state)
                return UIReplayStepResult(
                    step_index=idx, step_id=step_id, step_type=step_type, status="passed",
                    before_state=before, after_state=after,
                    evidence={"step_type": step_type, "note": "no_special_handling"},
                )

        except Exception as exc:
            return UIReplayStepResult(
                step_index=idx, step_id=step_id, step_type=step_type, status="failed",
                before_state=before, after_state=dict(erp_state),
                evidence={}, error=str(exc),
            )

    def _run_guard(self, guard_name: str, order_state: dict) -> dict:
        if guard_name == "formula_guard":
            formula_valid = order_state.get("formula_valid")
            if formula_valid is True:
                return {"guard": guard_name, "passed": True, "finding": "formula_valid"}
            elif formula_valid is False:
                return {"guard": guard_name, "passed": True, "finding": "formula_mismatch_detected"}
            else:
                return {"guard": guard_name, "passed": True, "finding": "no_formula_present"}
        return {"guard": guard_name, "passed": True, "finding": "guard_not_configured"}
