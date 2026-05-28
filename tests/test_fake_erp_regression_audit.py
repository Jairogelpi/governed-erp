from __future__ import annotations

from erpguard.db.session import SessionLocal, init_db
from erpguard.product.fake_erp_regression_audit import (
    get_fake_erp_regression_audit,
    persist_fake_erp_regression_audit_event,
)


def test_regression_audit_contains_requested_execution_and_completed_events():
    init_db()
    db = SessionLocal()
    try:
        actor = {"type": "user", "id": "operator_1"}
        for event_type, status in (
            ("requested", "info"),
            ("execution_completed", "completed"),
            ("comparison_completed", "completed"),
            ("regression_completed", "completed"),
        ):
            persist_fake_erp_regression_audit_event(
                regression_run_id="fregrun_1",
                case_id="fregcase_1",
                version_id="ver_1",
                execution_id="fexec_1",
                evidence_pack_id="fepack_1",
                actor=actor,
                event_type=event_type,
                status=status,
                detail={},
                session=db,
            )
        result = get_fake_erp_regression_audit(session=db, limit=20)
        event_types = [entry.event_type for entry in result.entries if entry.regression_run_id == "fregrun_1"]
        assert "requested" in event_types
        assert "execution_completed" in event_types
        assert "comparison_completed" in event_types
        assert "regression_completed" in event_types
    finally:
        db.close()
