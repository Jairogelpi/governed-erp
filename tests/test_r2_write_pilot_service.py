from __future__ import annotations

import pytest

from erpguard.db.session import SessionLocal, init_db
from erpguard.db.repositories import create_skill, create_skill_version
from erpguard.product.r2_write_policy import R2WritePilotPolicyService
from erpguard.product.r2_write_request import R2WritePilotRequestService
from erpguard.product.r2_write_executor import R2WritePilotExecutorService
from erpguard.adapters.odoo.r2_write_client import (
    OdooR2WriteClient, R2WriteViolationError,
    R2_ALLOWED_WRITE_MODELS, R2_ALLOWED_WRITE_FIELDS,
)
import json


@pytest.fixture(autouse=True)
def db_session():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


def _make_skill(db_session) -> str:
    skill = create_skill(db_session, name="R2 Test Skill", description=None)
    create_skill_version(
        db_session, skill.id, "1.0",
        json.dumps({"guards": [], "steps": []}),
        "deterministic_browser", False,
    )
    return skill.id


# ── R2 write client ────────────────────────────────────────────────────────

class TestOdooR2WriteClient:
    def test_allowed_models(self):
        assert "res.partner" in R2_ALLOWED_WRITE_MODELS

    def test_allowed_fields(self):
        assert "comment" in R2_ALLOWED_WRITE_FIELDS
        assert "website" in R2_ALLOWED_WRITE_FIELDS

    def test_disallowed_model_raises(self, monkeypatch):
        from erpguard.adapters.odoo.readonly_client import OdooReadOnlyClient
        mock_client = object.__new__(OdooReadOnlyClient)
        client = object.__new__(OdooR2WriteClient)
        client._client = mock_client
        with pytest.raises(R2WriteViolationError, match="not on the R2 pilot write whitelist"):
            client.write("sale.order", 1, {"state": "sale"})

    def test_disallowed_field_raises(self, monkeypatch):
        from erpguard.adapters.odoo.readonly_client import OdooReadOnlyClient
        mock_client = object.__new__(OdooReadOnlyClient)
        client = object.__new__(OdooR2WriteClient)
        client._client = mock_client
        with pytest.raises(R2WriteViolationError, match="not on the R2 allowed field list"):
            client.write("res.partner", 1, {"name": "Evil Name", "comment": "ok"})


# ── R2 policy service ──────────────────────────────────────────────────────

