from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from erpguard.product.agent_skill_run_preview import get_run_preview
from erpguard.product.governance_gap_explainer import explain_governance_gaps
from erpguard.product.operator_next_step_recommender import recommend_next_steps
from erpguard.product.semantic_skill_discovery import search_skills
from erpguard.product.skill_lifecycle_summary import get_lifecycle_summary
from erpguard.product.skill_reuse_suggester import get_reuse_suggestions


@dataclass(frozen=True)
class InternalReadOnlyHandlerResult:
    action_key: str
    result_payload: dict[str, Any]
    result_summary: str
    handler_type: str = "internal_read_only"
    erp_writes_performed: bool = False
    browser_control_performed: bool = False
    mcp_execution_performed: bool = False
    llm_runtime_used: bool = False
    system_state_mutated: bool = False
    skill_mutated: bool = False
    activation_performed: bool = False
    scheduling_performed: bool = False


def _require_version_id(action_key: str, parameters: dict[str, Any]) -> str:
    version_id = parameters.get("version_id")
    if not isinstance(version_id, str) or not version_id.strip():
        raise ValueError(f"{action_key}_requires_version_id")
    return version_id.strip()


def _handle_check_governance_gaps(parameters: dict[str, Any], session) -> InternalReadOnlyHandlerResult:
    version_id = _require_version_id("check_governance_gaps", parameters)
    result = explain_governance_gaps(version_id, session)
    payload = {
        "version_id": result.version_id,
        "skill_id": result.skill_id,
        "gap_count": result.gap_count,
        "is_fully_governed": result.is_fully_governed,
        "blocking_reason": result.blocking_reason,
        "gaps": [
            {
                "gap_type": gap.gap_type,
                "description": gap.description,
                "severity": gap.severity,
                "suggested_action": gap.suggested_action,
            }
            for gap in result.gaps
        ],
    }
    return InternalReadOnlyHandlerResult(
        action_key="check_governance_gaps",
        result_payload=payload,
        result_summary=f"Governance gaps inspected for version '{version_id}'. Found {result.gap_count} gaps.",
    )


def _handle_search_skills(parameters: dict[str, Any], session) -> InternalReadOnlyHandlerResult:
    query = str(parameters.get("query") or "").strip()
    status_filter = parameters.get("status_filter")
    runtime_type_filter = parameters.get("runtime_type_filter")
    active_only = bool(parameters.get("active_only", False))
    limit = int(parameters.get("limit", 20) or 20)
    result = search_skills(
        query,
        session,
        status_filter=status_filter if isinstance(status_filter, str) and status_filter else None,
        runtime_type_filter=runtime_type_filter if isinstance(runtime_type_filter, str) and runtime_type_filter else None,
        active_only=active_only,
        limit=limit,
    )
    payload = {
        "query": result.query,
        "total_found": result.total_found,
        "results": [
            {
                "version_id": hit.version_id,
                "skill_id": hit.skill_id,
                "name": hit.name,
                "status": hit.status,
                "is_active": hit.is_active,
                "runtime_type": hit.runtime_type,
                "relevance_score": hit.relevance_score,
                "match_reason": hit.match_reason,
                "guard_names": hit.guard_names,
                "step_count": hit.step_count,
            }
            for hit in result.results
        ],
    }
    return InternalReadOnlyHandlerResult(
        action_key="search_skills",
        result_payload=payload,
        result_summary=f"Skill search completed for query '{query}'. Returned {result.total_found} results.",
    )


def _handle_reuse_suggestions(parameters: dict[str, Any], session) -> InternalReadOnlyHandlerResult:
    query = str(parameters.get("query") or "").strip()
    version_id = parameters.get("version_id")
    version_id_value = version_id.strip() if isinstance(version_id, str) and version_id.strip() else None
    limit = int(parameters.get("limit", 10) or 10)
    result = get_reuse_suggestions(
        session,
        query=query,
        version_id=version_id_value,
        limit=limit,
    )
    payload = {
        "query": result.query,
        "reference_version_id": version_id_value,
        "total_found": result.total_found,
        "suggestions": [
            {
                "version_id": suggestion.version_id,
                "skill_id": suggestion.skill_id,
                "name": suggestion.name,
                "reuse_rationale": suggestion.reuse_rationale,
                "similarity_score": suggestion.similarity_score,
                "is_active": suggestion.is_active,
                "governance_complete": suggestion.governance_complete,
                "next_step": suggestion.next_step,
            }
            for suggestion in result.suggestions
        ],
    }
    return InternalReadOnlyHandlerResult(
        action_key="reuse_suggestions",
        result_payload=payload,
        result_summary=f"Reuse suggestions evaluated. Returned {result.total_found} read-only suggestions.",
    )


