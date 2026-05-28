from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

from erpguard.db.models import FakeERPExecutionEvidencePack
from erpguard.db.models import ActionPlanStepToken, UISkillVersionRecord
from erpguard.db.repositories import (
    create_action_plan_step_token,
    create_fake_erp_execution_record,
    get_fake_erp_execution_evidence_pack,
)
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.fake_erp_evidence_pack import create_persisted_fake_erp_evidence_pack
from erpguard.product.fake_erp_execution_record import FakeERPExecutionCreateRequest, create_fake_erp_execution
from erpguard.product.manual_dry_run_evidence import persist_manual_dry_run_evidence
from erpguard.db.repositories import create_active_skill_run, update_active_skill_run


def _seed_execution(*, token_status: str = "confirmed", dry_run_status: str = "completed"):
    init_db()
    db = SessionLocal()
    try:
        version = UISkillVersionRecord(
            id=f"ver_{uuid.uuid4().hex[:16]}",
            skill_id=f"skill_{uuid.uuid4().hex[:8]}",
            compiled_skill_id=f"comp_{uuid.uuid4().hex[:8]}",
            name="fake-pack-skill",
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
            status=dry_run_status,
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
        execution = create_fake_erp_execution(
            FakeERPExecutionCreateRequest(
                version_id=version.id,
                dry_run_id=dry_run.id,
                token_id=token_id,
                actor={"type": "user", "id": "operator_1"},
                execution_target="fake_erp",
                inputs={"order_reference": "SO-VALID"},
            ),
            db,
        )
        return execution.execution_id
    finally:
        db.close()


def test_creates_persisted_pack_from_completed_execution():
    execution_id = _seed_execution()
    init_db()
    db = SessionLocal()
    try:
        result = create_persisted_fake_erp_evidence_pack(execution_id=execution_id, session=db)
        assert result.created is True
        assert result.pack_id.startswith("fepack_")
        row = get_fake_erp_execution_evidence_pack(db, result.pack_id)
        assert row is not None
    finally:
        db.close()


def test_missing_execution_blocks():
    init_db()
    db = SessionLocal()
    try:
        result = create_persisted_fake_erp_evidence_pack(execution_id="fexec_missing", session=db)
        assert result.created is False
        assert "execution_not_found" in result.blocking_reasons
    finally:
        db.close()


def test_incomplete_execution_blocks():
    init_db()
    db = SessionLocal()
    try:
        execution_id = f"fexec_incomplete_{uuid.uuid4().hex[:8]}"
        create_fake_erp_execution_record(
            db,
            execution_id=execution_id,
            version_id="ver_demo_1",
            skill_id="skill_demo_1",
            dry_run_id="dryrun_demo_1",
            actor_json='{"type":"user","id":"operator_1"}',
            execution_target="fake_erp",
            inputs_json='{"order_reference":"SO-VALID"}',
            status="running",
            step_count=1,
            steps_executed=0,
            steps_blocked=0,
            result_summary="still running",
            safety_summary_json="{}",
        )
    finally:
        db.close()
    init_db()
    db = SessionLocal()
    try:
        result = create_persisted_fake_erp_evidence_pack(execution_id=execution_id, session=db)
        assert result.created is False
        assert "execution_not_completed" in result.blocking_reasons
    finally:
        db.close()


def test_repeated_create_reuses_same_pack_id_without_duplicates():
    execution_id = _seed_execution()
    init_db()
    db = SessionLocal()
    try:
        first = create_persisted_fake_erp_evidence_pack(execution_id=execution_id, session=db)
        second = create_persisted_fake_erp_evidence_pack(execution_id=execution_id, session=db)
        assert first.created is True
        assert second.created is False
        assert second.pack_id == first.pack_id
        count = (
            db.query(FakeERPExecutionEvidencePack)
            .filter(FakeERPExecutionEvidencePack.execution_id == execution_id)
            .count()
        )
        assert count == 1
    finally:
        db.close()