class TestR2WritePilotPolicyService:
    def test_blocked_by_feature_flag(self, db_session):
        skill_id = _make_skill(db_session)
        svc = R2WritePilotPolicyService(db_session)
        result = svc.check(
            skill_id=skill_id,
            request_id="req_test",
            target_model="res.partner",
            target_fields=["comment"],
            environment="staging",
            approver_1_id="user_1",
            approver_2_id="user_2",
        )
        assert result.passed is False
        codes = [v.code for v in result.violations]
        assert "feature_flag_disabled" in codes

    def test_passes_when_flag_enabled(self, db_session, monkeypatch):
        monkeypatch.setattr("erpguard.product.r2_write_policy._ALLOW_R2_REAL_WRITE_PILOT", True)
        skill_id = _make_skill(db_session)
        # create write readiness certification
        from erpguard.db.repositories import create_write_readiness_certification
        create_write_readiness_certification(
            db_session, skill_id=skill_id, assessment_id="assess_1",
            certification_status="certified", overall_risk_level="R2",
            evidence_json=json.dumps({"certified": True}),
        )
        svc = R2WritePilotPolicyService(db_session)
        result = svc.check(
            skill_id=skill_id,
            request_id="req_test",
            target_model="res.partner",
            target_fields=["comment"],
            environment="staging",
            approver_1_id="user_1",
            approver_2_id="user_2",
        )
        assert result.passed is True
        assert result.violations == []

    def test_blocked_wrong_model(self, db_session, monkeypatch):
        monkeypatch.setattr("erpguard.product.r2_write_policy._ALLOW_R2_REAL_WRITE_PILOT", True)
        skill_id = _make_skill(db_session)
        svc = R2WritePilotPolicyService(db_session)
        result = svc.check(
            skill_id=skill_id, request_id="r",
            target_model="sale.order", target_fields=["state"],
            environment="staging", approver_1_id="a", approver_2_id="b",
        )
        assert result.passed is False
        assert any(v.code == "model_not_whitelisted" for v in result.violations)

    def test_blocked_disallowed_field(self, db_session, monkeypatch):
        monkeypatch.setattr("erpguard.product.r2_write_policy._ALLOW_R2_REAL_WRITE_PILOT", True)
        skill_id = _make_skill(db_session)
        svc = R2WritePilotPolicyService(db_session)
        result = svc.check(
            skill_id=skill_id, request_id="r",
            target_model="res.partner", target_fields=["name"],
            environment="staging", approver_1_id="a", approver_2_id="b",
        )
        assert result.passed is False
        assert any(v.code == "fields_not_whitelisted" for v in result.violations)

    def test_blocked_production_environment(self, db_session, monkeypatch):
        monkeypatch.setattr("erpguard.product.r2_write_policy._ALLOW_R2_REAL_WRITE_PILOT", True)
        skill_id = _make_skill(db_session)
        svc = R2WritePilotPolicyService(db_session)
        result = svc.check(
            skill_id=skill_id, request_id="r",
            target_model="res.partner", target_fields=["comment"],
            environment="production", approver_1_id="a", approver_2_id="b",
        )
        assert result.passed is False
        assert any(v.code == "environment_not_allowed" for v in result.violations)

    def test_blocked_same_approver_twice(self, db_session, monkeypatch):
        monkeypatch.setattr("erpguard.product.r2_write_policy._ALLOW_R2_REAL_WRITE_PILOT", True)
        skill_id = _make_skill(db_session)
        svc = R2WritePilotPolicyService(db_session)
        result = svc.check(
            skill_id=skill_id, request_id="r",
            target_model="res.partner", target_fields=["comment"],
            environment="staging", approver_1_id="same", approver_2_id="same",
        )
        assert result.passed is False
        assert any(v.code == "duplicate_approvers" for v in result.violations)

    def test_target_model_whitelisted_flag(self, db_session):
        svc = R2WritePilotPolicyService(db_session)
        result = svc.check(
            skill_id="skill_x", request_id="r",
            target_model="res.partner", target_fields=["comment"],
            environment="staging", approver_1_id="a", approver_2_id="b",
        )
        assert result.target_model_whitelisted is True

    def test_generic_writes_always_false(self, db_session):
        svc = R2WritePilotPolicyService(db_session)
        result = svc.check(
            skill_id="s", request_id="r",
            target_model="res.partner", target_fields=["comment"],
            environment="staging", approver_1_id="a", approver_2_id="b",
        )
        assert result.allow_generic_real_odoo_writes is False
        assert result.allow_r3_r4_real_writes is False


# ── R2 request service ─────────────────────────────────────────────────────

class TestR2WritePilotRequestService:
    def test_create_request(self, db_session):
        skill_id = _make_skill(db_session)
        svc = R2WritePilotRequestService(db_session)
        model, is_dup = svc.create(
            skill_id=skill_id,
            requested_by={"id": "op1"},
            approver_1={"id": "ap1"},
            approver_2={"id": "ap2"},
            target_record_id=42,
            vals={"comment": "test note"},
            environment="staging",
        )
        assert model.request_id.startswith("r2req_")
        assert model.target_model == "res.partner"
        assert model.target_record_id == 42
        assert "comment" in model.target_fields
        assert model.environment == "staging"
        assert model.allow_generic_real_odoo_writes is False
        assert model.allow_r3_r4_real_writes is False
        assert is_dup is False

    def test_idempotency_returns_same(self, db_session):
        skill_id = _make_skill(db_session)
        svc = R2WritePilotRequestService(db_session)
        m1, _ = svc.create(skill_id=skill_id, requested_by={}, approver_1={"id":"a"}, approver_2={"id":"b"},
                            target_record_id=1, vals={"comment": "x"}, environment="staging")
        m2, is_dup = svc.create(skill_id=skill_id, requested_by={}, approver_1={"id":"a"}, approver_2={"id":"b"},
                                 target_record_id=1, vals={"comment": "x"}, environment="staging")
        assert m1.request_id == m2.request_id
        assert is_dup is True

    def test_disallowed_field_raises(self, db_session):
        skill_id = _make_skill(db_session)
        svc = R2WritePilotRequestService(db_session)
        with pytest.raises(ValueError, match="not allowed for R2 write"):
            svc.create(skill_id=skill_id, requested_by={}, approver_1={"id":"a"}, approver_2={"id":"b"},
                       target_record_id=1, vals={"name": "Evil"}, environment="staging")

    def test_get_request(self, db_session):
        skill_id = _make_skill(db_session)
        svc = R2WritePilotRequestService(db_session)
        m, _ = svc.create(skill_id=skill_id, requested_by={}, approver_1={"id":"a"}, approver_2={"id":"b"},
                           target_record_id=5, vals={"website": "https://example.com"}, environment="demo")
        fetched = svc.get(m.request_id)
        assert fetched.request_id == m.request_id
        assert fetched.environment == "demo"

    def test_list_for_skill(self, db_session):
        skill_id = _make_skill(db_session)
        svc = R2WritePilotRequestService(db_session)
        svc.create(skill_id=skill_id, requested_by={}, approver_1={"id":"a"}, approver_2={"id":"b"},
                   target_record_id=1, vals={"comment": "one"}, environment="staging")
        svc.create(skill_id=skill_id, requested_by={}, approver_1={"id":"a"}, approver_2={"id":"b"},
                   target_record_id=2, vals={"comment": "two"}, environment="staging")
        requests = svc.list_for_skill(skill_id)
        assert len(requests) >= 2


