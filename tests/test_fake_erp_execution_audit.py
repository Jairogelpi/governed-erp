from __future__ import annotations

from erpguard.db.session import SessionLocal, init_db
from erpguard.product.fake_erp_execution_audit import (
    get_fake_erp_execution_audit,
    persist_fake_erp_execution_audit_event,
)


def test_audit_contains_requested_gate_execution_step_and_completed_events():
    init_db()
    db = SessionLocal()
    try:
        actor = {"type": "user", "id": "operator_1"}
        execution_id = "fexec_audit_1"
        version_id = "ver_1"
        dry_run_id = "dryrun_1"
        for event_type, status in (
            ("requested", "info"),
            ("gate_passed", "ok"),
            ("execution_started", "running"),
            ("step_completed", "completed"),
            ("execution_completed", "completed"),
        ):
            persist_fake_erp_execution_audit_event(
                execution_id=execution_id,
                version_id=version_id,
                dry_run_id=dry_run_id,
                actor=actor,
                event_type=event_type,
                status=status,
                detail={},
                session=db,
            )
        result = get_fake_erp_execution_audit(session=db, limit=20)
        event_types = [e.event_type for e in result.entries if e.execution_id == execution_id]
        assert "requested" in event_types
        assert "gate_passed" in event_types
        assert "execution_started" in event_types
        assert "step_completed" in event_types
        assert "execution_completed" in event_types
    finally:
        db.close()


def test_blocked_gate_creates_audit_event():
    init_db()
    db = SessionLocal()
    try:
        persist_fake_erp_execution_audit_event(
            execution_id="fexec_audit_2",
            version_id="ver_2",
            dry_run_id="dryrun_2",
            actor={"type": "user", "id": "operator_1"},
            event_type="gate_blocked",
            status="blocked",
            detail={"blocking_reasons": ["token_not_confirmed:pending"]},
            session=db,
        )
        result = get_fake_erp_execution_audit(session=db, limit=20)
        blocked = [e for e in result.entries if e.execution_id == "fexec_audit_2" and e.event_type == "gate_blocked"]
        assert blocked
    finally:
        db.close()

