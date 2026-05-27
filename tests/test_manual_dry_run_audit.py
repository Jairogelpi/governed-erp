from __future__ import annotations

from erpguard.db.session import SessionLocal, init_db
from erpguard.product.manual_dry_run_audit import (
    get_manual_dry_run_audit,
    persist_manual_dry_run_audit_event,
)


def test_audit_contains_requested_gate_completed_events():
    init_db()
    db = SessionLocal()
    try:
        run_id = "dryrun_audit_1"
        version_id = "ver_audit_1"
        actor = {"type": "user", "id": "operator_1"}
        persist_manual_dry_run_audit_event(run_id=run_id, version_id=version_id, actor=actor, event_type="requested", status="info", detail={}, session=db)
        persist_manual_dry_run_audit_event(run_id=run_id, version_id=version_id, actor=actor, event_type="gate_passed", status="ok", detail={}, session=db)
        persist_manual_dry_run_audit_event(run_id=run_id, version_id=version_id, actor=actor, event_type="completed", status="completed", detail={}, session=db)

        result = get_manual_dry_run_audit(session=db, limit=20)
        event_types = [e.event_type for e in result.entries if e.run_id == run_id]
        assert "requested" in event_types
        assert "gate_passed" in event_types
        assert "completed" in event_types
    finally:
        db.close()


def test_blocked_gate_creates_audit_event():
    init_db()
    db = SessionLocal()
    try:
        run_id = "dryrun_audit_2"
        version_id = "ver_audit_2"
        actor = {"type": "user", "id": "operator_1"}
        persist_manual_dry_run_audit_event(
            run_id=run_id,
            version_id=version_id,
            actor=actor,
            event_type="gate_blocked",
            status="blocked",
            detail={"blocking_reasons": ["token_not_confirmed:pending"]},
            session=db,
        )
        result = get_manual_dry_run_audit(session=db, limit=20)
        blocked = [e for e in result.entries if e.run_id == run_id and e.event_type == "gate_blocked"]
        assert blocked
        assert blocked[0].status == "blocked"
    finally:
        db.close()
