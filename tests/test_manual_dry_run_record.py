from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

from erpguard.db.models import ActionPlanStepToken, UISkillVersionRecord
from erpguard.db.repositories import (
    create_action_plan_step_token,
    get_active_skill_run,
    get_manual_dry_run_evidence_for_run,
)
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.manual_dry_run_record import ManualDryRunCreateRequest, create_manual_dry_run_record


def _make_version(*, status: str = "active", is_active: bool = True) -> str:
    init_db()
    db = SessionLocal()
    try:
        row = UISkillVersionRecord(
            id=f"ver_{uuid.uuid4().hex[:16]}",
            skill_id=f"skill_{uuid.uuid4().hex[:8]}",
            compiled_skill_id=f"comp_{uuid.uuid4().hex[:8]}",
            name="manual-dry-run-record-skill",
            status=status,
            steps_json='[{"name":"Open sales order"},{"name":"Review formula"}]',
            guard_names_json='["formula_guard"]',
            runtime_type="deterministic_ui",
            llm_required=False,
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
        if status == "confirmed":
            row.confirmed_at = datetime.now(timezone.utc)
        if status == "expired":
            row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
        return token_id
    finally:
        db.close()


def test_creates_dry_run_record_for_eligible_active_governed_version():
    version_id = _make_version(status="active", is_active=True)
    token_id = _make_token(status="confirmed")
    init_db()
    db = SessionLocal()
    try:
        result = create_manual_dry_run_record(
            ManualDryRunCreateRequest(
                version_id=version_id,
                token_id=token_id,
                actor={"type": "user", "id": "operator_1", "display_name": "Operator"},
                source_plan_id="aplan_1",
                source_step_number=4,
                mode="dry_run",
                inputs={"order_reference": "SO-VALID"},
                reason="Operator requested dry-run",
            ),
            db,
        )
        assert result.status == "completed"
        assert result.active_skill_run_created is True
        assert result.simulation_performed is True
        assert result.execution_performed is False
        assert result.fake_erp_execution_performed is False
        assert result.odoo_execution_performed is False

        run = get_active_skill_run(db, result.run_id)
        assert run is not None
        assert run.status == "completed"
        summary = json.loads(run.summary_json)
        assert "No ERP action was executed" in summary["result_summary"]

        ev = get_manual_dry_run_evidence_for_run(db, result.run_id)
        assert ev is not None
    finally:
        db.close()


def test_no_erp_writes_or_browser_or_mcp_or_llm_or_scheduler_occurs():
    version_id = _make_version(status="active", is_active=True)
    token_id = _make_token(status="confirmed")
    init_db()
    db = SessionLocal()
    try:
        result = create_manual_dry_run_record(
            ManualDryRunCreateRequest(
                version_id=version_id,
                token_id=token_id,
                actor={"type": "user", "id": "operator_1"},
                mode="dry_run",
                inputs={"order_reference": "SO-VALID"},
            ),
            db,
        )
        assert result.erp_writes_performed is False
        assert result.browser_control_performed is False
        assert result.mcp_execution_performed is False
        assert result.llm_runtime_used is False
        assert result.scheduler_used is False
    finally:
        db.close()


def test_no_automatic_chaining_occurs_when_token_not_confirmed():
    version_id = _make_version(status="active", is_active=True)
    token_id = _make_token(status="pending")
    init_db()
    db = SessionLocal()
    try:
        result = create_manual_dry_run_record(
            ManualDryRunCreateRequest(
                version_id=version_id,
                token_id=token_id,
                actor={"type": "user", "id": "operator_1"},
                mode="dry_run",
            ),
            db,
        )
        assert result.status == "blocked"
        assert result.active_skill_run_created is False
        assert result.simulation_performed is False
    finally:
        db.close()