# ── R2 executor service ────────────────────────────────────────────────────

class TestR2WritePilotExecutorService:
    def test_blocked_by_default(self, db_session):
        skill_id = _make_skill(db_session)
        req, _ = R2WritePilotRequestService(db_session).create(
            skill_id=skill_id, requested_by={},
            approver_1={"id": "a"}, approver_2={"id": "b"},
            target_record_id=1, vals={"comment": "blocked test"}, environment="staging",
        )
        run = R2WritePilotExecutorService(db_session).execute(req.request_id)
        assert run.status == "blocked"
        assert run.executed_action == "blocked_by_feature_flag"
        assert run.allow_r2_real_write_pilot is False
        assert run.allow_generic_real_odoo_writes is False
        assert run.allow_r3_r4_real_writes is False

    def test_idempotent_blocked_run(self, db_session):
        skill_id = _make_skill(db_session)
        req, _ = R2WritePilotRequestService(db_session).create(
            skill_id=skill_id, requested_by={},
            approver_1={"id": "a"}, approver_2={"id": "b"},
            target_record_id=1, vals={"comment": "idem test"}, environment="staging",
        )
        svc = R2WritePilotExecutorService(db_session)
        run1 = svc.execute(req.request_id)
        run2 = svc.execute(req.request_id)
        assert run1.run_id == run2.run_id

    def test_get_run(self, db_session):
        skill_id = _make_skill(db_session)
        req, _ = R2WritePilotRequestService(db_session).create(
            skill_id=skill_id, requested_by={},
            approver_1={"id": "a"}, approver_2={"id": "b"},
            target_record_id=3, vals={"comment": "get run test"}, environment="staging",
        )
        svc = R2WritePilotExecutorService(db_session)
        run = svc.execute(req.request_id)
        fetched = svc.get(run.run_id)
        assert fetched.run_id == run.run_id
        assert fetched.status == "blocked"

    def test_evidence_stored_on_blocked_run(self, db_session):
        skill_id = _make_skill(db_session)
        req, _ = R2WritePilotRequestService(db_session).create(
            skill_id=skill_id, requested_by={},
            approver_1={"id": "a"}, approver_2={"id": "b"},
            target_record_id=4, vals={"comment": "evidence test"}, environment="staging",
        )
        svc = R2WritePilotExecutorService(db_session)
        run = svc.execute(req.request_id)
        evidence = svc.get_evidence(run.run_id)
        assert len(evidence) == 1
        ev = evidence[0]
        assert ev.action_taken == "blocked_by_feature_flag"
        assert ev.target_model == "res.partner"
        assert ev.target_record_id == "4"
        assert "rollback_instructions" in ev.model_dump()
        assert ev.allow_r2_real_write_pilot is False
        assert ev.allow_generic_real_odoo_writes is False

    def test_pre_snapshot_captured(self, db_session):
        skill_id = _make_skill(db_session)
        req, _ = R2WritePilotRequestService(db_session).create(
            skill_id=skill_id, requested_by={},
            approver_1={"id": "a"}, approver_2={"id": "b"},
            target_record_id=5, vals={"comment": "snapshot test"}, environment="staging",
        )
        svc = R2WritePilotExecutorService(db_session)
        run = svc.execute(req.request_id)
        assert "target_model" in run.pre_snapshot
        assert run.pre_snapshot["target_model"] == "res.partner"

    def test_rollback_instructions_in_evidence(self, db_session):
        skill_id = _make_skill(db_session)
        req, _ = R2WritePilotRequestService(db_session).create(
            skill_id=skill_id, requested_by={},
            approver_1={"id": "a"}, approver_2={"id": "b"},
            target_record_id=6, vals={"website": "https://test.com"}, environment="staging",
        )
        svc = R2WritePilotExecutorService(db_session)
        run = svc.execute(req.request_id)
        evidence = svc.get_evidence(run.run_id)
        rollback = evidence[0].rollback_instructions
        assert "action" in rollback
        assert "model" in rollback
        assert rollback["model"] == "res.partner"
