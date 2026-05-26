from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from erpguard.product.agent_candidate_activation_request import (
    create_activation_request as _create_activation_request,
)
from erpguard.product.agent_candidate_activation_service import activate_candidate_version
from erpguard.product.agent_candidate_human_decision import record_human_decision as _record_human_decision


@dataclass(frozen=True)
class InternalGovernanceMutationHandlerResult:
    action_key: str
    result_payload: dict[str, Any]
    result_summary: str
    previous_state: dict[str, Any]
    new_state: dict[str, Any]
    handler_type: str = "internal_governance_mutation"
    erp_writes_performed: bool = False
    browser_control_performed: bool = False
    mcp_execution_performed: bool = False
    llm_runtime_used: bool = False
    system_state_mutated: bool = True
    skill_mutated: bool = False
    activation_performed: bool = False
    scheduling_performed: bool = False


def _require_version_id(action_key: str, parameters: dict[str, Any]) -> str:
    version_id = parameters.get("version_id")
    if not isinstance(version_id, str) or not version_id.strip():
        raise ValueError(f"{action_key}_requires_version_id")
    return version_id.strip()


def _handle_record_human_decision(
    parameters: dict[str, Any], session
) -> InternalGovernanceMutationHandlerResult:
    version_id = _require_version_id("record_human_decision", parameters)
    decision = str(parameters.get("decision") or "").strip()
    actor = str(parameters.get("actor") or "").strip()
    rationale = str(parameters.get("rationale") or "").strip()
    if not decision:
        raise ValueError("record_human_decision_requires_decision")
    if not actor:
        raise ValueError("record_human_decision_requires_actor")

    previous_state: dict[str, Any] = {"decision": "none", "governance_status": "pending"}
    result = _record_human_decision(version_id, decision, actor, rationale, session=session)
    if result.blocking_reason:
        raise ValueError(result.blocking_reason)

    new_state: dict[str, Any] = {
        "decision": result.decision,
        "governance_status": result.governance_status,
        "decision_id": result.decision_id,
    }
    payload = {
        "version_id": result.version_id,
        "skill_id": result.skill_id,
        "decision_id": result.decision_id,
        "decision": result.decision,
        "actor": result.actor,
        "rationale": result.rationale,
        "governance_status": result.governance_status,
        "version_status": result.version_status,
    }
    return InternalGovernanceMutationHandlerResult(
        action_key="record_human_decision",
        result_payload=payload,
        result_summary=(
            f"Human decision '{decision}' recorded for version '{version_id}'. "
            f"Governance status: '{result.governance_status}'."
        ),
        previous_state=previous_state,
        new_state=new_state,
    )


def _handle_create_activation_request(
    parameters: dict[str, Any], session
) -> InternalGovernanceMutationHandlerResult:
    version_id = _require_version_id("create_activation_request", parameters)
    requested_by = str(
        parameters.get("requested_by") or parameters.get("actor") or ""
    ).strip()
    rationale = str(parameters.get("rationale") or "").strip()
    if not requested_by:
        raise ValueError("create_activation_request_requires_requested_by")

    previous_state: dict[str, Any] = {"activation_request_exists": False}
    result = _create_activation_request(version_id, requested_by, rationale, session=session)
    if not result.eligible and result.blocking_reason:
        raise ValueError(result.blocking_reason)

    new_state: dict[str, Any] = {
        "activation_request_exists": True,
        "request_id": result.request_id,
        "request_status": result.request_status,
    }
    payload = {
        "version_id": result.version_id,
        "skill_id": result.skill_id,
        "request_id": result.request_id,
        "request_status": result.request_status,
        "requested_by": result.requested_by,
        "rationale": result.rationale,
        "eligible": result.eligible,
    }
    return InternalGovernanceMutationHandlerResult(
        action_key="create_activation_request",
        result_payload=payload,
        result_summary=(
            f"Activation request '{result.request_id}' created for version '{version_id}'. "
            f"Status: '{result.request_status}'."
        ),
        previous_state=previous_state,
        new_state=new_state,
    )


def _handle_activate_candidate(
    parameters: dict[str, Any], session
) -> InternalGovernanceMutationHandlerResult:
    version_id = _require_version_id("activate_candidate", parameters)
    actor = str(parameters.get("actor") or "").strip()
    if not actor:
        raise ValueError("activate_candidate_requires_actor")

    previous_state: dict[str, Any] = {"version_status": "candidate", "is_active": False}
    result = activate_candidate_version(version_id, actor=actor, session=session)
    if not result.activated and result.blocking_reason:
        raise ValueError(result.blocking_reason)

    new_state: dict[str, Any] = {
        "version_status": result.version_status,
        "is_active": result.is_active,
        "activated": result.activated,
        "prior_version_deactivated": result.prior_version_deactivated,
    }
    payload = {
        "version_id": result.version_id,
        "skill_id": result.skill_id,
        "activated": result.activated,
        "prior_version_deactivated": result.prior_version_deactivated,
        "prior_version_id": result.prior_version_id,
        "version_status": result.version_status,
        "is_active": result.is_active,
        "is_executed": result.is_executed,
        "can_execute": result.can_execute,
    }
    return InternalGovernanceMutationHandlerResult(
        action_key="activate_candidate",
        result_payload=payload,
        result_summary=(
            f"Candidate version '{version_id}' activated. "
            f"Prior version deactivated: {result.prior_version_deactivated}."
        ),
        previous_state=previous_state,
        new_state=new_state,
        activation_performed=True,
        skill_mutated=True,
    )


_GOVERNANCE_MUTATION_HANDLERS: dict[str, Any] = {
    "activate_candidate": _handle_activate_candidate,
    "create_activation_request": _handle_create_activation_request,
    "record_human_decision": _handle_record_human_decision,
}


def list_governance_mutation_actions() -> list[str]:
    return sorted(_GOVERNANCE_MUTATION_HANDLERS.keys())


def run_internal_governance_mutation_handler(
    action_key: str,
    parameters: dict[str, Any],
    session,
) -> InternalGovernanceMutationHandlerResult:
    handler = _GOVERNANCE_MUTATION_HANDLERS.get(action_key)
    if handler is None:
        raise ValueError(f"unsupported_governance_mutation_action:{action_key}")
    return handler(parameters, session)
