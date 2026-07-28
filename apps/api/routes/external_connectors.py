from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.schemas.external_connectors import (
    ConnectorListResponse,
    ConnectorPolicyResponse,
    ConnectorReadEvidenceListResponse,
    ConnectorReadEvidenceResponse,
    ConnectorSignalListResponse,
    ExternalConnectorAuditResponse,
    ReadCalendarsRequest,
    ReadCalendarsResponse,
    ReadUpcomingEventsRequest,
    ReadUpcomingEventsResponse,
    TestReadinessRequest,
    TestReadinessResponse,
)
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.connector_read_evidence import ConnectorReadEvidenceService
from erpguard.product.connector_signal_generator import ConnectorSignalGenerator
from erpguard.product.external_connector_audit import ExternalConnectorAuditService
from erpguard.product.external_connector_policy import ExternalConnectorPolicy
from erpguard.product.external_connector_redaction import (
    redact_calendar_events,
    redact_calendar_item,
)
from erpguard.product.google_calendar_readonly_client import GoogleCalendarReadOnlyClient

router = APIRouter(prefix="/v1/external-connectors", tags=["external-connectors"])

_CONNECTOR_ID = "google_calendar_readonly"
_policy = ExternalConnectorPolicy()
_signal_gen = ConnectorSignalGenerator()


@router.get("", response_model=ConnectorListResponse)
def list_external_connectors():
    return {
        "connectors": _policy.list_connectors(),
        "policy_version": "sprint18-v1",
    }


@router.get("/google-calendar-readonly/policy", response_model=ConnectorPolicyResponse)
def get_connector_policy():
    return _policy.get_connector_policy(_CONNECTOR_ID)


@router.post("/google-calendar-readonly/test-readiness", response_model=TestReadinessResponse)
def test_readiness(request: TestReadinessRequest):
    check = _policy.check(_CONNECTOR_ID, "test_readiness")
    init_db()
    session = SessionLocal()
    try:
        audit = ExternalConnectorAuditService(session)
        audit.record(
            auth_profile_id=request.auth_profile_id,
            connector_id=_CONNECTOR_ID,
            event_type="test_readiness",
            operation="test_readiness",
            status="allowed" if check.allowed else "blocked",
            fixture_mode=True,
            actor=request.actor,
            details={"policy_passed": check.allowed, "violations": check.violations},
        )
    finally:
        session.close()

    return {
        "connector_id": _CONNECTOR_ID,
        "auth_profile_id": request.auth_profile_id,
        "policy_allowed": check.allowed,
        "fixture_mode": True,
        "violations": check.violations,
        "allowed_scopes": check.allowed_scopes,
        "policy_version": check.policy_version,
    }


@router.post("/google-calendar-readonly/read-calendars", response_model=ReadCalendarsResponse)
def read_calendars(request: ReadCalendarsRequest):
    check = _policy.check(_CONNECTOR_ID, "read_calendars")
    if not check.allowed:
        return JSONResponse(
            status_code=403,
            content={"error": {"code": "policy_violation", "violations": check.violations}},
        )

    client = GoogleCalendarReadOnlyClient()
    read_result = client.read_calendars()

    safe_calendars = [redact_calendar_item(c) for c in read_result.items]

    signals = _signal_gen.generate_from_calendars(
        safe_calendars, fixture_mode=read_result.fixture_mode
    )

    result_summary = {
        "total_count": read_result.total_count,
        "fixture_mode": read_result.fixture_mode,
        "read_only": True,
    }

    init_db()
    session = SessionLocal()
    try:
        evidence_svc = ConnectorReadEvidenceService(session)
        evidence = evidence_svc.store(
            auth_profile_id=request.auth_profile_id,
            connector_id=_CONNECTOR_ID,
            operation="read_calendars",
            fixture_mode=read_result.fixture_mode,
            record_count=read_result.total_count,
            redacted_fields_count=0,
            result_summary=result_summary,
        )
        audit = ExternalConnectorAuditService(session)
        audit.record(
            auth_profile_id=request.auth_profile_id,
            connector_id=_CONNECTOR_ID,
            event_type="read_calendars",
            operation="read_calendars",
            status="success",
            fixture_mode=read_result.fixture_mode,
            actor=request.actor,
            details=result_summary,
        )
    finally:
        session.close()

    return {
        "connector_id": _CONNECTOR_ID,
        "auth_profile_id": request.auth_profile_id,
        "fixture_mode": read_result.fixture_mode,
        "calendars": safe_calendars,
        "total_count": read_result.total_count,
        "redacted_fields_count": 0,
        "read_only": True,
        "evidence_id": evidence.id,
        "signals": [s.model_dump() for s in signals],
    }


