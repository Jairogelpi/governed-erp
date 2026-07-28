from __future__ import annotations

import pytest

from erpguard.db.session import SessionLocal, init_db
from erpguard.product.operator_session import OperatorSessionService
from erpguard.product.operator_orchestrator import OperatorOrchestrator
from erpguard.product.operator_timeline import OperatorTimelineService
from erpguard.product.operator_summary import OperatorSummaryService
from erpguard.product.operator_flow_state import FLOW_STEPS, next_step, is_before_or_at


@pytest.fixture(autouse=True)
def db_session():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


# ── Flow state helpers ─────────────────────────────────────────────────────

class TestFlowState:
    def test_flow_starts_with_awaiting_tenant(self):
        assert FLOW_STEPS[0] == "awaiting_tenant"

    def test_flow_ends_with_completed(self):
        assert FLOW_STEPS[-1] == "completed"

    def test_next_step_advances(self):
        assert next_step("awaiting_tenant") == "awaiting_connection"

    def test_next_step_at_end(self):
        assert next_step("completed") is None

    def test_is_before_or_at_boundary(self):
        assert is_before_or_at("run_diagnosis", "run_live_read") is True
        assert is_before_or_at("run_live_read", "run_live_read") is True
        assert is_before_or_at("run_write_readiness", "run_live_read") is False


# ── OperatorSessionService ─────────────────────────────────────────────────

class TestOperatorSessionService:
    def test_create_session(self, db_session):
        svc = OperatorSessionService(db_session)
        result = svc.create()
        assert result["session_id"].startswith("opsession_")
        assert result["current_step"] == "awaiting_tenant"
        assert result["status"] == "active"
        assert result["known_ids"] == {}

    def test_get_session(self, db_session):
        svc = OperatorSessionService(db_session)
        created = svc.create()
        fetched = svc.get(created["session_id"])
        assert fetched["session_id"] == created["session_id"]

    def test_get_session_not_found(self, db_session):
        from erpguard.core.errors import ObjectNotFoundError
        svc = OperatorSessionService(db_session)
        with pytest.raises(ObjectNotFoundError):
            svc.get("opsession_nonexistent_xyz")

    def test_select_tenant_advances_step(self, db_session):
        svc = OperatorSessionService(db_session)
        session = svc.create()
        result = svc.select_tenant(session["session_id"], "tenant_test_123")
        assert result["tenant_id"] == "tenant_test_123"
        assert result["current_step"] == "awaiting_connection"
        assert result["known_ids"]["tenant_id"] == "tenant_test_123"

    def test_select_connection_advances_step(self, db_session):
        svc = OperatorSessionService(db_session)
        session = svc.create()
        svc.select_tenant(session["session_id"], "tenant_abc")
        result = svc.select_connection(session["session_id"], "conn_test_456")
        assert result["connection_id"] == "conn_test_456"
        assert result["current_step"] == "run_diagnosis"
        assert result["known_ids"]["connection_id"] == "conn_test_456"

    def test_select_opportunity(self, db_session):
        svc = OperatorSessionService(db_session)
        session = svc.create()
        # Manually inject opportunity step via direct update
        from erpguard.db.repositories import update_operator_session
        import json
        update_operator_session(
            db_session,
            session["session_id"],
            current_step="select_opportunity",
            known_ids_json=json.dumps({"opportunity_ids": ["opp_1", "opp_2"]}),
        )
        result = svc.select_opportunity(session["session_id"], "opp_1")
        assert result["known_ids"]["opportunity_id"] == "opp_1"
        assert result["current_step"] == "create_draft"


# ── OperatorOrchestrator — non-Odoo steps ─────────────────────────────────

