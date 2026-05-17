import json

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.schemas.audit import PreflightCaseDetailResponse
from apps.api.schemas.preflight import PreflightRequest, PreflightResponse
from erpguard.adapters.factory import create_adapter_from_connection, get_adapter
from erpguard.canonical.enums import CanonicalAction, ERPType
from erpguard.core.errors import AdapterConfigurationError, AdapterNotImplementedError
from erpguard.core.preflight import PREFLIGHT_CREATED, PREFLIGHT_DECIDED, run_preflight
from erpguard.db.repositories import (
    create_audit_event,
    create_invariant_results_from_policy_issues,
    create_preflight_case,
    get_connection,
    get_preflight_case,
    list_invariant_results,
)
from erpguard.db.session import SessionLocal, init_db

router = APIRouter(prefix="/v1", tags=["preflight"])


@router.post("/preflight", response_model=PreflightResponse)
def preflight(request: PreflightRequest):
    adapter_result = _resolve_adapter(request)
    if isinstance(adapter_result, JSONResponse):
        return adapter_result
    adapter, connection_id = adapter_result

    canonical_action = _parse_canonical_action(request.action.canonical_action)
    if isinstance(canonical_action, JSONResponse):
        return canonical_action

    result = run_preflight(
        adapter=adapter,
        actor=request.actor,
        canonical_action=canonical_action,
        target_id=request.action.target_id,
        policy_id=request.policy_id,
    )
    _persist_preflight_result(result, connection_id=connection_id)
    return _to_response(result)


@router.get("/preflight/{preflight_id}", response_model=PreflightCaseDetailResponse)
def get_preflight(preflight_id: str):
    init_db()
    session = SessionLocal()
    try:
        case = get_preflight_case(session, preflight_id)
        if case is None:
            return JSONResponse(
                status_code=404,
                content={
                    "error": {
                        "code": "preflight_not_found",
                        "message": f"Preflight case '{preflight_id}' not found.",
                    }
                },
            )
        invariants = list_invariant_results(session, preflight_id)
        return {
            "preflight_id": case.id,
            "actor": _json_loads(case.actor_json) or {},
            "action": _json_loads(case.action_json) or {},
            "canonical_action": case.canonical_action,
            "canonical_object": case.canonical_object,
            "decision": case.decision,
            "risk_level": case.risk_level,
            "summary": case.summary,
            "simulation": _json_loads(case.simulation_json),
            "invariant_results": [_invariant_to_dict(row) for row in invariants],
            "created_at": case.created_at.isoformat(),
        }
    finally:
        session.close()


def _resolve_adapter(request: PreflightRequest):
    if request.connection_id:
        init_db()
        session = SessionLocal()
        try:
            connection = get_connection(session, request.connection_id)
            if connection is None:
                return JSONResponse(
                    status_code=404,
                    content={
                        "error": {
                            "code": "connection_not_found",
                            "message": f"Connection '{request.connection_id}' not found.",
                            "details": {"connection_id": request.connection_id},
                        }
                    },
                )
            try:
                return create_adapter_from_connection(connection), connection.id
            except AdapterConfigurationError as exc:
                return JSONResponse(
                    status_code=400,
                    content={"error": {"code": "adapter_configuration_error", "message": str(exc), "details": {}}},
                )
            except AdapterNotImplementedError as exc:
                return JSONResponse(
                    status_code=501,
                    content={"error": {"code": "adapter_not_implemented", "message": str(exc), "details": {}}},
                )
        finally:
            session.close()

    if not request.erp_type:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "connection_or_erp_type_required",
                    "message": "Either connection_id or erp_type is required.",
                    "details": {},
                }
            },
        )

    erp_type = _parse_erp_type(request.erp_type)
    if isinstance(erp_type, JSONResponse):
        return erp_type

    try:
        return get_adapter(erp_type), erp_type.value
    except AdapterConfigurationError as exc:
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "adapter_configuration_error", "message": str(exc), "details": {}}},
        )
    except AdapterNotImplementedError as exc:
        return JSONResponse(
            status_code=501,
            content={"error": {"code": "adapter_not_implemented", "message": str(exc), "details": {}}},
        )


def _parse_erp_type(value: str) -> ERPType | JSONResponse:
    try:
        return ERPType(value)
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "unsupported_erp_type",
                    "message": f"Unsupported ERP type '{value}'.",
                    "details": {"erp_type": value},
                }
            },
        )


def _parse_canonical_action(value: str) -> CanonicalAction | JSONResponse:
    try:
        return CanonicalAction(value)
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "unsupported_canonical_action",
                    "message": f"Unsupported canonical action '{value}'.",
                    "details": {"canonical_action": value},
                }
            },
        )


def _persist_preflight_result(result, connection_id: str) -> None:
    init_db()
    session = SessionLocal()
    try:
        case = create_preflight_case(session, result, connection_id=connection_id)
        create_invariant_results_from_policy_issues(session, case.id, result.issues)
        create_audit_event(session, case.id, PREFLIGHT_CREATED, {"case_id": case.id})
        create_audit_event(session, case.id, PREFLIGHT_DECIDED, result.model_dump(mode="json"))
    finally:
        session.close()


def _to_response(result) -> dict:
    return {
        "preflight_id": result.id,
        "decision": result.decision.value,
        "risk_level": result.risk_level.value,
        "summary": result.summary,
        "issues": [issue.model_dump(mode="json") for issue in result.issues],
        "warnings": [warning.model_dump(mode="json") for warning in result.warnings],
        "actor": result.actor,
        "canonical_action": result.canonical_action.value,
        "target_id": result.target_id,
        "policy_id": result.policy_id,
        "policy_version": result.policy_version,
    }


def _invariant_to_dict(row) -> dict:
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


def _json_loads(value: str | None):
    if not value:
        return None
    return json.loads(value)
