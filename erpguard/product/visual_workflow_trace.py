"""Sprint 82 - sanitized visual workflow traces from supplied steps."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from erpguard.db.repositories import (
    create_visual_workflow_trace,
    create_visual_workflow_trace_audit_event,
    get_visual_browser_session_by_id,
    get_visual_observation_snapshot_by_id,
    get_visual_workflow_trace_by_id,
    list_visual_workflow_trace_audit_events,
    list_visual_workflow_traces,
)

ALLOWED_STEP_TYPES = {"navigate", "filter", "search", "open_record", "read_table", "read_form", "read_field", "compare_value", "human_decision", "note"}
BLOCKED_STEP_TYPES = {"click", "submit_form", "write_field", "create_record", "update_record", "delete_record", "confirm_order", "post_invoice", "reconcile_payment", "move_stock", "complete_manufacturing", "send_email"}
SECRET_MARKERS = {"password", "api_key", "token", "secret", "authorization", "bearer", "credential"}


@dataclass
class VisualWorkflowTraceInput:
    visual_session_id: str
    created_by: str = "operator_1"
    workflow_name: str = ""
    workflow_goal: str = ""
    observation_ids: list[str] = field(default_factory=list)
    steps: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class VisualWorkflowTrace:
    workflow_trace_id: str
    visual_session_id: str
    created_by: str
    status: str
    workflow_name: str
    workflow_goal: str
    observation_ids: list[str]
    steps: list[dict[str, Any]]
    dangerous_action_steps: list[dict[str, Any]]
    credential_touchpoints: list[dict[str, Any]]
    redaction_summary: dict[str, Any]
    safety_summary: dict[str, Any]
    blocking_reasons: list[str]


class VisualWorkflowTraceService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_trace(self, input: VisualWorkflowTraceInput) -> VisualWorkflowTrace:
        workflow_trace_id = f"vtrace_{uuid.uuid4().hex[:12]}"
        self._audit(workflow_trace_id, input.visual_session_id, "visual_workflow_trace_requested", "requested", input.created_by, {})
        visual_session = get_visual_browser_session_by_id(self.session, input.visual_session_id)
        sanitized = _sanitize(input)
        reason = self._blocking_reason(input, visual_session)
        status = "blocked" if reason else "created"
        row = create_visual_workflow_trace(
            self.session,
            workflow_trace_id=workflow_trace_id,
            visual_session_id=input.visual_session_id,
            created_by=input.created_by,
            status=status,
            workflow_name="" if reason else sanitized["workflow_name"],
            workflow_goal="" if reason else sanitized["workflow_goal"],
            observation_ids_json=json.dumps(input.observation_ids),
            steps_json=json.dumps([] if reason else sanitized["steps"], sort_keys=True),
            dangerous_action_steps_json=json.dumps([] if reason else sanitized["dangerous_steps"], sort_keys=True),
            credential_touchpoints_json=json.dumps([] if reason else sanitized["credential_touchpoints"], sort_keys=True),
            redaction_summary_json=json.dumps(sanitized["redaction_summary"], sort_keys=True),
            safety_summary_json=json.dumps(_safety_summary(), sort_keys=True),
            blocking_reasons_json=json.dumps([reason] if reason else []),
        )
        self._audit(
            workflow_trace_id,
            input.visual_session_id,
            "visual_workflow_trace_blocked" if reason else "visual_workflow_trace_created",
            status,
            input.created_by,
            {"blocked": bool(reason)},
        )
        return self._row_to_result(row)

    def get_trace(self, workflow_trace_id: str) -> dict[str, Any] | None:
        row = get_visual_workflow_trace_by_id(self.session, workflow_trace_id)
        if row is None:
            return None
        self._audit(row.workflow_trace_id, row.visual_session_id, "visual_workflow_trace_retrieved", row.status, row.created_by, {})
        return self._row_to_dict(row)

    def list_traces(self, limit: int = 50) -> list[dict[str, Any]]:
        return [self._row_to_dict(row) for row in list_visual_workflow_traces(self.session, limit=limit)]

    def _blocking_reason(self, input: VisualWorkflowTraceInput, visual_session: Any | None) -> str | None:
        if visual_session is None:
            return "visual_session_not_found"
        if visual_session.status == "revoked":
            return "visual_session_revoked"
        if visual_session.status == "blocked":
            return "visual_session_blocked"
        if not input.workflow_name.strip():
            return "workflow_name_required"
        if not input.steps:
            return "steps_required"
        for observation_id in input.observation_ids:
            observation = get_visual_observation_snapshot_by_id(self.session, observation_id)
            if observation is None:
                return "observation_not_found"
            if observation.status != "created":
                return "observation_not_created"
        for step in input.steps:
            if step.get("step_type") in BLOCKED_STEP_TYPES or step.get("step_type") not in ALLOWED_STEP_TYPES:
                return "blocked_step_type_supplied"
            touchpoint = step.get("credential_touchpoint")
            if isinstance(touchpoint, dict) and "value" in touchpoint:
                return "credential_value_supplied"
        if _contains_raw_secret_value(input):
            return "raw_secret_marker_detected"
        return None

    def _audit(self, workflow_trace_id: str, visual_session_id: str, event_type: str, status: str, actor: str, details: dict[str, Any]) -> None:
        create_visual_workflow_trace_audit_event(
            self.session,
            workflow_trace_id=workflow_trace_id,
            visual_session_id=visual_session_id,
            event_type=event_type,
            status=status,
            actor=actor,
            details_json=json.dumps(_safe_details(details), sort_keys=True),
        )

    def _row_to_result(self, row: Any) -> VisualWorkflowTrace:
        return VisualWorkflowTrace(**self._row_to_dict(row))

    def _row_to_dict(self, row: Any) -> dict[str, Any]:
        return {
            "workflow_trace_id": row.workflow_trace_id,
            "visual_session_id": row.visual_session_id,
            "created_by": row.created_by,
            "status": row.status,
            "workflow_name": row.workflow_name,
            "workflow_goal": row.workflow_goal,
            "observation_ids": json.loads(row.observation_ids_json),
            "steps": json.loads(row.steps_json),
            "dangerous_action_steps": json.loads(row.dangerous_action_steps_json),
            "credential_touchpoints": json.loads(row.credential_touchpoints_json),
            "redaction_summary": json.loads(row.redaction_summary_json),
            "safety_summary": json.loads(row.safety_summary_json),
            "blocking_reasons": json.loads(row.blocking_reasons_json),
        }


def _sanitize(input: VisualWorkflowTraceInput) -> dict[str, Any]:
    redacted: list[str] = []
    steps: list[dict[str, Any]] = []
    credential_touchpoints: list[dict[str, Any]] = []
    for index, step in enumerate(input.steps):
        clean_step = {str(key): _sanitize_value(value, f"steps[{index}].{key}", redacted) for key, value in step.items() if key != "credential_touchpoint"}
        touchpoint = step.get("credential_touchpoint")
        if isinstance(touchpoint, dict):
            credential_touchpoints.append({
                "step_index": index,
                "field_label": _sanitize_text(str(touchpoint.get("field_label", "")), f"touchpoints[{index}].field_label", redacted),
                "touchpoint_type": _sanitize_text(str(touchpoint.get("touchpoint_type", "")), f"touchpoints[{index}].touchpoint_type", redacted),
                "value_present": bool(touchpoint.get("value_present", False)),
                "value_stored": False,
            })
        steps.append(clean_step)
    return {
        "workflow_name": _sanitize_text(input.workflow_name, "workflow_name", redacted),
        "workflow_goal": _sanitize_text(input.workflow_goal, "workflow_goal", redacted),
        "steps": steps,
        "dangerous_steps": [],
        "credential_touchpoints": credential_touchpoints,
        "redaction_summary": {"redacted_fields": sorted(set(redacted)), "redaction_performed": bool(redacted)},
    }


def _sanitize_value(value: Any, path: str, redacted: list[str]) -> Any:
    if isinstance(value, str):
        return _sanitize_text(value, path, redacted)
    if isinstance(value, list):
        return [_sanitize_value(item, f"{path}[]", redacted) for item in value]
    if isinstance(value, dict):
        return {str(key): _sanitize_value(item, f"{path}.{key}", redacted) for key, item in value.items()}
    return value


def _sanitize_text(value: str, path: str, redacted: list[str]) -> str:
    if any(marker in value.lower() for marker in SECRET_MARKERS):
        redacted.append(path)
        return "<redacted>"
    return value


def _contains_raw_secret_value(input: VisualWorkflowTraceInput) -> bool:
    raw = json.dumps(input.__dict__, default=str).lower()
    return bool(re.search(r"(password|api_key|token|secret|authorization|bearer|credential)\s*[:=]\s*[^,\s]+", raw))


def _safety_summary() -> dict[str, Any]:
    return {
        "trace_only": True,
        "browser_launched": False,
        "browser_control_performed": False,
        "automatic_clicks_performed": False,
        "form_submission_performed": False,
        "action_execution_performed": False,
        "dom_observation_performed": False,
        "screen_capture_performed": False,
        "workflow_recording_performed": False,
        "simulated_workflow_recording": True,
        "credentials_exposed": False,
        "raw_secret_accessed": False,
        "mcp_execution_performed": False,
        "scheduler_used": False,
        "erp_write_performed": False,
    }


def _safe_details(details: dict[str, Any]) -> dict[str, Any]:
    return {"blocked": bool(details.get("blocked", False))} if "blocked" in details else {}


@dataclass
class VisualWorkflowTraceAuditResult:
    events: list[dict[str, Any]]


class VisualWorkflowTraceAuditService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_audit(self, limit: int = 50) -> VisualWorkflowTraceAuditResult:
        return VisualWorkflowTraceAuditResult(events=[
            {
                "event_type": row.event_type,
                "workflow_trace_id": row.workflow_trace_id,
                "visual_session_id": row.visual_session_id,
                "status": row.status,
                "actor": row.actor,
                "details": _safe_details(json.loads(row.details_json)),
                "created_at": row.created_at,
            }
            for row in list_visual_workflow_trace_audit_events(self.session, limit=limit)
        ])
