from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.db.models import ActionPlanStepToken, UISkillVersionRecord
from erpguard.db.repositories import create_action_plan_step_token
from erpguard.db.session import SessionLocal, init_db
from erpguard.db.repositories import create_active_skill_run, update_active_skill_run
from erpguard.product.fake_erp_execution_record import FakeERPExecutionCreateRequest, create_fake_erp_execution
from erpguard.product.manual_dry_run_evidence import persist_manual_dry_run_evidence


client = TestClient(app)
BASE = "/v1/operator-console/action-plan"


def _seed_execution():
    init_db()
    db = SessionLocal()
    try:
        version = UISkillVersionRecord(
            id=f"ver_{uuid.uuid4().hex[:16]}",
            skill_id=f"skill_{uuid.uuid4().hex[:8]}",
            compiled_skill_id=f"comp_{uuid.uuid4().hex[:8]}",
            name="fake-pack-api-skill",
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
        token.status = "confirmed"
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


def test_create_and_get_evidence_pack():
    execution_id = _seed_execution()
    created = client.post(f"{BASE}/fake-erp-evidence-pack", json={"execution_id": execution_id})
    assert created.status_code == 200
    body = created.json()
    assert body["created"] is True
    pack_id = body["pack_id"]

    fetched = client.get(f"{BASE}/fake-erp-evidence-pack/{pack_id}")
    assert fetched.status_code == 200
    assert fetched.json()["pack_id"] == pack_id


def test_get_latest_pack_for_execution():
    execution_id = _seed_execution()
    client.post(f"{BASE}/fake-erp-evidence-pack", json={"execution_id": execution_id})
    r = client.get(f"{BASE}/fake-erp-execution/{execution_id}/evidence-pack")
    assert r.status_code == 200
    assert r.json()["execution_id"] == execution_id


def test_missing_execution_blocks_pack_creation():
    r = client.post(f"{BASE}/fake-erp-evidence-pack", json={"execution_id": "fexec_missing"})
    assert r.status_code == 200
    assert "execution_not_found" in r.json()["blocking_reasons"]

