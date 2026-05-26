from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any

from erpguard.db.repositories import (
    create_action_dispatch_result_record,
    get_action_dispatch_result_record,
)


@dataclass(frozen=True)
class OperatorActionDispatchResult:
    dispatch_id: str
    action_key: str
    status: str
    dispatch_performed: bool
    handler_type: str
    token_confirmed: bool
    eligibility_passed: bool
    result_payload: dict[str, Any] = field(default_factory=dict)
    result_summary: str = ""
    blocking_reasons: list[str] = field(default_factory=list)
    erp_writes_performed: bool = False
    browser_control_performed: bool = False
    mcp_execution_performed: bool = False
    llm_runtime_used: bool = False
    system_state_mutated: bool = False
    skill_mutated: bool = False
    activation_performed: bool = False
    scheduling_performed: bool = False
    audit_recorded: bool = False
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


def _serialize(value: dict[str, Any] | list[str]) -> str:
    return json.dumps(value, default=str, sort_keys=True)


def persist_dispatch_result(
    *,
    dispatch_id: str | None = None,
    action_key: str,
    status: str,
    dispatch_performed: bool,
    handler_type: str,
    token_confirmed: bool,
    eligibility_passed: bool,
    result_payload: dict[str, Any],
    result_summary: str,
    blocking_reasons: list[str],
    endpoint_hint: str,
    method_hint: str,
    token_id: str | None,
    version_id: str | None,
    parameters: dict[str, Any],
    audit_recorded: bool,
    session,
) -> OperatorActionDispatchResult:
    dispatch_id = dispatch_id or f"disp_{uuid.uuid4().hex[:16]}"
    create_action_dispatch_result_record(
        session,
        dispatch_id=dispatch_id,
        action_key=action_key,
        status=status,
        handler_type=handler_type,
        endpoint_hint=endpoint_hint,
        method_hint=method_hint,
        token_id=token_id,
        version_id=version_id,
        parameters_json=_serialize(parameters),
        result_payload_json=_serialize(result_payload),
        result_summary=result_summary,
        blocking_reasons_json=_serialize(blocking_reasons),
        token_confirmed=token_confirmed,
        eligibility_passed=eligibility_passed,
        dispatch_performed=dispatch_performed,
        erp_writes_performed=False,
        browser_control_performed=False,
        mcp_execution_performed=False,
        llm_runtime_used=False,
        system_state_mutated=False,
        skill_mutated=False,
        activation_performed=False,
        scheduling_performed=False,
        audit_recorded=audit_recorded,
    )
    return OperatorActionDispatchResult(
        dispatch_id=dispatch_id,
        action_key=action_key,
        status=status,
        dispatch_performed=dispatch_performed,
        handler_type=handler_type,
        token_confirmed=token_confirmed,
        eligibility_passed=eligibility_passed,
        result_payload=result_payload,
        result_summary=result_summary,
        blocking_reasons=blocking_reasons,
        audit_recorded=audit_recorded,
    )


def get_dispatch_result(dispatch_id: str, session) -> OperatorActionDispatchResult | None:
    row = get_action_dispatch_result_record(session, dispatch_id)
    if row is None:
        return None
    return OperatorActionDispatchResult(
        dispatch_id=row.id,
        action_key=row.action_key,
        status=row.status,
        dispatch_performed=row.dispatch_performed,
        handler_type=row.handler_type,
        token_confirmed=row.token_confirmed,
        eligibility_passed=row.eligibility_passed,
        result_payload=json.loads(row.result_payload_json or "{}"),
        result_summary=row.result_summary,
        blocking_reasons=json.loads(row.blocking_reasons_json or "[]"),
        erp_writes_performed=row.erp_writes_performed,
        browser_control_performed=row.browser_control_performed,
        mcp_execution_performed=row.mcp_execution_performed,
        llm_runtime_used=row.llm_runtime_used,
        system_state_mutated=row.system_state_mutated,
        skill_mutated=row.skill_mutated,
        activation_performed=row.activation_performed,
        scheduling_performed=row.scheduling_performed,
        audit_recorded=row.audit_recorded,
    )
