from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from erpguard.product.operator_action_dispatch_eligibility import check_eligibility
from erpguard.product.operator_action_dispatch_execution_audit import persist_dispatch_execution_event
from erpguard.product.operator_action_dispatch_handlers import (
    InternalReadOnlyHandlerResult,
    list_dispatchable_actions,
    run_internal_read_only_handler,
)
from erpguard.product.operator_action_dispatch_result import (
    OperatorActionDispatchResult,
    persist_dispatch_result,
)
from erpguard.product.operator_action_governance_mutation_handlers import (
    InternalGovernanceMutationHandlerResult,
    list_governance_mutation_actions,
    run_internal_governance_mutation_handler,
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
    handler_type: str = "internal_read_only",
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
        handler_type=handler_type,
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
        handler_type=handler_type,
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


def dispatch_confirmed_action(
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
                "Only explicitly registered allowlist actions may be dispatched."
            ),
            session=session,
        )

    read_only_keys = list_dispatchable_actions()
    mutation_keys = list_governance_mutation_actions()

    if request.action_key in read_only_keys:
        handler_type = "internal_read_only"
    elif request.action_key in mutation_keys:
        handler_type = "internal_governance_mutation"
    else:
        return _persist_blocked(
            request=request,
            reason=(
                f"Action '{request.action_key}' is not available in the dispatch registry. "
                "Check the action key and sprint allowlist."
            ),
            session=session,
        )

    token = get_token_status(request.token_id, session)
    if token is None:
        return _persist_blocked(
            request=request,
            reason="Confirmed token required for dispatch. Token was not found.",
            handler_type=handler_type,
            session=session,
        )
    if token.status != "confirmed":
        return _persist_blocked(
            request=request,
            reason=(
                f"Confirmed token required for dispatch. Token status is '{token.status}'."
            ),
            handler_type=handler_type,
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
            handler_type=handler_type,
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
        handler_type=handler_type,
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

    parameters = {
        **request.parameters,
        "version_id": request.version_id or request.parameters.get("version_id"),
    }

    handler_result: InternalReadOnlyHandlerResult | InternalGovernanceMutationHandlerResult
    try:
        if handler_type == "internal_read_only":
            handler_result = run_internal_read_only_handler(
                request.action_key, parameters, session
            )
            system_state_mutated = False
            skill_mutated = False
            activation_performed = False
        else:
            handler_result = run_internal_governance_mutation_handler(
                request.action_key, parameters, session
            )
            system_state_mutated = handler_result.system_state_mutated
            skill_mutated = handler_result.skill_mutated
            activation_performed = handler_result.activation_performed
    except ValueError as exc:
        persist_dispatch_execution_event(
            dispatch_id=dispatch_id,
            action_key=request.action_key,
            event_type="blocked",
            status="blocked",
            handler_type=handler_type,
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
        return persist_dispatch_result(
            dispatch_id=dispatch_id,
            action_key=request.action_key,
            status="blocked",
            dispatch_performed=False,
            handler_type=handler_type,
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
        system_state_mutated=system_state_mutated,
        skill_mutated=skill_mutated,
        activation_performed=activation_performed,
        session=session,
    )
    completed_detail = {
        "plan_id": request.plan_id,
        "step_number": request.step_number,
        "result_summary": handler_result.result_summary,
        "endpoint_hint_executed": False,
        "handler_selected_by": "action_key",
    }
    if handler_type == "internal_governance_mutation":
        actor_value = request.parameters.get("actor") or request.parameters.get("requested_by")
        underlying_artifact_type: str | None = {
            "record_human_decision": "decision",
            "create_activation_request": "activation_request",
            "activate_candidate": "activation",
        }.get(request.action_key)
        underlying_artifact_id: str | None = None
        if request.action_key == "record_human_decision":
            underlying_artifact_id = str(handler_result.result_payload.get("decision_id") or "").strip() or None
        elif request.action_key == "create_activation_request":
            underlying_artifact_id = str(handler_result.result_payload.get("request_id") or "").strip() or None
        elif request.action_key == "activate_candidate":
            underlying_artifact_id = str(
                handler_result.result_payload.get("version_id") or handler_result.result_payload.get("skill_id") or ""
            ).strip() or None
        assert isinstance(handler_result, InternalGovernanceMutationHandlerResult)
        completed_detail.update(
            {
                "previous_state": handler_result.previous_state,
                "new_state": handler_result.new_state,
                "actor": str(actor_value).strip() if actor_value is not None else None,
                "underlying_artifact_type": underlying_artifact_type,
                "underlying_artifact_id": underlying_artifact_id,
            }
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
        detail=completed_detail,
        session=session,
    )
    return result


# Alias for backward compatibility with Sprint 45 callers
dispatch_confirmed_read_only_action = dispatch_confirmed_action
