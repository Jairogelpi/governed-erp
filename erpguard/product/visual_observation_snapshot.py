"""Sprint 81 - sanitized visual observation snapshots from supplied payloads."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from erpguard.db.repositories import (
    create_visual_observation_audit_event,
    create_visual_observation_snapshot,
    get_visual_browser_session_by_id,
    get_visual_observation_snapshot_by_id,
    list_visual_observation_audit_events,
    list_visual_observation_snapshots,
)

RAW_SECRET_MARKERS = {"password", "api_key", "token", "secret", "authorization", "bearer", "credential"}
DANGEROUS_LABELS = {
    "confirmar", "validar", "publicar", "reconciliar", "pagar", "enviar",
    "eliminar", "archivar", "transferir", "marcar como hecho", "done",
    "post", "validate", "delete", "confirm", "pay", "send",
}


@dataclass
class VisualObservationSnapshotInput:
    visual_session_id: str
    created_by: str = "operator_1"
    observation_source: str = "mocked_payload"
    screen_summary: dict[str, Any] = field(default_factory=dict)
    dom_summary: dict[str, Any] = field(default_factory=dict)
    visible_text: list[str] = field(default_factory=list)
    tables: list[dict[str, Any]] = field(default_factory=list)
    forms: list[dict[str, Any]] = field(default_factory=list)
    buttons: list[dict[str, Any]] = field(default_factory=list)
    credential_fields_detected: list[dict[str, Any]] = field(default_factory=list)
    dangerous_action_candidates: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class VisualObservationSnapshot:
    observation_id: str
    visual_session_id: str
    created_by: str
    target_url: str
    target_host: str
    status: str
    observation_source: str
    screen_summary: dict[str, Any]
    dom_summary: dict[str, Any]
    visible_text_redacted: list[str]
    detected_tables: list[dict[str, Any]]
    detected_forms: list[dict[str, Any]]
    detected_buttons: list[dict[str, Any]]
    credential_fields_detected: list[dict[str, Any]]
    dangerous_action_candidates: list[dict[str, Any]]
    redaction_summary: dict[str, Any]
    safety_summary: dict[str, Any]
    blocking_reasons: list[str]


class VisualObservationSnapshotService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_snapshot(self, input: VisualObservationSnapshotInput) -> VisualObservationSnapshot:
        observation_id = f"vobs_{uuid.uuid4().hex[:12]}"
        self._audit(observation_id, input.visual_session_id, "visual_observation_snapshot_requested", "requested", input.created_by, {})
        visual_session = get_visual_browser_session_by_id(self.session, input.visual_session_id)
        reason = self._blocking_reason(input, visual_session)
        sanitized = _sanitize_payload(input)
        status = "blocked" if reason else "created"
        row = create_visual_observation_snapshot(
            self.session,
            observation_id=observation_id,
            visual_session_id=input.visual_session_id,
            created_by=input.created_by,
            target_url=getattr(visual_session, "target_url", ""),
            target_host=getattr(visual_session, "target_host", ""),
            status=status,
            observation_source=input.observation_source,
            screen_summary_json=json.dumps({} if reason else sanitized["screen_summary"], sort_keys=True),
            dom_summary_json=json.dumps({} if reason else sanitized["dom_summary"], sort_keys=True),
            visible_text_redacted_json=json.dumps([] if reason else sanitized["visible_text_redacted"]),
            detected_tables_json=json.dumps([] if reason else sanitized["tables"], sort_keys=True),
            detected_forms_json=json.dumps([] if reason else sanitized["forms"], sort_keys=True),
            detected_buttons_json=json.dumps([] if reason else sanitized["buttons"], sort_keys=True),
            credential_fields_detected_json=json.dumps([] if reason else sanitized["credential_fields"], sort_keys=True),
            dangerous_action_candidates_json=json.dumps([] if reason else sanitized["dangerous_actions"], sort_keys=True),
            redaction_summary_json=json.dumps(sanitized["redaction_summary"], sort_keys=True),
            safety_summary_json=json.dumps(_safety_summary(), sort_keys=True),
            blocking_reasons_json=json.dumps([reason] if reason else []),
        )
        self._audit(
            observation_id,
            input.visual_session_id,
            "visual_observation_snapshot_blocked" if reason else "visual_observation_snapshot_created",
            status,
            input.created_by,
            {"blocked": bool(reason)},
        )
        return self._row_to_result(row)

    def get_snapshot(self, observation_id: str) -> dict[str, Any] | None:
        row = get_visual_observation_snapshot_by_id(self.session, observation_id)
        if row is None:
            return None
        self._audit(row.observation_id, row.visual_session_id, "visual_observation_snapshot_retrieved", row.status, row.created_by, {})
        return self._row_to_dict(row)

    def list_snapshots(self, limit: int = 50) -> list[dict[str, Any]]:
        return [self._row_to_dict(row) for row in list_visual_observation_snapshots(self.session, limit=limit)]

    def _blocking_reason(self, input: VisualObservationSnapshotInput, visual_session: Any | None) -> str | None:
        if visual_session is None:
            return "visual_session_not_found"
        if visual_session.status == "revoked":
            return "visual_session_revoked"
        if visual_session.status == "blocked":
            return "visual_session_blocked"
        if not any([input.screen_summary, input.dom_summary, input.visible_text, input.tables, input.forms, input.buttons]):
            return "observation_payload_required"
        for field in input.credential_fields_detected:
            if field.get("value_present") is True:
                return "credential_visibility_forbidden"
            if "value" in field:
                return "raw_secret_marker_detected"
        if _contains_raw_secret_value(input):
            return "raw_secret_marker_detected"
        return None

    def _audit(self, observation_id: str, visual_session_id: str, event_type: str, status: str, actor: str, details: dict[str, Any]) -> None:
        create_visual_observation_audit_event(
            self.session,
            observation_id=observation_id,
            visual_session_id=visual_session_id,
            event_type=event_type,
            status=status,
            actor=actor,
            details_json=json.dumps(_safe_audit_details(details), sort_keys=True),
        )

    def _row_to_result(self, row: Any) -> VisualObservationSnapshot:
        return VisualObservationSnapshot(**self._row_to_dict(row))

    def _row_to_dict(self, row: Any) -> dict[str, Any]:
        return {
            "observation_id": row.observation_id,
            "visual_session_id": row.visual_session_id,
            "created_by": row.created_by,
            "target_url": row.target_url,
            "target_host": row.target_host,
            "status": row.status,
            "observation_source": row.observation_source,
            "screen_summary": json.loads(row.screen_summary_json),
            "dom_summary": json.loads(row.dom_summary_json),
            "visible_text_redacted": json.loads(row.visible_text_redacted_json),
            "detected_tables": json.loads(row.detected_tables_json),
            "detected_forms": json.loads(row.detected_forms_json),
            "detected_buttons": json.loads(row.detected_buttons_json),
            "credential_fields_detected": json.loads(row.credential_fields_detected_json),
            "dangerous_action_candidates": json.loads(row.dangerous_action_candidates_json),
            "redaction_summary": json.loads(row.redaction_summary_json),
            "safety_summary": json.loads(row.safety_summary_json),
            "blocking_reasons": json.loads(row.blocking_reasons_json),
        }


def _sanitize_payload(input: VisualObservationSnapshotInput) -> dict[str, Any]:
    redacted: list[str] = []
    screen = _sanitize_mapping(input.screen_summary, "screen_summary", redacted)
    dom = _sanitize_mapping(input.dom_summary, "dom_summary", redacted)
    visible_text = [_sanitize_text(item, f"visible_text[{idx}]", redacted) for idx, item in enumerate(input.visible_text)]
    tables = [_sanitize_mapping(table, f"tables[{idx}]", redacted) for idx, table in enumerate(input.tables)]
    forms = [_sanitize_mapping(form, f"forms[{idx}]", redacted) for idx, form in enumerate(input.forms)]
    buttons = [_sanitize_mapping(button, f"buttons[{idx}]", redacted) for idx, button in enumerate(input.buttons)]
    credential_fields = [
        {
            "field_label": _sanitize_text(str(field.get("field_label", "")), "credential_field_label", redacted),
            "field_type": _sanitize_text(str(field.get("field_type", "")), "credential_field_type", redacted),
            "selector_hint_redacted": "<redacted>" if field.get("selector_hint_redacted") else "",
            "value_present": bool(field.get("value_present", False)),
        }
        for field in input.credential_fields_detected
    ]
    dangerous = _dangerous_actions(buttons, input.dangerous_action_candidates)
    return {
        "screen_summary": screen,
        "dom_summary": dom,
        "visible_text_redacted": visible_text,
        "tables": tables,
        "forms": forms,
        "buttons": buttons,
        "credential_fields": credential_fields,
        "dangerous_actions": dangerous,
        "redaction_summary": {"redacted_fields": sorted(set(redacted)), "redaction_performed": bool(redacted)},
    }


def _sanitize_mapping(value: dict[str, Any], prefix: str, redacted: list[str]) -> dict[str, Any]:
    return {str(key): _sanitize_value(item, f"{prefix}.{key}", redacted) for key, item in value.items()}


def _sanitize_value(value: Any, path: str, redacted: list[str]) -> Any:
    if isinstance(value, str):
        return _sanitize_text(value, path, redacted)
    if isinstance(value, list):
        return [_sanitize_value(item, f"{path}[]", redacted) for item in value]
    if isinstance(value, dict):
        return _sanitize_mapping(value, path, redacted)
    return value


def _sanitize_text(value: str, path: str, redacted: list[str]) -> str:
    lower = value.lower()
    if any(marker in lower for marker in RAW_SECRET_MARKERS):
        redacted.append(path)
        return "<redacted>"
    return value


def _contains_raw_secret_value(input: VisualObservationSnapshotInput) -> bool:
    raw = json.dumps(input.__dict__, default=str).lower()
    pattern = r"(password|api_key|token|secret|authorization|bearer|credential)\s*[:=]\s*[^,\\s]+"
    return bool(re.search(pattern, raw))


def _dangerous_actions(buttons: list[dict[str, Any]], supplied: list[dict[str, Any]]) -> list[dict[str, Any]]:
    labels = [str(button.get("label", "")) for button in buttons]
    labels.extend(str(item.get("label", "")) for item in supplied)
    result = []
    for label in labels:
        if label.lower() in DANGEROUS_LABELS:
            result.append({
                "label": label,
                "risk_level": "high",
                "reason": "dangerous_action_label_detected",
                "requires_human_approval": True,
                "auto_execute_allowed": False,
            })
    return result


def _safety_summary() -> dict[str, Any]:
    return {
        "observation_only": True,
        "browser_launched": False,
        "browser_control_performed": False,
        "automatic_clicks_performed": False,
        "form_submission_performed": False,
        "action_execution_performed": False,
        "dom_observation_performed": False,
        "simulated_dom_observation": True,
        "screen_capture_performed": False,
        "simulated_screen_observation": True,
        "workflow_recording_performed": False,
        "credentials_exposed": False,
        "raw_secret_accessed": False,
        "mcp_execution_performed": False,
        "scheduler_used": False,
        "erp_write_performed": False,
    }


def _safe_audit_details(details: dict[str, Any]) -> dict[str, Any]:
    return {"blocked": bool(details.get("blocked", False))} if "blocked" in details else {}


@dataclass
class VisualObservationAuditResult:
    events: list[dict[str, Any]]


class VisualObservationAuditService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_audit(self, limit: int = 50) -> VisualObservationAuditResult:
        return VisualObservationAuditResult(events=[
            {
                "event_type": row.event_type,
                "observation_id": row.observation_id,
                "visual_session_id": row.visual_session_id,
                "status": row.status,
                "actor": row.actor,
                "details": _safe_audit_details(json.loads(row.details_json)),
                "created_at": row.created_at,
            }
            for row in list_visual_observation_audit_events(self.session, limit=limit)
        ])