def _handle_inspect_lifecycle(parameters: dict[str, Any], session) -> InternalReadOnlyHandlerResult:
    version_id = _require_version_id("inspect_lifecycle", parameters)
    result = get_lifecycle_summary(version_id, session)
    payload = {
        "version_id": result.version_id,
        "skill_id": result.skill_id,
        "name": result.name,
        "status": result.status,
        "is_active": result.is_active,
        "runtime_type": result.runtime_type,
        "governance_status": result.governance_status,
        "has_human_decision": result.has_human_decision,
        "human_decision": result.human_decision,
        "has_activation_request": result.has_activation_request,
        "has_run_preview": result.has_run_preview,
        "llm_required": result.llm_required,
        "preview_event_count": result.preview_event_count,
        "blocking_reason": result.blocking_reason,
        "lifecycle_events": [
            {
                "event_type": event.event_type,
                "from_status": event.from_status,
                "to_status": event.to_status,
                "actor": event.actor,
                "created_at": event.created_at,
            }
            for event in result.lifecycle_events
        ],
    }
    return InternalReadOnlyHandlerResult(
        action_key="inspect_lifecycle",
        result_payload=payload,
        result_summary=f"Lifecycle inspected for version '{version_id}'. Governance status is '{result.governance_status}'.",
    )


def _handle_recommend_next_step(parameters: dict[str, Any], session) -> InternalReadOnlyHandlerResult:
    version_id = _require_version_id("recommend_next_step", parameters)
    result = recommend_next_steps(version_id, session)
    payload = {
        "version_id": result.version_id,
        "skill_id": result.skill_id,
        "governance_status": result.governance_status,
        "step_count": result.step_count,
        "all_steps_complete": result.all_steps_complete,
        "blocking_reason": result.blocking_reason,
        "next_steps": [
            {
                "step_number": step.step_number,
                "action": step.action,
                "rationale": step.rationale,
                "endpoint_hint": step.endpoint_hint,
                "severity": step.severity,
            }
            for step in result.next_steps
        ],
    }
    return InternalReadOnlyHandlerResult(
        action_key="recommend_next_step",
        result_payload=payload,
        result_summary=f"Next-step recommendations prepared for version '{version_id}'. Found {result.step_count} steps.",
    )


def _handle_run_preview(parameters: dict[str, Any], session) -> InternalReadOnlyHandlerResult:
    version_id = _require_version_id("run_preview", parameters)
    result = get_run_preview(version_id, session)
    if result.blocking_reason:
        raise ValueError(result.blocking_reason)
    payload = {
        "version_id": result.version_id,
        "skill_id": result.skill_id,
        "preview_ready": result.preview_ready,
        "eligible": result.eligible,
        "plan_ready": result.plan_ready,
        "gate_passed": result.gate_passed,
        "execution_ready": result.execution_ready,
        "step_count": result.step_count,
        "runtime_type": result.runtime_type,
        "guard_names": result.guard_names,
        "will_execute": result.will_execute,
        "can_execute": result.can_execute,
    }
    return InternalReadOnlyHandlerResult(
        action_key="run_preview",
        result_payload=payload,
        result_summary=f"Preview evaluated for version '{version_id}'. Ready: {result.preview_ready}.",
    )


_HANDLERS = {
    "check_governance_gaps": _handle_check_governance_gaps,
    "inspect_lifecycle": _handle_inspect_lifecycle,
    "recommend_next_step": _handle_recommend_next_step,
    "reuse_suggestions": _handle_reuse_suggestions,
    "run_preview": _handle_run_preview,
    "search_skills": _handle_search_skills,
}


def list_dispatchable_actions() -> list[str]:
    return sorted(_HANDLERS.keys())


def run_internal_read_only_handler(action_key: str, parameters: dict[str, Any], session) -> InternalReadOnlyHandlerResult:
    handler = _HANDLERS.get(action_key)
    if handler is None:
        raise ValueError(f"unsupported_dispatch_action:{action_key}")
    return handler(parameters, session)
