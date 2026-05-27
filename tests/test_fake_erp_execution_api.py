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
BASE = "/v1/operator-console/action-plan"


def _seed(*, steps_json: str, token_status: str = "confirmed", dry_run_status: str = "completed", with_evidence: bool = True):
    init_db()
    db = SessionLocal()
    try:
        version = UISkillVersionRecord(
            id=f"ver_{uuid.uuid4().hex[:16]}",
            skill_id=f"skill_{uuid.uuid4().hex[:8]}",
            compiled_skill_id=f"comp_{uuid.uuid4().hex[:8]}",
            name="fake-erp-api-skill",
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
            status=dry_run_status,
            summary_json=json.dumps({"mode": "dry_run", "result_summary": "ok"}),
            finished_at=datetime.now(timezone.utc),
        )
        if with_evidence:
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


def _request(version_id: str, dry_run_id: str, token_id: str, **overrides):
    body = {
        "version_id": version_id,
        "dry_run_id": dry_run_id,
        "token_id": token_id,
        "actor": {"type": "user", "id": "operator_1", "display_name": "Operator"},
        "execution_target": "fake_erp",
        "inputs": {"order_reference": "SO-VALID"},
        "reason": "Operator approved controlled Fake ERP execution after dry-run evidence.",
    }
    body.update(overrides)
    return body


def test_creates_controlled_fake_erp_execution_from_completed_manual_dry_run():
    version_id, token_id, dry_run_id = _seed(steps_json='[{"name":"Validate","operation":"fake_validate_order","target":"fake_erp"}]')
    r = client.post(f"{BASE}/fake-erp-execution", json=_request(version_id, dry_run_id, token_id))
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "completed"
    assert body["execution_performed"] is True
    assert body["fake_erp_execution_performed"] is True
    assert body["odoo_execution_performed"] is False
    assert body["real_erp_execution_performed"] is False


def test_pending_token_blocks():
    version_id, token_id, dry_run_id = _seed(steps_json='[{"name":"Validate","operation":"fake_validate_order","target":"fake_erp"}]', token_status="pending")
    r = client.post(f"{BASE}/fake-erp-execution", json=_request(version_id, dry_run_id, token_id))
    assert "token_not_confirmed:pending" in r.json()["blocking_reasons"]


def test_missing_dry_run_id_blocks():
    version_id, token_id, _ = _seed(steps_json='[{"name":"Validate","operation":"fake_validate_order","target":"fake_erp"}]')
    r = client.post(f"{BASE}/fake-erp-execution", json=_request(version_id, "dryrun_missing", token_id))
    assert "dry_run_not_found" in r.json()["blocking_reasons"]


def test_dry_run_for_different_version_blocks():
    version_id, token_id, dry_run_id = _seed(steps_json='[{"name":"Validate","operation":"fake_validate_order","target":"fake_erp"}]')
    other_version_id, _, _ = _seed(steps_json='[{"name":"Validate","operation":"fake_validate_order","target":"fake_erp"}]')
    r = client.post(f"{BASE}/fake-erp-execution", json=_request(other_version_id, dry_run_id, token_id))
    assert "dry_run_version_mismatch" in r.json()["blocking_reasons"]


def test_missing_dry_run_evidence_blocks():
    version_id, token_id, dry_run_id = _seed(
        steps_json='[{"name":"Validate","operation":"fake_validate_order","target":"fake_erp"}]',
        with_evidence=False,
    )
    r = client.post(f"{BASE}/fake-erp-execution", json=_request(version_id, dry_run_id, token_id))
    assert "dry_run_evidence_missing" in r.json()["blocking_reasons"]


def test_non_allowlisted_step_blocks():
    version_id, token_id, dry_run_id = _seed(steps_json='[{"name":"Navigate","type":"navigate","target":"/fake-erp/sales/orders"}]')
    r = client.post(f"{BASE}/fake-erp-execution", json=_request(version_id, dry_run_id, token_id))
    assert any(reason.startswith("step_not_fake_erp_allowlisted") for reason in r.json()["blocking_reasons"])


def test_result_retrieval_works():
    version_id, token_id, dry_run_id = _seed(steps_json='[{"name":"Validate","operation":"fake_validate_order","target":"fake_erp"}]')
    create = client.post(f"{BASE}/fake-erp-execution", json=_request(version_id, dry_run_id, token_id)).json()
    r = client.get(f"{BASE}/fake-erp-execution/{create['execution_id']}")
    assert r.status_code == 200
    assert r.json()["execution_id"] == create["execution_id"]


def test_audit_retrieval_works():
    version_id, token_id, dry_run_id = _seed(steps_json='[{"name":"Validate","operation":"fake_validate_order","target":"fake_erp"}]')
    client.post(f"{BASE}/fake-erp-execution", json=_request(version_id, dry_run_id, token_id))
    r = client.get(f"{BASE}/fake-erp-execution-audit")
    assert r.status_code == 200
    assert r.json()["event_count"] >= 1

