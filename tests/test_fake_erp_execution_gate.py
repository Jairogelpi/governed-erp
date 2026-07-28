from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

from erpguard.db.models import ActionPlanStepToken, UISkillVersionRecord
from erpguard.db.repositories import (
    create_action_plan_step_token,
    create_active_skill_run,
    update_active_skill_run,
)
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.fake_erp_execution_gate import (
    FakeERPExecutionGateRequest,
    evaluate_fake_erp_execution_gate,
)
from erpguard.product.manual_dry_run_evidence import persist_manual_dry_run_evidence


def _make_version(*, steps_json: str, status: str = "active", is_active: bool = True, runtime_type: str = "deterministic_ui") -> str:
    init_db()
    db = SessionLocal()
    try:
        row = UISkillVersionRecord(
            id=f"ver_{uuid.uuid4().hex[:16]}",
            skill_id=f"skill_{uuid.uuid4().hex[:8]}",
            compiled_skill_id=f"comp_{uuid.uuid4().hex[:8]}",
            name="fake-erp-execution-skill",
            status=status,
            steps_json=steps_json,
            guard_names_json='["formula_guard"]',
            runtime_type=runtime_type,
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


def _make_completed_dry_run(*, version_id: str, with_evidence: bool = True, status: str = "completed") -> str:
    init_db()
    db = SessionLocal()
    try:
        version = db.get(UISkillVersionRecord, version_id)
        run = create_active_skill_run(
            db,
            version_id=version_id,
            skill_id=version.skill_id,
            actor="operator_1",
            target_base_url="manual://dry-run",
            inputs_json=json.dumps({"order_reference": "SO-VALID"}),
            gate_result_json="{}",
            input_validation_json='{"mode":"dry_run"}',
        )
        update_active_skill_run(
            db,
            run.id,
            status=status,
            summary_json=json.dumps({"mode": "dry_run", "result_summary": "ok"}),
            finished_at=datetime.now(timezone.utc),
        )
        if with_evidence:
            persist_manual_dry_run_evidence(
                run_id=run.id,
                version_id=version_id,
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
        return run.id
    finally:
        db.close()


def test_gate_passes_for_completed_manual_dry_run_and_allowlisted_fake_steps():
    version_id = _make_version(
        steps_json=json.dumps(
            [
                {"name": "Fake validate order", "operation": "fake_validate_order", "target": "fake_erp"},
                {"name": "Fake update status", "operation": "fake_update_sandbox_status", "target": "fake_erp"},
            ]
        )
    )
    token_id = _make_token(status="confirmed")
    dry_run_id = _make_completed_dry_run(version_id=version_id)
    init_db()
    db = SessionLocal()
    try:
        result = evaluate_fake_erp_execution_gate(
            FakeERPExecutionGateRequest(
                version_id=version_id,
                dry_run_id=dry_run_id,
                token_id=token_id,
                actor_id="operator_1",
                execution_target="fake_erp",
            ),
            db,
        )
        assert result.passed is True
        assert len(result.allowlisted_steps) == 2
    finally:
        db.close()


def test_pending_token_blocks():
    version_id = _make_version(steps_json='[{"name":"Fake","operation":"fake_validate_order","target":"fake_erp"}]')
    token_id = _make_token(status="pending")
    dry_run_id = _make_completed_dry_run(version_id=version_id)
    init_db()
    db = SessionLocal()
    try:
        result = evaluate_fake_erp_execution_gate(FakeERPExecutionGateRequest(version_id, dry_run_id, token_id, "operator_1", "fake_erp"), db)
        assert "token_not_confirmed:pending" in result.blocking_reasons
    finally:
        db.close()


def test_missing_actor_blocks():
    version_id = _make_version(steps_json='[{"name":"Fake","operation":"fake_validate_order","target":"fake_erp"}]')
    token_id = _make_token(status="confirmed")
    dry_run_id = _make_completed_dry_run(version_id=version_id)
    init_db()
    db = SessionLocal()
    try:
        result = evaluate_fake_erp_execution_gate(FakeERPExecutionGateRequest(version_id, dry_run_id, token_id, "", "fake_erp"), db)
        assert "actor_required" in result.blocking_reasons
    finally:
        db.close()


def test_dry_run_for_different_version_blocks():
    version_id = _make_version(steps_json='[{"name":"Fake","operation":"fake_validate_order","target":"fake_erp"}]')
    other_version_id = _make_version(steps_json='[{"name":"Fake","operation":"fake_validate_order","target":"fake_erp"}]')
    token_id = _make_token(status="confirmed")
    dry_run_id = _make_completed_dry_run(version_id=other_version_id)
    init_db()
    db = SessionLocal()
    try:
        result = evaluate_fake_erp_execution_gate(FakeERPExecutionGateRequest(version_id, dry_run_id, token_id, "operator_1", "fake_erp"), db)
        assert "dry_run_version_mismatch" in result.blocking_reasons
    finally:
        db.close()


def test_incomplete_dry_run_blocks():
    version_id = _make_version(steps_json='[{"name":"Fake","operation":"fake_validate_order","target":"fake_erp"}]')
    token_id = _make_token(status="confirmed")
    dry_run_id = _make_completed_dry_run(version_id=version_id, status="blocked")
    init_db()
    db = SessionLocal()
    try:
        result = evaluate_fake_erp_execution_gate(FakeERPExecutionGateRequest(version_id, dry_run_id, token_id, "operator_1", "fake_erp"), db)
        assert "dry_run_not_completed" in result.blocking_reasons
    finally:
        db.close()


def test_missing_dry_run_evidence_blocks():
    version_id = _make_version(steps_json='[{"name":"Fake","operation":"fake_validate_order","target":"fake_erp"}]')
    token_id = _make_token(status="confirmed")
    dry_run_id = _make_completed_dry_run(version_id=version_id, with_evidence=False)
    init_db()
    db = SessionLocal()
    try:
        result = evaluate_fake_erp_execution_gate(FakeERPExecutionGateRequest(version_id, dry_run_id, token_id, "operator_1", "fake_erp"), db)
        assert "dry_run_evidence_missing" in result.blocking_reasons
    finally:
        db.close()


def test_execution_target_not_fake_erp_blocks():
    version_id = _make_version(steps_json='[{"name":"Fake","operation":"fake_validate_order","target":"fake_erp"}]')
    token_id = _make_token(status="confirmed")
    dry_run_id = _make_completed_dry_run(version_id=version_id)
    init_db()
    db = SessionLocal()
    try:
        result = evaluate_fake_erp_execution_gate(FakeERPExecutionGateRequest(version_id, dry_run_id, token_id, "operator_1", "odoo"), db)
        assert "execution_target_not_allowed:odoo" in result.blocking_reasons
    finally:
        db.close()


def test_unsupported_runtime_blocks():
    version_id = _make_version(
        steps_json='[{"name":"Fake","operation":"fake_validate_order","target":"fake_erp"}]',
        runtime_type="deterministic_browser",
    )
    token_id = _make_token(status="confirmed")
    dry_run_id = _make_completed_dry_run(version_id=version_id)
    init_db()
    db = SessionLocal()
    try:
        result = evaluate_fake_erp_execution_gate(FakeERPExecutionGateRequest(version_id, dry_run_id, token_id, "operator_1", "fake_erp"), db)
        assert "unsupported_runtime_type" in result.blocking_reasons
    finally:
        db.close()


def test_non_allowlisted_step_blocks():
    version_id = _make_version(steps_json='[{"name":"Navigate","type":"navigate","target":"/fake-erp/sales/orders"}]')
    token_id = _make_token(status="confirmed")
    dry_run_id = _make_completed_dry_run(version_id=version_id)
    init_db()
    db = SessionLocal()
    try:
        result = evaluate_fake_erp_execution_gate(FakeERPExecutionGateRequest(version_id, dry_run_id, token_id, "operator_1", "fake_erp"), db)
        assert any(reason.startswith("step_not_fake_erp_allowlisted") for reason in result.blocking_reasons)
    finally:
        db.close()

