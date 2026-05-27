from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

from erpguard.db.models import ActionPlanStepToken, UISkillVersionRecord
from erpguard.db.repositories import (
    create_action_plan_step_token,
    create_active_skill_run,
    get_fake_erp_execution_record,
    update_active_skill_run,
)
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.fake_erp_execution_record import FakeERPExecutionCreateRequest, create_fake_erp_execution
from erpguard.product.manual_dry_run_evidence import persist_manual_dry_run_evidence


def _setup(*, steps_json: str, token_status: str = "confirmed"):
    init_db()
    db = SessionLocal()
    try:
        version = UISkillVersionRecord(
            id=f"ver_{uuid.uuid4().hex[:16]}",
            skill_id=f"skill_{uuid.uuid4().hex[:8]}",
            compiled_skill_id=f"comp_{uuid.uuid4().hex[:8]}",
            name="fake-erp-record-skill",
            status="active",
            steps_json=steps_json,
            guard_names_json='["formula_guard"]',
            runtime_type="deterministic_ui",
            llm_required=False,
            promotion_readiness_json="{}",
            is_active=True,
        )
        db.add(version)
        db.commit()
        token_id = f"tok_{uuid.uuid4().hex[:16]}"
        create_action_plan_step_token(
            db,
            token_id=token_id,
            plan_id="aplan_fake_erp_execution",
            step_number=5,
            step_title="Controlled Fake ERP execution",
            endpoint_hint="POST /v1/operator-console/action-plan/fake-erp-execution",
            method_hint="POST",
            severity="blocking",
            risk_level="medium",
            risk_summary="controlled fake erp execution",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        token = db.query(ActionPlanStepToken).filter(ActionPlanStepToken.id == token_id).first()
        token.status = token_status
        if token_status == "confirmed":
            token.confirmed_at = datetime.now(timezone.utc)
        if token_status == "expired":
            token.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)

        dry_run = create_active_skill_run(
            db,
            version_id=version.id,
            skill_id=version.skill_id,
            actor="operator_1",
            target_base_url="manual://dry-run",
            inputs_json=json.dumps({"order_reference": "SO-VALID"}),
            gate_result_json="{}",
            input_validation_json='{"mode":"dry_run"}',
        )
        update_active_skill_run(
            db,
            dry_run.id,
            status="completed",
            summary_json=json.dumps({"mode": "dry_run", "result_summary": "ok"}),
            finished_at=datetime.now(timezone.utc),
        )
        persist_manual_dry_run_evidence(
            run_id=dry_run.id,
            version_id=version.id,
            skill_id=version.skill_id,
            actor={"type": "user", "id": "operator_1"},
            mode="dry_run",
            inputs={"order_reference": "SO-VALID"},
            preview_reference_id=None,
            source_plan_id="aplan_1",
            source_step_number=4,
            gate_result={"passed": True},
            steps_json=version.steps_json,
            session=db,
        )
        db.commit()
        return version.id, token_id, dry_run.id
    finally:
        db.close()


def test_creates_controlled_fake_erp_execution_from_completed_manual_dry_run():
    version_id, token_id, dry_run_id = _setup(
        steps_json='[{"name":"Validate","operation":"fake_validate_order","target":"fake_erp"}]'
    )
    init_db()
    db = SessionLocal()
    try:
        result = create_fake_erp_execution(
            FakeERPExecutionCreateRequest(
                version_id=version_id,
                dry_run_id=dry_run_id,
                token_id=token_id,
                actor={"type": "user", "id": "operator_1"},
                execution_target="fake_erp",
                inputs={"order_reference": "SO-VALID"},
                reason="Operator approved controlled Fake ERP execution after dry-run evidence.",
            ),
            db,
        )
        assert result.status == "completed"
        assert result.execution_performed is True
        assert result.fake_erp_execution_performed is True
        assert result.real_erp_execution_performed is False
        row = get_fake_erp_execution_record(db, result.execution_id)
        assert row is not None
        assert row.steps_executed == 1
    finally:
        db.close()


def test_no_real_erp_browser_mcp_llm_scheduler_or_http_occurs():
    version_id, token_id, dry_run_id = _setup(
        steps_json='[{"name":"Validate","operation":"fake_validate_order","target":"fake_erp"}]'
    )
    init_db()
    db = SessionLocal()
    try:
        result = create_fake_erp_execution(
            FakeERPExecutionCreateRequest(
                version_id=version_id,
                dry_run_id=dry_run_id,
                token_id=token_id,
                actor={"type": "user", "id": "operator_1"},
                execution_target="fake_erp",
                inputs={"order_reference": "SO-VALID"},
            ),
            db,
        )
        assert result.odoo_execution_performed is False
        assert result.real_erp_execution_performed is False
        assert result.browser_control_performed is False
        assert result.mcp_execution_performed is False
        assert result.llm_runtime_used is False
        assert result.scheduler_used is False
        assert result.external_http_performed is False
    finally:
        db.close()

