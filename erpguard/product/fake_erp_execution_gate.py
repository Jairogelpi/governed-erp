from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

from erpguard.db.repositories import (
    expire_action_plan_step_tokens,
    get_action_plan_step_token,
    get_active_skill_run,
    get_manual_dry_run_evidence_for_run,
    get_ui_skill_version_record,
)


FAKE_ERP_ALLOWED_OPERATIONS = {
    "fake_read_record",
    "fake_validate_order",
    "fake_calculate_totals",
    "fake_update_sandbox_status",
}
_BLOCKED_TARGET_KEYWORDS = ("odoo", "real_erp", "browser", "mcp", "scheduler", "http", "endpoint_hint")


@dataclass(frozen=True)
class FakeERPExecutionGateRequest:
    version_id: str
    dry_run_id: str
    token_id: str
    actor_id: str
    execution_target: str


@dataclass(frozen=True)
class FakeERPExecutionGateResult:
    version_id: str
    dry_run_id: str
    passed: bool
    checks: list[dict] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    token_status: str = "not_found"
    allowlisted_steps: list[dict] = field(default_factory=list)


def _parse_steps(steps_json: str) -> list[dict]:
    try:
        data = json.loads(steps_json or "[]")
        if isinstance(data, list):
            return [step for step in data if isinstance(step, dict)]
    except Exception:
        pass
    return []


def _step_operation(step: dict) -> str:
    return str(step.get("operation") or step.get("action_key") or step.get("type") or "").strip()


def _step_target(step: dict) -> str:
    return str(step.get("target") or step.get("execution_target") or "").strip()


def _step_is_allowlisted(step: dict) -> tuple[bool, str | None]:
    operation = _step_operation(step)
    target = _step_target(step).lower()
    packed = json.dumps(step).lower()

    if any(keyword in packed for keyword in _BLOCKED_TARGET_KEYWORDS):
        return False, "step_references_blocked_target"

    if operation in FAKE_ERP_ALLOWED_OPERATIONS:
        return True, None
    if operation.startswith("fake_"):
        return True, None
    if target == "fake_erp" and operation.startswith("fake_"):
        return True, None
    return False, "step_not_fake_erp_allowlisted"


def evaluate_fake_erp_execution_gate(req: FakeERPExecutionGateRequest, session) -> FakeERPExecutionGateResult:
    checks: list[dict] = []
    blocking: list[str] = []
    allowlisted_steps: list[dict] = []

    expire_action_plan_step_tokens(session, now=datetime.now(timezone.utc))
    token = get_action_plan_step_token(session, req.token_id)
    token_status = token.status if token is not None else "not_found"
    token_ok = token is not None and token.status == "confirmed"
    checks.append({"check": "confirmed_token_exists", "ok": token_ok, "value": token_status})
    if not token_ok:
        blocking.append(f"token_not_confirmed:{token_status}")

    actor_ok = bool((req.actor_id or "").strip())
    checks.append({"check": "actor_present", "ok": actor_ok})
    if not actor_ok:
        blocking.append("actor_required")

    version = get_ui_skill_version_record(session, req.version_id)
    version_ok = version is not None
    checks.append({"check": "version_exists", "ok": version_ok})
    if not version_ok:
        blocking.append("version_not_found")
        return FakeERPExecutionGateResult(
            version_id=req.version_id,
            dry_run_id=req.dry_run_id,
            passed=False,
            checks=checks,
            blocking_reasons=blocking,
            token_status=token_status,
        )

    governed_active_ok = version.status == "active" and version.is_active is True
    checks.append({"check": "version_is_active_governed", "ok": governed_active_ok})
    if not governed_active_ok:
        blocking.append("version_not_active_governed")

    dry_run = get_active_skill_run(session, req.dry_run_id)
    dry_run_exists = dry_run is not None
    checks.append({"check": "dry_run_exists", "ok": dry_run_exists})
    if not dry_run_exists:
        blocking.append("dry_run_not_found")
        return FakeERPExecutionGateResult(
            version_id=req.version_id,
            dry_run_id=req.dry_run_id,
            passed=False,
            checks=checks,
            blocking_reasons=blocking,
            token_status=token_status,
        )

    same_version = dry_run.version_id == req.version_id
    checks.append({"check": "dry_run_matches_version", "ok": same_version, "value": dry_run.version_id})
    if not same_version:
        blocking.append("dry_run_version_mismatch")

    dry_run_completed = dry_run.status == "completed"
    checks.append({"check": "dry_run_completed", "ok": dry_run_completed, "value": dry_run.status})
    if not dry_run_completed:
        blocking.append("dry_run_not_completed")

    dry_run_summary = json.loads(dry_run.summary_json or "{}") if dry_run.summary_json else {}
    dry_run_mode_ok = dry_run_summary.get("mode", "dry_run") == "dry_run"
    checks.append({"check": "dry_run_mode_is_dry_run", "ok": dry_run_mode_ok, "value": dry_run_summary.get("mode")})
    if not dry_run_mode_ok:
        blocking.append("dry_run_mode_invalid")

    dry_run_evidence = get_manual_dry_run_evidence_for_run(session, req.dry_run_id)
    evidence_ok = dry_run_evidence is not None
    checks.append({"check": "dry_run_evidence_exists", "ok": evidence_ok})
    if not evidence_ok:
        blocking.append("dry_run_evidence_missing")

    target = (req.execution_target or "").strip().lower()
    target_ok = target == "fake_erp"
    checks.append({"check": "execution_target_is_fake_erp", "ok": target_ok, "value": target})
    if not target_ok:
        blocking.append(f"execution_target_not_allowed:{target or 'missing'}")

    runtime_ok = version.runtime_type == "deterministic_ui"
    checks.append({"check": "runtime_type_supported", "ok": runtime_ok, "value": version.runtime_type})
    if not runtime_ok:
        blocking.append("unsupported_runtime_type")

    raw_steps = _parse_steps(version.steps_json)
    step_ok = True
    for idx, step in enumerate(raw_steps, start=1):
        allowed, reason = _step_is_allowlisted(step)
        step_info = {
            "step_number": idx,
            "step_name": str(step.get("name") or step.get("id") or f"step_{idx}"),
            "operation": _step_operation(step),
            "target": _step_target(step),
            "allowlisted": allowed,
        }
        if allowed:
            allowlisted_steps.append(step_info)
        else:
            step_ok = False
            blocking.append(f"{reason}:{idx}")
    checks.append({"check": "skill_steps_allowlisted_for_fake_erp", "ok": step_ok, "value": allowlisted_steps})

    return FakeERPExecutionGateResult(
        version_id=req.version_id,
        dry_run_id=req.dry_run_id,
        passed=len(blocking) == 0,
        checks=checks,
        blocking_reasons=blocking,
        token_status=token_status,
        allowlisted_steps=allowlisted_steps,
    )
