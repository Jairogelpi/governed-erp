from __future__ import annotations

import json
import pytest

from erpguard.db.session import SessionLocal, init_db
from erpguard.db.repositories import (
    create_skill, create_skill_version,
    create_r2_write_pilot_run, create_r2_write_pilot_evidence,
)
from erpguard.product.r2_evidence_review import R2EvidenceReviewService, _compute_delta
from erpguard.product.r2_rollback_rehearsal import R2RollbackRehearsalService
from erpguard.product.r2_execution_report import R2ExecutionReportService
from erpguard.product.r2_promotion_gate import R2PromotionGateService


@pytest.fixture(autouse=True)
def db_session():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


def _make_run(db_session, *, status="blocked", allow_r2=False,
              pre_fields=None, post_fields=None) -> str:
    skill = create_skill(db_session, name="R11 Test Skill", description=None)
    create_skill_version(db_session, skill.id, "1.0", "{}", "deterministic_browser", False)

    pre_snap = {"target_model": "res.partner", "target_record_id": 1, "field_values": pre_fields or {}}
    post_snap = {"target_model": "res.partner", "target_record_id": 1, "field_values": post_fields or {}}

    run = create_r2_write_pilot_run(
        db_session,
        request_id=f"r2req_test_{skill.id[:8]}",
        skill_id=skill.id,
        status=status,
        executed_action="blocked_by_feature_flag" if status == "blocked" else "res.partner.write",
        pre_snapshot_json=json.dumps(pre_snap),
        post_snapshot_json=json.dumps(post_snap),
        result_json=json.dumps({"blocked": True}),
        policy_passed=False,
        allow_r2_real_write_pilot=allow_r2,
    )

    rollback = {
        "action": "re-write original field values",
        "model": "res.partner",
        "record_id": 1,
        "restore_vals": pre_fields or {},
        "odoo_call": "env['res.partner'].browse(1).write({})",
        "notes": "test",
    }
    create_r2_write_pilot_evidence(
        db_session,
        run_id=run.id,
        request_id=run.request_id,
        skill_id=skill.id,
        action_taken="blocked_by_feature_flag",
        target_model="res.partner",
        target_record_id="1",
        pre_snapshot_json=json.dumps(pre_snap),
        post_snapshot_json=json.dumps(post_snap),
        rollback_instructions_json=json.dumps(rollback),
        idempotency_key=f"r2_idem_{skill.id[:16]}",
        allow_r2_real_write_pilot=allow_r2,
    )
    return run.id


# ── _compute_delta helper ──────────────────────────────────────────────────

class TestComputeDelta:
    def test_no_change(self):
        delta, changed, unchanged, drift = _compute_delta({"comment": "x"}, {"comment": "x"})
        assert changed == 0
        assert unchanged == 1
        assert drift == []

    def test_field_changed(self):
        delta, changed, unchanged, drift = _compute_delta({"comment": "old"}, {"comment": "new"})
        assert changed == 1
        assert delta["comment"] == {"before": "old", "after": "new"}

    def test_empty_snapshots(self):
        delta, changed, unchanged, drift = _compute_delta({}, {})
        assert changed == 0
        assert unchanged == 0


# ── R2EvidenceReviewService ────────────────────────────────────────────────

class TestR2EvidenceReviewService:
    def test_creates_review_for_blocked_run(self, db_session):
        run_id = _make_run(db_session)
        svc = R2EvidenceReviewService(db_session)
        result = svc.get_or_create(run_id)
        assert result["run_id"] == run_id
        assert "review_id" in result
        assert result["review_id"].startswith("r2review_")
        assert result["status"] == "completed"

    def test_idempotent_on_second_call(self, db_session):
        run_id = _make_run(db_session)
        svc = R2EvidenceReviewService(db_session)
        r1 = svc.get_or_create(run_id)
        r2 = svc.get_or_create(run_id)
        assert r1["review_id"] == r2["review_id"]

    def test_no_drift_when_snapshots_equal(self, db_session):
        run_id = _make_run(db_session, pre_fields={"comment": "x"}, post_fields={"comment": "x"})
        result = R2EvidenceReviewService(db_session).get_or_create(run_id)
        assert result["drift_detected"] is False
        assert result["fields_changed"] == 0

    def test_drift_when_field_missing_post(self, db_session):
        run_id = _make_run(db_session, pre_fields={"comment": "x"}, post_fields={})
        result = R2EvidenceReviewService(db_session).get_or_create(run_id)
        assert result["fields_changed"] == 1

    def test_safety_invariants_always_false(self, db_session):
        run_id = _make_run(db_session)
        result = R2EvidenceReviewService(db_session).get_or_create(run_id)
        inv = result["safety_invariants"]
        assert inv["can_execute_real_writes"] is False
        assert inv["allow_generic_real_odoo_writes"] is False
        assert inv["allow_r3_r4_real_writes"] is False

    def test_run_not_found_raises(self, db_session):
        from erpguard.core.errors import ObjectNotFoundError
        with pytest.raises(ObjectNotFoundError):
            R2EvidenceReviewService(db_session).get_or_create("r2run_nonexistent")

    def test_rollback_instructions_included(self, db_session):
        run_id = _make_run(db_session)
        result = R2EvidenceReviewService(db_session).get_or_create(run_id)
        ri = result["rollback_instructions"]
        assert "model" in ri or ri == {}


# ── R2RollbackRehearsalService ─────────────────────────────────────────────

