from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from erpguard.db.repositories import (
    expire_action_plan_step_tokens,
    get_action_plan_step_token,
    get_ui_skill_version_record,
    list_agent_skill_run_preview_events_for_version,
)
from erpguard.product.governance_gap_explainer import explain_governance_gaps


@dataclass(frozen=True)
class ManualDryRunGateRequest:
    version_id: str
    token_id: str
    mode: str
    actor_id: str
    requested_target: str | None = None


@dataclass(frozen=True)
class ManualDryRunGateResult:
    version_id: str
    passed: bool
    checks: list[dict] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    token_status: str = "not_found"
    preview_reference_id: str | None = None


def evaluate_manual_dry_run_gate(req: ManualDryRunGateRequest, session) -> ManualDryRunGateResult:
    checks: list[dict] = []
    blocking: list[str] = []

    expire_action_plan_step_tokens(session, now=datetime.now(timezone.utc))
    token = get_action_plan_step_token(session, req.token_id)
    token_status = token.status if token is not None else "not_found"
    token_ok = token is not None and token.status == "confirmed"
    checks.append({"check": "confirmed_token_exists", "ok": token_ok, "value": token_status})
    if not token_ok:
        blocking.append(f"token_not_confirmed:{token_status}")

    mode_ok = (req.mode or "").lower() == "dry_run"
    checks.append({"check": "mode_is_dry_run", "ok": mode_ok, "value": req.mode})
    if not mode_ok:
        blocking.append("only_dry_run_mode_allowed")

    actor_ok = bool((req.actor_id or "").strip())
    checks.append({"check": "actor_present", "ok": actor_ok})
    if not actor_ok:
        blocking.append("actor_required")

    version = get_ui_skill_version_record(session, req.version_id)
    version_ok = version is not None
    checks.append({"check": "version_exists", "ok": version_ok})
    if not version_ok:
        blocking.append("version_not_found")
        return ManualDryRunGateResult(
            version_id=req.version_id,
            passed=False,
            checks=checks,
            blocking_reasons=blocking,
            token_status=token_status,
        )

    governed_active_ok = version.status == "active" and version.is_active is True
    checks.append(
        {
            "check": "version_is_active_governed",
            "ok": governed_active_ok,
            "value": {"status": version.status, "is_active": version.is_active},
        }
    )
    if not governed_active_ok:
        blocking.append("version_not_active_governed")

    runtime_ok = version.runtime_type == "deterministic_ui"
    checks.append({"check": "runtime_type_safe", "ok": runtime_ok, "value": version.runtime_type})
    if not runtime_ok:
        blocking.append("unsupported_runtime_type")

    llm_ok = not version.llm_required
    checks.append({"check": "llm_runtime_not_required", "ok": llm_ok, "value": version.llm_required})
    if not llm_ok:
        blocking.append("llm_runtime_not_allowed")

    preview_events = list_agent_skill_run_preview_events_for_version(session, req.version_id)
    preview_completed = [e for e in preview_events if e.step == "run_preview_completed" and e.status == "completed"]
    preview_exists = len(preview_completed) > 0
    preview_reference_id = preview_completed[-1].id if preview_completed else None

    inline_preview_pass = governed_active_ok and runtime_ok and llm_ok
    preview_ok = preview_exists or inline_preview_pass
    checks.append(
        {
            "check": "run_preview_exists_or_inline_pass",
            "ok": preview_ok,
            "value": {
                "preview_exists": preview_exists,
                "inline_preview_pass": inline_preview_pass,
                "preview_reference_id": preview_reference_id,
            },
        }
    )
    if not preview_ok:
        blocking.append("run_preview_missing_or_failed")

    gaps = explain_governance_gaps(req.version_id, session)
    blocking_gaps = [g.gap_type for g in gaps.gaps if g.severity == "blocking"]
    no_blocking_gaps = len(blocking_gaps) == 0 or governed_active_ok
    checks.append(
        {
            "check": "no_blocking_governance_gaps",
            "ok": no_blocking_gaps,
            "value": {
                "blocking_gaps": blocking_gaps,
                "bypassed_for_active_governed": governed_active_ok,
            },
        }
    )
    if not no_blocking_gaps:
        blocking.append("blocking_governance_gaps_present")

    target = (req.requested_target or "simulation").lower().strip()
    target_ok = target not in {"odoo", "fake_erp", "browser", "mcp"}
    checks.append({"check": "requested_target_allowed", "ok": target_ok, "value": target})
    if not target_ok:
        blocking.append(f"requested_target_not_allowed:{target}")

    passed = len(blocking) == 0
    return ManualDryRunGateResult(
        version_id=req.version_id,
        passed=passed,
        checks=checks,
        blocking_reasons=blocking,
        token_status=token_status,
        preview_reference_id=preview_reference_id,
    )
