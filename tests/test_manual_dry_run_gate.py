from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from erpguard.db.repositories import create_action_plan_step_token
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.manual_dry_run_gate import ManualDryRunGateRequest, evaluate_manual_dry_run_gate
from erpguard.db.models import UISkillVersionRecord, ActionPlanStepToken


def _make_version(*, status: str = "active", is_active: bool = True, runtime_type: str = "deterministic_ui", llm_required: bool = False) -> str:
    init_db()
    db = SessionLocal()
    try:
        row = UISkillVersionRecord(
            id=f"ver_{uuid.uuid4().hex[:16]}",
            skill_id=f"skill_{uuid.uuid4().hex[:8]}",
            compiled_skill_id=f"comp_{uuid.uuid4().hex[:8]}",
            name="manual-dry-run-skill",
            status=status,
            steps_json='[{"name":"Open sales order"},{"name":"Review formula"}]',
            guard_names_json='["formula_guard"]',
            runtime_type=runtime_type,
            llm_required=llm_required,
            promotion_readiness_json="{}",
            is_active=is_active,
        )
        db.add(row)
        db.commit()
        return row.id
    finally:
        db.close()


def _make_token(*, status: str = "confirmed") -> str:
    init_db()
    db = SessionLocal()
    try:
        token_id = f"tok_{uuid.uuid4().hex[:16]}"
        create_action_plan_step_token(
            db,
            token_id=token_id,
            plan_id="aplan_manual_dry_run",
            step_number=4,
            step_title="Manual dry-run",
            endpoint_hint="POST /v1/operator-console/action-plan/manual-dry-run",
            method_hint="POST",
            severity="blocking",
            risk_level="medium",
            risk_summary="manual dry-run confirmation",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        row = db.query(ActionPlanStepToken).filter(ActionPlanStepToken.id == token_id).first()
        row.status = status
        if status == "expired":
            row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        if status == "confirmed":
            row.confirmed_at = datetime.now(timezone.utc)
        db.commit()
        return token_id
    finally:
        db.close()


def test_gate_passes_for_eligible_active_governed_version():
    version_id = _make_version(status="active", is_active=True)
    token_id = _make_token(status="confirmed")
    init_db()
    db = SessionLocal()
    try:
        result = evaluate_manual_dry_run_gate(
            ManualDryRunGateRequest(
                version_id=version_id,
                token_id=token_id,
                mode="dry_run",
                actor_id="operator_1",
                requested_target="simulation",
            ),
            db,
        )
        assert result.passed is True
        assert result.blocking_reasons == []
    finally:
        db.close()


def test_requires_confirmed_token():
    version_id = _make_version()
    token_id = _make_token(status="pending")
    init_db()
    db = SessionLocal()
    try:
        result = evaluate_manual_dry_run_gate(ManualDryRunGateRequest(version_id=version_id, token_id=token_id, mode="dry_run", actor_id="operator_1"), db)
        assert result.passed is False
        assert any("token_not_confirmed" in x for x in result.blocking_reasons)
    finally:
        db.close()


def test_pending_token_blocks():
    version_id = _make_version()
    token_id = _make_token(status="pending")
    init_db()
    db = SessionLocal()
    try:
        result = evaluate_manual_dry_run_gate(ManualDryRunGateRequest(version_id=version_id, token_id=token_id, mode="dry_run", actor_id="operator_1"), db)
        assert result.passed is False
        assert "token_not_confirmed:pending" in result.blocking_reasons
    finally:
        db.close()


def test_expired_token_blocks():
    version_id = _make_version()
    token_id = _make_token(status="expired")
    init_db()
    db = SessionLocal()
    try:
        result = evaluate_manual_dry_run_gate(ManualDryRunGateRequest(version_id=version_id, token_id=token_id, mode="dry_run", actor_id="operator_1"), db)
        assert result.passed is False
        assert "token_not_confirmed:expired" in result.blocking_reasons
    finally:
        db.close()


def test_missing_actor_blocks():
    version_id = _make_version()
    token_id = _make_token(status="confirmed")
    init_db()
    db = SessionLocal()
    try:
        result = evaluate_manual_dry_run_gate(ManualDryRunGateRequest(version_id=version_id, token_id=token_id, mode="dry_run", actor_id=""), db)
        assert result.passed is False
        assert "actor_required" in result.blocking_reasons
    finally:
        db.close()


def test_missing_version_blocks():
    token_id = _make_token(status="confirmed")
    init_db()
    db = SessionLocal()
    try:
        result = evaluate_manual_dry_run_gate(ManualDryRunGateRequest(version_id="ver_missing", token_id=token_id, mode="dry_run", actor_id="operator_1"), db)
        assert result.passed is False
        assert "version_not_found" in result.blocking_reasons
    finally:
        db.close()


def test_invalid_version_blocks():
    version_id = _make_version(status="draft", is_active=False)
    token_id = _make_token(status="confirmed")
    init_db()
    db = SessionLocal()
    try:
        result = evaluate_manual_dry_run_gate(ManualDryRunGateRequest(version_id=version_id, token_id=token_id, mode="dry_run", actor_id="operator_1"), db)
        assert result.passed is False
        assert "version_not_active_governed" in result.blocking_reasons
    finally:
        db.close()


def test_governance_gap_blocks_for_non_governed_version():
    version_id = _make_version(status="candidate", is_active=False)
    token_id = _make_token(status="confirmed")
    init_db()
    db = SessionLocal()
    try:
        result = evaluate_manual_dry_run_gate(ManualDryRunGateRequest(version_id=version_id, token_id=token_id, mode="dry_run", actor_id="operator_1"), db)
        assert result.passed is False
        assert "blocking_governance_gaps_present" in result.blocking_reasons
    finally:
        db.close()


def test_non_dry_run_mode_blocks():
    version_id = _make_version()
    token_id = _make_token(status="confirmed")
    init_db()
    db = SessionLocal()
    try:
        result = evaluate_manual_dry_run_gate(ManualDryRunGateRequest(version_id=version_id, token_id=token_id, mode="live_run", actor_id="operator_1"), db)
        assert result.passed is False
        assert "only_dry_run_mode_allowed" in result.blocking_reasons
    finally:
        db.close()


def test_requested_odoo_target_blocks():
    version_id = _make_version()
    token_id = _make_token(status="confirmed")
    init_db()
    db = SessionLocal()
    try:
        result = evaluate_manual_dry_run_gate(ManualDryRunGateRequest(version_id=version_id, token_id=token_id, mode="dry_run", actor_id="operator_1", requested_target="odoo"), db)
        assert result.passed is False
        assert "requested_target_not_allowed:odoo" in result.blocking_reasons
    finally:
        db.close()


def test_requested_fake_erp_target_blocks_in_sprint_47():
    version_id = _make_version()
    token_id = _make_token(status="confirmed")
    init_db()
    db = SessionLocal()
    try:
        result = evaluate_manual_dry_run_gate(ManualDryRunGateRequest(version_id=version_id, token_id=token_id, mode="dry_run", actor_id="operator_1", requested_target="fake_erp"), db)
        assert result.passed is False
        assert "requested_target_not_allowed:fake_erp" in result.blocking_reasons
    finally:
        db.close()


def test_browser_target_blocks():
    version_id = _make_version()
    token_id = _make_token(status="confirmed")
    init_db()
    db = SessionLocal()
    try:
        result = evaluate_manual_dry_run_gate(ManualDryRunGateRequest(version_id=version_id, token_id=token_id, mode="dry_run", actor_id="operator_1", requested_target="browser"), db)
        assert result.passed is False
        assert "requested_target_not_allowed:browser" in result.blocking_reasons
    finally:
        db.close()


def test_mcp_target_blocks():
    version_id = _make_version()
    token_id = _make_token(status="confirmed")
    init_db()
    db = SessionLocal()
    try:
        result = evaluate_manual_dry_run_gate(ManualDryRunGateRequest(version_id=version_id, token_id=token_id, mode="dry_run", actor_id="operator_1", requested_target="mcp"), db)
        assert result.passed is False
        assert "requested_target_not_allowed:mcp" in result.blocking_reasons
    finally:
        db.close()
