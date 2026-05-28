from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.db.models import ActionPlanStepToken, UISkillVersionRecord
from erpguard.db.repositories import create_action_plan_step_token, create_active_skill_run, update_active_skill_run
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.manual_dry_run_evidence import persist_manual_dry_run_evidence


client = TestClient(app)
BASE = "/v1/operator-console/fake-erp-regression"


def _seed():
    init_db()
    db = SessionLocal()
    try:
        version = UISkillVersionRecord(
            id=f"ver_{uuid.uuid4().hex[:16]}",
            skill_id=f"skill_{uuid.uuid4().hex[:8]}",
            compiled_skill_id=f"comp_{uuid.uuid4().hex[:8]}",
            name="fake-regression-api-skill",
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
        return version.id, dry_run.id, token_id
    finally:
        db.close()


def test_create_run_get_and_audit_regression_case():
    version_id, dry_run_id, token_id = _seed()
    create_case = client.post(
        f"{BASE}/cases",
        json={
            "version_id": version_id,
            "dry_run_id": dry_run_id,
            "name": "SO-VALID regression",
            "execution_target": "fake_erp",
            "inputs": {"order_reference": "SO-VALID"},
            "expected_outcomes": {
                "status": "completed",
                "steps_executed": 1,
                "steps_blocked": 0,
                "execution_target": "fake_erp",
            },
        },
    )
    assert create_case.status_code == 200
    case_id = create_case.json()["case_id"]
    get_case = client.get(f"{BASE}/cases/{case_id}")
    assert get_case.status_code == 200
    run = client.post(
        f"{BASE}/run",
        json={
            "case_id": case_id,
            "token_id": token_id,
            "actor": {"type": "user", "id": "operator_1", "display_name": "Operator"},
            "reason": "Run regression",
        },
    )
    assert run.status_code == 200
    run_body = run.json()
    assert run_body["fake_erp_execution_performed"] is True
    assert run_body["odoo_execution_performed"] is False
    assert run_body["real_erp_execution_performed"] is False
    get_run = client.get(f"{BASE}/runs/{run_body['regression_run_id']}")
    assert get_run.status_code == 200
    audit = client.get(f"{BASE}/audit")
    assert audit.status_code == 200
    assert audit.json()["event_count"] >= 1
