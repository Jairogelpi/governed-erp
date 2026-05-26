from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from apps.api.schemas.operator_action_dispatch_execute import (
    DispatchableActionsResponse,
    DispatchExecuteRequest,
    DispatchExecutionAuditEntrySchema,
    DispatchExecutionAuditResponse,
    DispatchResultResponse,
)
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.operator_action_dispatch_execution_audit import get_dispatch_execution_audit
from erpguard.product.operator_action_dispatch_handlers import list_dispatchable_actions
from erpguard.product.operator_action_dispatch_result import get_dispatch_result
from erpguard.product.operator_action_dispatcher import (
    DispatchRequest,
    dispatch_confirmed_read_only_action,
)

router = APIRouter(
    prefix="/v1/operator-console",
    tags=["operator-action-dispatch-execute"],
)


def _to_response(result) -> DispatchResultResponse:
    return DispatchResultResponse(
        dispatch_id=result.dispatch_id,
        action_key=result.action_key,
        status=result.status,
        dispatch_performed=result.dispatch_performed,
        handler_type=result.handler_type,
        token_confirmed=result.token_confirmed,
        eligibility_passed=result.eligibility_passed,
        result_payload=result.result_payload,
        result_summary=result.result_summary,
        blocking_reasons=result.blocking_reasons,
        erp_writes_performed=result.erp_writes_performed,
        browser_control_performed=result.browser_control_performed,
        mcp_execution_performed=result.mcp_execution_performed,
        llm_runtime_used=result.llm_runtime_used,
        system_state_mutated=result.system_state_mutated,
        skill_mutated=result.skill_mutated,
        activation_performed=result.activation_performed,
        scheduling_performed=result.scheduling_performed,
        audit_recorded=result.audit_recorded,
    )


@router.get("/action-plan/dispatchable-actions", response_model=DispatchableActionsResponse)
def get_dispatchable_actions():
    actions = list_dispatchable_actions()
    return DispatchableActionsResponse(actions=actions, total=len(actions))


@router.post("/action-plan/dispatch", response_model=DispatchResultResponse)
def dispatch_read_only_action(body: DispatchExecuteRequest):
    init_db()
    db = SessionLocal()
    try:
        result = dispatch_confirmed_read_only_action(
            DispatchRequest(
                plan_id=body.plan_id,
                step_number=body.step_number,
                action_key=body.action_key,
                endpoint_hint=body.endpoint_hint,
                method_hint=body.method_hint,
                token_id=body.token_id,
                version_id=body.version_id,
                parameters=body.parameters,
            ),
            session=db,
        )
        return _to_response(result)
    finally:
        db.close()


@router.get("/action-plan/dispatch-results/{dispatch_id}", response_model=DispatchResultResponse)
def get_dispatch_result_endpoint(dispatch_id: str):
    init_db()
    db = SessionLocal()
    try:
        result = get_dispatch_result(dispatch_id, db)
        if result is None:
            raise HTTPException(status_code=404, detail="dispatch_result_not_found")
        return _to_response(result)
    finally:
        db.close()


@router.get("/action-plan/dispatch-execution-audit", response_model=DispatchExecutionAuditResponse)
def get_dispatch_execution_audit_endpoint(limit: int = Query(default=50, ge=1, le=200)):
    init_db()
    db = SessionLocal()
    try:
        result = get_dispatch_execution_audit(db, limit=limit)
        return DispatchExecutionAuditResponse(
            entries=[
                DispatchExecutionAuditEntrySchema(
                    event_id=entry.event_id,
                    dispatch_id=entry.dispatch_id,
                    action_key=entry.action_key,
                    event_type=entry.event_type,
                    status=entry.status,
                    handler_type=entry.handler_type,
                    endpoint_hint=entry.endpoint_hint,
                    method_hint=entry.method_hint,
                    token_id=entry.token_id,
                    version_id=entry.version_id,
                    detail=entry.detail,
                    created_at=entry.created_at,
                )
                for entry in result.entries
            ],
            event_count=result.event_count,
        )
    finally:
        db.close()
