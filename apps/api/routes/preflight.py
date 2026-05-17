from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.schemas.preflight import PreflightRequest, PreflightResponse
from erpguard.adapters.factory import get_adapter
from erpguard.canonical.enums import CanonicalAction, ERPType
from erpguard.core.errors import AdapterConfigurationError, AdapterNotImplementedError
from erpguard.core.preflight import PREFLIGHT_CREATED, PREFLIGHT_DECIDED, run_preflight
from erpguard.db.repositories import (
    create_audit_event,
    create_invariant_results_from_policy_issues,
    create_preflight_case,
)
from erpguard.db.session import SessionLocal, init_db

router = APIRouter(prefix="/v1", tags=["preflight"])


@router.post("/preflight", response_model=PreflightResponse)
def preflight(request: PreflightRequest):
    erp_type = _parse_erp_type(request.erp_type)
    if isinstance(erp_type, JSONResponse):
        return erp_type

    try:
        adapter = get_adapter(erp_type)
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
    _persist_preflight_result(result)
    return _to_response(result)


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


def _persist_preflight_result(result) -> None:
    init_db()
    session = SessionLocal()
    try:
        case = create_preflight_case(session, result)
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
