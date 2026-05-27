from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.db.models import ActionPlanStepToken, UISkillVersionRecord
from erpguard.db.repositories import create_action_plan_step_token
from erpguard.db.session import SessionLocal, init_db


client = TestClient(app)
BASE = "/v1/operator-console/action-plan"


def _make_version(*, status: str = "active", is_active: bool = True) -> str:
    init_db()
    db = SessionLocal()
    try:
        row = UISkillVersionRecord(
            id=f"ver_{uuid.uuid4().hex[:16]}",
            skill_id=f"skill_{uuid.uuid4().hex[:8]}",
            compiled_skill_id=f"comp_{uuid.uuid4().hex[:8]}",
            name="manual-dry-run-api-skill",
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


def _token(*, status: str = "confirmed") -> str:
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


def _request(version_id: str, token_id: str, **overrides):
    body = {
        "version_id": version_id,
        "token_id": token_id,
        "actor": {"type": "user", "id": "operator_1", "display_name": "Operator"},
        "source_plan_id": "aplan_1",
        "source_step_number": 4,
        "mode": "dry_run",
        "inputs": {"order_reference": "SO-VALID"},
        "reason": "Operator requested a dry-run evidence record after preview passed.",
        "requested_target": "simulation",
    }
    body.update(overrides)
    return body


def test_creates_dry_run_record_for_eligible_active_governed_version():
    version_id = _make_version(status="active", is_active=True)
    token_id = _token(status="confirmed")
    r = client.post(f"{BASE}/manual-dry-run", json=_request(version_id, token_id))
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "completed"
    assert body["mode"] == "dry_run"
    assert body["execution_performed"] is False
    assert body["simulation_performed"] is True
    assert body["active_skill_run_created"] is True
    assert body["fake_erp_execution_performed"] is False
    assert body["odoo_execution_performed"] is False
    assert body["audit_recorded"] is True
    assert body["evidence_id"]


def test_requires_confirmed_token():
    version_id = _make_version()
    token_id = _token(status="pending")
    r = client.post(f"{BASE}/manual-dry-run", json=_request(version_id, token_id))
    assert r.status_code == 200
    assert r.json()["status"] == "blocked"


def test_pending_token_blocks():
    version_id = _make_version()
    token_id = _token(status="pending")
    r = client.post(f"{BASE}/manual-dry-run", json=_request(version_id, token_id))
    assert "token_not_confirmed:pending" in r.json()["blocking_reasons"]


def test_expired_token_blocks():
    version_id = _make_version()
    token_id = _token(status="expired")
    r = client.post(f"{BASE}/manual-dry-run", json=_request(version_id, token_id))
    assert "token_not_confirmed:expired" in r.json()["blocking_reasons"]


def test_missing_actor_blocks():
    version_id = _make_version()
    token_id = _token(status="confirmed")
    body = _request(version_id, token_id)
    body["actor"] = {"type": "user", "id": "", "display_name": "Operator"}
    r = client.post(f"{BASE}/manual-dry-run", json=body)
    assert "actor_required" in r.json()["blocking_reasons"]


def test_missing_version_blocks():
    token_id = _token(status="confirmed")
    r = client.post(f"{BASE}/manual-dry-run", json=_request("ver_missing", token_id))
    assert r.status_code == 200
    assert r.json()["status"] == "blocked"


def test_invalid_version_blocks():
    version_id = _make_version(status="draft", is_active=False)
    token_id = _token(status="confirmed")
    r = client.post(f"{BASE}/manual-dry-run", json=_request(version_id, token_id))
    assert "version_not_active_governed" in r.json()["blocking_reasons"]


def test_non_dry_run_mode_blocks():
    version_id = _make_version()
    token_id = _token(status="confirmed")
    r = client.post(f"{BASE}/manual-dry-run", json=_request(version_id, token_id, mode="live_run"))
    assert "only_dry_run_mode_allowed" in r.json()["blocking_reasons"]


def test_requested_odoo_target_blocks():
    version_id = _make_version()
    token_id = _token(status="confirmed")
    r = client.post(f"{BASE}/manual-dry-run", json=_request(version_id, token_id, requested_target="odoo"))
    assert "requested_target_not_allowed:odoo" in r.json()["blocking_reasons"]


def test_requested_fake_erp_execution_blocks_in_sprint_47():
    version_id = _make_version()
    token_id = _token(status="confirmed")
    r = client.post(f"{BASE}/manual-dry-run", json=_request(version_id, token_id, requested_target="fake_erp"))
    assert "requested_target_not_allowed:fake_erp" in r.json()["blocking_reasons"]


def test_browser_target_blocks():
    version_id = _make_version()
    token_id = _token(status="confirmed")
    r = client.post(f"{BASE}/manual-dry-run", json=_request(version_id, token_id, requested_target="browser"))
    assert "requested_target_not_allowed:browser" in r.json()["blocking_reasons"]


def test_mcp_target_blocks():
    version_id = _make_version()
    token_id = _token(status="confirmed")
    r = client.post(f"{BASE}/manual-dry-run", json=_request(version_id, token_id, requested_target="mcp"))
    assert "requested_target_not_allowed:mcp" in r.json()["blocking_reasons"]


def test_no_erp_writes_browser_mcp_llm_scheduler_occurs():
    version_id = _make_version()
    token_id = _token(status="confirmed")
    r = client.post(f"{BASE}/manual-dry-run", json=_request(version_id, token_id))
    body = r.json()
    assert body["erp_writes_performed"] is False
    assert body["browser_control_performed"] is False
    assert body["mcp_execution_performed"] is False
    assert body["llm_runtime_used"] is False
    assert body["scheduler_used"] is False


def test_no_automatic_chaining_occurs():
    version_id = _make_version()
    token_id = _token(status="pending")
    r = client.post(f"{BASE}/manual-dry-run", json=_request(version_id, token_id))
    body = r.json()
    assert body["status"] == "blocked"
    assert body["active_skill_run_created"] is False


def test_result_retrieval_works():
    version_id = _make_version()
    token_id = _token(status="confirmed")
    create = client.post(f"{BASE}/manual-dry-run", json=_request(version_id, token_id)).json()
    run_id = create["run_id"]
    r = client.get(f"{BASE}/manual-dry-run/{run_id}")
    assert r.status_code == 200
    assert r.json()["run_id"] == run_id


def test_audit_retrieval_works():
    version_id = _make_version()
    token_id = _token(status="confirmed")
    client.post(f"{BASE}/manual-dry-run", json=_request(version_id, token_id))
    r = client.get(f"{BASE}/manual-dry-run-audit")
    assert r.status_code == 200
    body = r.json()
    assert body["event_count"] >= 1
    assert "entries" in body


def test_blocked_gate_creates_audit():
    version_id = _make_version()
    token_id = _token(status="pending")
    client.post(f"{BASE}/manual-dry-run", json=_request(version_id, token_id))
    r = client.get(f"{BASE}/manual-dry-run-audit")
    assert any(e["event_type"] in {"gate_blocked", "blocked"} for e in r.json()["entries"])