class TestR2RollbackRehearsalService:
    def test_rehearsal_passes_with_complete_instructions(self, db_session):
        run_id = _make_run(db_session, pre_fields={"comment": "old"})
        result = R2RollbackRehearsalService(db_session).rehearse(run_id)
        assert result["rehearsal_id"].startswith("r2reh_")
        assert result["instructions_valid"] is True
        assert result["rehearsal_passed"] is True
        assert result["missing_fields"] == []

    def test_dry_run_steps_present(self, db_session):
        run_id = _make_run(db_session, pre_fields={"comment": "x"})
        result = R2RollbackRehearsalService(db_session).rehearse(run_id)
        assert len(result["dry_run_steps"]) >= 3

    def test_real_rollback_never_executed(self, db_session):
        run_id = _make_run(db_session)
        result = R2RollbackRehearsalService(db_session).rehearse(run_id)
        assert result["real_rollback_executed"] is False

    def test_idempotent_second_call(self, db_session):
        run_id = _make_run(db_session)
        svc = R2RollbackRehearsalService(db_session)
        r1 = svc.rehearse(run_id)
        r2 = svc.rehearse(run_id)
        assert r1["rehearsal_id"] == r2["rehearsal_id"]

    def test_safety_invariants_always_false(self, db_session):
        run_id = _make_run(db_session)
        result = R2RollbackRehearsalService(db_session).rehearse(run_id)
        inv = result["safety_invariants"]
        assert inv["can_execute_real_writes"] is False
        assert inv["allow_generic_real_odoo_writes"] is False


# ── R2ExecutionReportService ───────────────────────────────────────────────

class TestR2ExecutionReportService:
    def test_generates_report(self, db_session):
        run_id = _make_run(db_session)
        result = R2ExecutionReportService(db_session).get_or_generate(run_id)
        assert result["report_id"].startswith("r2report_")
        assert result["run_id"] == run_id
        assert result["status"] == "completed"
        assert isinstance(result["residual_risk_score"], int)
        assert result["risk_level"] in ("none", "low", "medium", "high")

    def test_blocked_run_has_zero_residual_risk(self, db_session):
        run_id = _make_run(db_session, status="blocked")
        result = R2ExecutionReportService(db_session).get_or_generate(run_id)
        assert result["residual_risk_score"] == 0
        assert result["risk_level"] == "none"

    def test_idempotent_on_second_call(self, db_session):
        run_id = _make_run(db_session)
        svc = R2ExecutionReportService(db_session)
        r1 = svc.get_or_generate(run_id)
        r2 = svc.get_or_generate(run_id)
        assert r1["report_id"] == r2["report_id"]

    def test_report_contains_audit_notes(self, db_session):
        run_id = _make_run(db_session)
        result = R2ExecutionReportService(db_session).get_or_generate(run_id)
        notes = result["report"].get("audit_notes", [])
        assert any("ALLOW_GENERIC_REAL_ODOO_WRITES=false" in note for note in notes)
        assert any("ALLOW_R3_R4_REAL_WRITES=false" in note for note in notes)


# ── R2PromotionGateService ─────────────────────────────────────────────────

class TestR2PromotionGateService:
    def test_gate_blocked_without_review(self, db_session):
        run_id = _make_run(db_session)
        result = R2PromotionGateService(db_session).evaluate(run_id)
        assert result["gate_id"].startswith("r2gate_")
        assert result["blocked"] is True
        assert result["gate_status"] == "blocked"
        reasons = result["blocking_reasons"]
        assert any("evidence_review" in r for r in reasons)

    def test_gate_passed_after_all_checks(self, db_session):
        run_id = _make_run(db_session, status="blocked")
        svc_review = R2EvidenceReviewService(db_session)
        svc_rehearsal = R2RollbackRehearsalService(db_session)
        svc_report = R2ExecutionReportService(db_session)
        svc_review.get_or_create(run_id)
        svc_rehearsal.rehearse(run_id)
        svc_report.get_or_generate(run_id)
        result = R2PromotionGateService(db_session).evaluate(run_id)
        assert result["blocked"] is False
        assert result["gate_status"] == "passed"

    def test_gate_checks_include_generic_writes_lock(self, db_session):
        run_id = _make_run(db_session)
        result = R2PromotionGateService(db_session).evaluate(run_id)
        check_names = [c["name"] for c in result["checks"]]
        assert "generic_writes_locked" in check_names
        assert "r3_r4_writes_locked" in check_names
        generic_check = next(c for c in result["checks"] if c["name"] == "generic_writes_locked")
        assert generic_check["passed"] is True
        r3r4_check = next(c for c in result["checks"] if c["name"] == "r3_r4_writes_locked")
        assert r3r4_check["passed"] is True

    def test_idempotent_second_call(self, db_session):
        run_id = _make_run(db_session)
        svc = R2PromotionGateService(db_session)
        r1 = svc.evaluate(run_id)
        r2 = svc.evaluate(run_id)
        assert r1["gate_id"] == r2["gate_id"]

    def test_safety_invariants_always_false(self, db_session):
        run_id = _make_run(db_session)
        result = R2PromotionGateService(db_session).evaluate(run_id)
        inv = result["safety_invariants"]
        assert inv["allow_generic_real_odoo_writes"] is False
        assert inv["allow_r3_r4_real_writes"] is False
        assert inv["can_execute_real_writes"] is False
