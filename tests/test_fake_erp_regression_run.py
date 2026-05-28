from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

from erpguard.db.models import ActionPlanStepToken, UISkillVersionRecord
from erpguard.db.repositories import create_action_plan_step_token, create_active_skill_run, update_active_skill_run
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.fake_erp_regression_case import (
    FakeERPRegressionCaseCreateRequest,
    create_manual_fake_erp_regression_case,
)
from erpguard.product.fake_erp_regression_run import (
    FakeERPRegressionRunRequest,
    create_manual_fake_erp_regression_run,
)
from erpguard.product.manual_dry_run_evidence import persist_manual_dry_run_evidence


def _seed(*, token_status: str = "confirmed"):
    init_db()
    db = SessionLocal()
    try:
        version = UISkillVersionRecord(
            id=f"ver_{uuid.uuid4().hex[:16]}",
            skill_id=f"skill_{uuid.uuid4().hex[:8]}",
            compiled_skill_id=f"comp_{uuid.uuid4().hex[:8]}",
            name="fake-regression-run-skill",
            status="active",
            steps_json='[{"name":"Validate","operation":"fake_validate_order","target":"fake_erp"}]',
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
            plan_id="aplan_fake_regression",
            step_number=6,
            step_title="Manual fake erp regression",
            endpoint_hint="POST /v1/operator-console/fake-erp-regression/run",
            method_hint="POST",
            severity="blocking",
            risk_level="medium",
            risk_summary="manual fake erp regression",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        token = db.query(ActionPlanStepToken).filter(ActionPlanStepToken.id == token_id).first()
        token.status = token_status
        if token_status == "confirmed":
            token.confirmed_at = datetime.now(timezone.utc)
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
        case = create_manual_fake_erp_regression_case(
            FakeERPRegressionCaseCreateRequest(
                version_id=version.id,
                dry_run_id=dry_run.id,
                name="SO-VALID regression",
                inputs={"order_reference": "SO-VALID"},
                expected_outcomes={
                    "status": "completed",
                    "steps_executed": 1,
                    "steps_blocked": 0,
                    "execution_target": "fake_erp",
                },
            ),
            db,
        )
        return case.case_id, token_id
    finally:
        db.close()


def test_creates_manual_regression_run_with_completed_fake_erp_execution():
    case_id, token_id = _seed()
    init_db()
    db = SessionLocal()
    try:
        result = create_manual_fake_erp_regression_run(
            FakeERPRegressionRunRequest(
                case_id=case_id,
                token_id=token_id,
                actor={"type": "user", "id": "operator_1"},
                reason="Run regression",
            ),
            db,
        )
        assert result.execution_performed is True
        assert result.fake_erp_execution_performed is True
        assert result.matched is True
        assert result.odoo_execution_performed is False
        assert result.real_erp_execution_performed is False
        assert result.browser_control_performed is False
        assert result.mcp_execution_performed is False
        assert result.scheduler_used is False
        assert result.external_http_performed is False
    finally:
        db.close()


def test_pending_token_blocks_manual_regression_run():
    case_id, token_id = _seed(token_status="pending")
    init_db()
    db = SessionLocal()
    try:
        result = create_manual_fake_erp_regression_run(
            FakeERPRegressionRunRequest(
                case_id=case_id,
                token_id=token_id,
                actor={"type": "user", "id": "operator_1"},
            ),
            db,
        )
        assert result.status == "blocked"
        assert "token_not_confirmed:pending" in result.blocking_reasons
    finally:
        db.close()