@router.post("/google-calendar-readonly/read-upcoming-events", response_model=ReadUpcomingEventsResponse)
def read_upcoming_events(request: ReadUpcomingEventsRequest):
    check = _policy.check(_CONNECTOR_ID, "read_upcoming_events")
    if not check.allowed:
        return JSONResponse(
            status_code=403,
            content={"error": {"code": "policy_violation", "violations": check.violations}},
        )

    client = GoogleCalendarReadOnlyClient()
    read_result = client.read_upcoming_events(max_results=request.max_results)

    safe_events, redacted_count = redact_calendar_events(read_result.items)

    signals = _signal_gen.generate_from_events(
        safe_events, fixture_mode=read_result.fixture_mode
    )

    result_summary = {
        "total_count": read_result.total_count,
        "redacted_fields_count": redacted_count,
        "fixture_mode": read_result.fixture_mode,
        "read_only": True,
    }

    init_db()
    session = SessionLocal()
    try:
        evidence_svc = ConnectorReadEvidenceService(session)
        evidence = evidence_svc.store(
            auth_profile_id=request.auth_profile_id,
            connector_id=_CONNECTOR_ID,
            operation="read_upcoming_events",
            fixture_mode=read_result.fixture_mode,
            record_count=read_result.total_count,
            redacted_fields_count=redacted_count,
            result_summary=result_summary,
        )
        audit = ExternalConnectorAuditService(session)
        audit.record(
            auth_profile_id=request.auth_profile_id,
            connector_id=_CONNECTOR_ID,
            event_type="read_upcoming_events",
            operation="read_upcoming_events",
            status="success",
            fixture_mode=read_result.fixture_mode,
            actor=request.actor,
            details=result_summary,
        )
    finally:
        session.close()

    return {
        "connector_id": _CONNECTOR_ID,
        "auth_profile_id": request.auth_profile_id,
        "fixture_mode": read_result.fixture_mode,
        "events": safe_events,
        "total_count": read_result.total_count,
        "redacted_fields_count": redacted_count,
        "read_only": True,
        "evidence_id": evidence.id,
        "signals": [s.model_dump() for s in signals],
    }


@router.get("/read-evidence/{evidence_id}", response_model=ConnectorReadEvidenceResponse)
def get_read_evidence(evidence_id: str):
    init_db()
    session = SessionLocal()
    try:
        svc = ConnectorReadEvidenceService(session)
        evidence = svc.get(evidence_id)
        if evidence is None:
            return JSONResponse(
                status_code=404,
                content={"error": {"code": "evidence_not_found", "message": f"Evidence {evidence_id} not found"}},
            )
        return evidence.model_dump()
    finally:
        session.close()


@router.get("/auth-profiles/{auth_profile_id}/read-evidence", response_model=ConnectorReadEvidenceListResponse)
def list_read_evidence(auth_profile_id: str):
    init_db()
    session = SessionLocal()
    try:
        svc = ConnectorReadEvidenceService(session)
        items = svc.list_for_profile(auth_profile_id)
        return {
            "auth_profile_id": auth_profile_id,
            "evidence": [e.model_dump() for e in items],
        }
    finally:
        session.close()


@router.get("/auth-profiles/{auth_profile_id}/signals", response_model=ConnectorSignalListResponse)
def get_signals_for_profile(auth_profile_id: str):
    init_db()
    session = SessionLocal()
    try:
        svc = ConnectorReadEvidenceService(session)
        evidence_list = svc.list_for_profile(auth_profile_id)

        all_signals: list[dict] = []
        for ev in evidence_list[:1]:
            if ev.operation == "read_upcoming_events":
                sigs = _signal_gen.generate_from_events([], fixture_mode=ev.fixture_mode)
                for s in sigs:
                    s_dict = s.model_dump()
                    if s.signal_code == "upcoming_events_count":
                        s_dict["value"] = str(ev.record_count)
                    all_signals.append(s_dict)
            elif ev.operation == "read_calendars":
                sigs = _signal_gen.generate_from_calendars([], fixture_mode=ev.fixture_mode)
                for s in sigs:
                    s_dict = s.model_dump()
                    if s.signal_code == "calendars_accessible":
                        s_dict["value"] = str(ev.record_count)
                    all_signals.append(s_dict)

        return {
            "auth_profile_id": auth_profile_id,
            "connector_id": _CONNECTOR_ID,
            "signals": all_signals,
        }
    finally:
        session.close()


@router.get("/auth-profiles/{auth_profile_id}/audit", response_model=ExternalConnectorAuditResponse)
def get_audit_for_profile(auth_profile_id: str):
    init_db()
    session = SessionLocal()
    try:
        svc = ExternalConnectorAuditService(session)
        events = svc.list_for_profile(auth_profile_id)
        return {
            "auth_profile_id": auth_profile_id,
            "events": [e.model_dump() for e in events],
        }
    finally:
        session.close()