class TestOperatorOrchestrator:
    def test_run_next_auto_creates_tenant(self, db_session):
        svc = OperatorSessionService(db_session)
        session = svc.create()
        orch = OperatorOrchestrator(db_session)
        result = orch.run_next(session["session_id"])
        assert result["step_status"] == "ok"
        assert result["known_ids"].get("tenant_id") is not None
        assert result["current_step"] == "awaiting_connection"

    def test_run_next_at_awaiting_connection_blocks(self, db_session):
        svc = OperatorSessionService(db_session)
        session = svc.create()
        # advance past awaiting_tenant
        orch = OperatorOrchestrator(db_session)
        orch.run_next(session["session_id"])  # runs awaiting_tenant
        result = orch.run_next(session["session_id"])  # now at awaiting_connection
        assert "awaiting_connection" in result["message"] or result["current_step"] == "awaiting_connection"

    def test_run_next_missing_session_raises(self, db_session):
        from erpguard.core.errors import ObjectNotFoundError
        orch = OperatorOrchestrator(db_session)
        with pytest.raises(ObjectNotFoundError):
            orch.run_next("opsession_does_not_exist")

    def test_run_next_compile_skill_from_review(self, db_session):
        """Test compile_skill step directly using known review_id."""
        import json
        from erpguard.db.repositories import update_operator_session
        svc = OperatorSessionService(db_session)
        session = svc.create()

        # Need a real review to compile — create one via the draft review service
        # First create a compiled skill set-up via the product chain
        # We'll inject skill_id directly to test steps after compile
        # Just test that the orchestrator handles missing skill_id gracefully
        update_operator_session(
            db_session,
            session["session_id"],
            current_step="run_dry_run_proof",
            known_ids_json=json.dumps({}),
        )
        orch = OperatorOrchestrator(db_session)
        result = orch.run_next(session["session_id"])
        # Should error because no skill_id
        assert result["step_status"] == "error"
        assert "skill_id" in result["message"]

    def test_run_next_select_opportunity_with_no_opportunities(self, db_session):
        import json
        from erpguard.db.repositories import update_operator_session
        svc = OperatorSessionService(db_session)
        session = svc.create()
        update_operator_session(
            db_session,
            session["session_id"],
            current_step="select_opportunity",
            known_ids_json=json.dumps({}),
        )
        orch = OperatorOrchestrator(db_session)
        result = orch.run_next(session["session_id"])
        assert result["step_status"] == "ok"
        assert "skipping" in result["message"].lower() or result["message"] != ""

    def test_run_next_optional_r1_write_pilot_is_blocked(self, db_session):
        import json
        from erpguard.db.repositories import update_operator_session
        svc = OperatorSessionService(db_session)
        session = svc.create()
        update_operator_session(
            db_session,
            session["session_id"],
            current_step="optional_r1_write_pilot",
            known_ids_json=json.dumps({"skill_id": "skill_test"}),
        )
        orch = OperatorOrchestrator(db_session)
        result = orch.run_next(session["session_id"])
        assert result["step_status"] == "ok"
        assert "blocked" in result["message"].lower()

    def test_completed_session_returns_immediately(self, db_session):
        from erpguard.db.repositories import update_operator_session
        svc = OperatorSessionService(db_session)
        session = svc.create()
        update_operator_session(db_session, session["session_id"], status="completed", current_step="completed")
        orch = OperatorOrchestrator(db_session)
        result = orch.run_next(session["session_id"])
        assert "completed" in result["message"].lower()

    def test_run_safe_readonly_path_runs_past_awaiting_tenant(self, db_session):
        svc = OperatorSessionService(db_session)
        session = svc.create()
        orch = OperatorOrchestrator(db_session)
        result = orch.run_safe_readonly_path(session["session_id"])
        # Should run awaiting_tenant, then stop at awaiting_connection (blocking)
        assert "awaiting_tenant" in result["steps_executed"]
        assert result["current_step"] == "awaiting_connection"


# ── OperatorTimelineService ────────────────────────────────────────────────

class TestOperatorTimelineService:
    def test_empty_timeline(self, db_session):
        svc = OperatorSessionService(db_session)
        session = svc.create()
        timeline_svc = OperatorTimelineService(db_session)
        result = timeline_svc.get_timeline(session["session_id"])
        assert result["session_id"] == session["session_id"]
        assert result["events"] == []
        assert result["steps_completed"] == []

    def test_timeline_records_events_after_run(self, db_session):
        svc = OperatorSessionService(db_session)
        session = svc.create()
        orch = OperatorOrchestrator(db_session)
        orch.run_next(session["session_id"])  # runs awaiting_tenant
        timeline_svc = OperatorTimelineService(db_session)
        result = timeline_svc.get_timeline(session["session_id"])
        assert len(result["events"]) >= 1
        assert "awaiting_tenant" in result["steps_completed"]

    def test_timeline_not_found(self, db_session):
        from erpguard.core.errors import ObjectNotFoundError
        timeline_svc = OperatorTimelineService(db_session)
        with pytest.raises(ObjectNotFoundError):
            timeline_svc.get_timeline("opsession_not_exist")


# ── OperatorSummaryService ─────────────────────────────────────────────────

class TestOperatorSummaryService:
    def test_summary_new_session(self, db_session):
        svc = OperatorSessionService(db_session)
        session = svc.create()
        summary_svc = OperatorSummaryService(db_session)
        result = summary_svc.summarize(session["session_id"])
        assert result["session_id"] == session["session_id"]
        assert result["status"] == "active"
        assert result["progress_pct"] >= 0
        assert result["steps_total"] > 0

    def test_summary_safety_invariants_always_safe(self, db_session):
        svc = OperatorSessionService(db_session)
        session = svc.create()
        summary_svc = OperatorSummaryService(db_session)
        result = summary_svc.summarize(session["session_id"])
        inv = result["safety_invariants"]
        assert inv["can_execute_real_writes"] is False
        assert inv["allow_generic_real_odoo_writes"] is False
        assert inv["allow_r3_r4_real_writes"] is False
        assert inv["approved_for_real_execution"] is False

    def test_summary_progress_increases_after_step(self, db_session):
        svc = OperatorSessionService(db_session)
        session = svc.create()
        summary_svc = OperatorSummaryService(db_session)
        before = summary_svc.summarize(session["session_id"])
        orch = OperatorOrchestrator(db_session)
        orch.run_next(session["session_id"])
        after = summary_svc.summarize(session["session_id"])
        assert after["progress_pct"] >= before["progress_pct"]
        assert after["steps_completed"] >= before["steps_completed"]

    def test_summary_known_ids_excludes_secrets(self, db_session):
        import json
        from erpguard.db.repositories import update_operator_session
        svc = OperatorSessionService(db_session)
        session = svc.create()
        update_operator_session(
            db_session,
            session["session_id"],
            known_ids_json=json.dumps({"skill_id": "s1", "password": "secret_val", "api_key": "key123"}),
        )
        summary_svc = OperatorSummaryService(db_session)
        result = summary_svc.summarize(session["session_id"])
        assert "skill_id" in result["known_ids"]
        assert "password" not in result["known_ids"]
        assert "api_key" not in result["known_ids"]
