import json

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.schemas.audit import AuditTrailResponse
from erpguard.db.models import AuditEvent, InvariantResult, PreflightCase
from erpguard.db.repositories import get_preflight_case, list_audit_events, list_invariant_results
from erpguard.db.session import SessionLocal, init_db

router = APIRouter(prefix="/v1", tags=["audit"])


@router.get("/audit/{case_id}", response_model=AuditTrailResponse)
def get_audit_case(case_id: str):
    init_db()
    session = SessionLocal()
    try:
        case = get_preflight_case(session, case_id)
        if case is None:
            return JSONResponse(
                status_code=404,
                content={"error": {"code": "audit_case_not_found", "message": f"Audit case '{case_id}' not found."}},
            )
        invariants = list_invariant_results(session, case_id)
        events = list_audit_events(session, case_id)
        return {
            "case_id": case.id,
            "preflight_case": _case_summary(case),
            "invariant_results": [_invariant_to_dict(row) for row in invariants],
            "audit_events": [_audit_event_to_dict(row) for row in events],
            "execution": None,
        }
    finally:
        session.close()


def _case_summary(case: PreflightCase) -> dict:
    return {
        "preflight_id": case.id,
        "canonical_action": case.canonical_action,
        "canonical_object": case.canonical_object,
        "decision": case.decision,
        "risk_level": case.risk_level,
        "summary": case.summary,
        "created_at": case.created_at.isoformat(),
    }


def _invariant_to_dict(row: InvariantResult) -> dict:
    return {
        "id": row.id,
        "preflight_case_id": row.preflight_case_id,
        "invariant_id": row.invariant_id,
        "invariant_type": row.invariant_type,
        "status": row.status,
        "severity": row.severity,
        "message": row.message,
        "evidence": _json_loads(row.evidence_json),
        "created_at": row.created_at.isoformat(),
    }


def _audit_event_to_dict(row: AuditEvent) -> dict:
    return {
        "id": row.id,
        "case_id": row.case_id,
        "event_type": row.event_type,
        "event": _json_loads(row.event_json),
        "created_at": row.created_at.isoformat(),
    }


def _json_loads(value: str | None):
    if not value:
        return None
    return json.loads(value)
