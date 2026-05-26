from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from erpguard.product.operator_action_dispatch_eligibility import check_eligibility
from erpguard.product.operator_action_dispatch_execution_audit import persist_dispatch_execution_event
from erpguard.product.operator_action_dispatch_handlers import (
    list_dispatchable_actions,
    run_internal_read_only_handler,
)
from erpguard.product.operator_action_dispatch_result import (
    OperatorActionDispatchResult,
    persist_dispatch_result,
)
from erpguard.product.operator_action_registry import get_action_entry
from erpguard.product.operator_step_confirmation import get_token_status


@dataclass(frozen=True)
class DispatchRequest:
    plan_id: str
    step_number: int
    action_key: str
    endpoint_hint: str
    method_hint: str
    token_id: str
    version_id: str | None
    parameters: dict[str, Any]


def _persist_blocked(
    *,
    request: DispatchRequest,
    reason: str,
    session,
    eligibility_passed: bool = False,
    token_confirmed: bool = False,
) -> OperatorActionDispatchResult:
    dispatch_id = f"disp_{uuid.uuid4().hex[:16]}"
    persist_dispatch_execution_event(
        dispatch_id=dispatch_id,
        action_key=request.action_key,
        event_type="blocked",
        status="blocked",
        handler_type="internal_read_only",
        endpoint_hint=request.endpoint_hint,
        method_hint=request.method_hint,
        token_id=request.token_id,
        version_id=request.version_id,
        detail={
            "plan_id": request.plan_id,
            "step_number": request.step_number,
            "blocking_reason": reason,
            "dispatch_performed": False,
            "endpoint_hint_executed": False,
        },
        session=session,
    )
    return persist_dispatch_result(
        dispatch_id=dispatch_id,
        action_key=request.action_key,
        status="blocked",
        dispatch_performed=False,
        handler_type="internal_read_only",
        token_confirmed=token_confirmed,
        eligibility_passed=eligibility_passed,
        result_payload={},
        result_summary=reason,
        blocking_reasons=[reason],
        endpoint_hint=request.endpoint_hint,
        method_hint=request.method_hint,
        token_id=request.token_id,
        version_id=request.version_id,
        parameters=request.parameters,
        audit_recorded=True,
        session=session,
    )


def dispatch_confirmed_read_only_action(
    request: DispatchRequest,
    *,
    session,
) -> OperatorActionDispatchResult:
    action = get_action_entry(request.action_key)
    if action is None:
        return _persist_blocked(
            request=request,
            reason=(
                f"Action key '{request.action_key}' is not registered. "
                "Sprint 45 dispatch accepts only explicitly registered allowlist actions."
            ),
            session=session,
        )

    if request.action_key not in list_dispatchable_actions():
        return _persist_blocked(
            request=request,
            reason=(
                f"Action '{request.action_key}' is not allowed in Sprint 45. "
                "Only internal read-only advisory handlers may be dispatched."
            ),
            session=session,
        )

    token = get_token_status(request.token_id, session)
    if token is None:
        return _persist_blocked(
            request=request,
            reason="Confirmed token required for dispatch. Token was not found.",
            session=session,
        )
    if token.status != "confirmed":
        return _persist_blocked(
            request=request,
            reason=(
                f"Confirmed token required for dispatch. Token status is '{token.status}'."
            ),
            session=session,
        )

    eligibility = check_eligibility(
        action_key=request.action_key,
        endpoint_hint=request.endpoint_hint,
        method_hint=request.method_hint,
        token_id=request.token_id,
        version_id=request.version_id,
        session=session,
    )
    if not eligibility.eligible:
        return _persist_blocked(
            request=request,
            reason=eligibility.blocked_reason or "Dispatch eligibility failed.",
            session=session,
            eligibility_passed=False,
            token_confirmed=True,
        )

    dispatch_id = f"disp_{uuid.uuid4().hex[:16]}"
    persist_dispatch_execution_event(
        dispatch_id=dispatch_id,
        action_key=request.action_key,
        event_type="requested",
        status="accepted",
        handler_type="internal_read_only",
        endpoint_hint=request.endpoint_hint,
        method_hint=request.method_hint,
        token_id=request.token_id,
        version_id=request.version_id,
        detail={
            "plan_id": request.plan_id,
            "step_number": request.step_number,
            "endpoint_hint_executed": False,
            "handler_selected_by": "action_key",
        },
        session=session,
    )

    try:
        handler_result = run_internal_read_only_handler(
            request.action_key,
            {**request.parameters, "version_id": request.version_id or request.parameters.get("version_id")},
            session,
        )
    except ValueError as exc:
        persist_dispatch_execution_event(
            dispatch_id=dispatch_id,
            action_key=request.action_key,
            event_type="blocked",
            status="blocked",
            handler_type="internal_read_only",
            endpoint_hint=request.endpoint_hint,
            method_hint=request.method_hint,
            token_id=request.token_id,
            version_id=request.version_id,
            detail={
                "plan_id": request.plan_id,
                "step_number": request.step_number,
                "blocking_reason": str(exc),
                "endpoint_hint_executed": False,
            },
            session=session,
        )
        create_result = persist_dispatch_result(
            dispatch_id=dispatch_id,
            action_key=request.action_key,
            status="blocked",
            dispatch_performed=False,
            handler_type="internal_read_only",
            token_confirmed=True,
            eligibility_passed=True,
            result_payload={},
            result_summary=str(exc),
            blocking_reasons=[str(exc)],
            endpoint_hint=request.endpoint_hint,
            method_hint=request.method_hint,
            token_id=request.token_id,
            version_id=request.version_id,
            parameters=request.parameters,
            audit_recorded=True,
            session=session,
        )
        return create_result

    result = persist_dispatch_result(
        dispatch_id=dispatch_id,
        action_key=request.action_key,
        status="completed",
        dispatch_performed=True,
        handler_type=handler_result.handler_type,
        token_confirmed=True,
        eligibility_passed=True,
        result_payload=handler_result.result_payload,
        result_summary=handler_result.result_summary,
        blocking_reasons=[],
        endpoint_hint=request.endpoint_hint,
        method_hint=request.method_hint,
        token_id=request.token_id,
        version_id=request.version_id,
        parameters=request.parameters,
        audit_recorded=True,
        session=session,
    )
    persist_dispatch_execution_event(
        dispatch_id=result.dispatch_id,
        action_key=request.action_key,
        event_type="completed",
        status="completed",
        handler_type=handler_result.handler_type,
        endpoint_hint=request.endpoint_hint,
        method_hint=request.method_hint,
        token_id=request.token_id,
        version_id=request.version_id,
        detail={
            "plan_id": request.plan_id,
            "step_number": request.step_number,
            "result_summary": handler_result.result_summary,
            "endpoint_hint_executed": False,
            "handler_selected_by": "action_key",
        },
        session=session,
    )
    return result
