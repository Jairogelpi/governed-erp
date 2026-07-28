"""Sprint 83 - table/form extraction from sanitized visual artifacts."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from erpguard.db.repositories import (
    create_visual_table_form_extraction,
    create_visual_table_form_extraction_audit_event,
    get_visual_observation_snapshot_by_id,
    get_visual_table_form_extraction_by_id,
    get_visual_workflow_trace_by_id,
    list_visual_table_form_extraction_audit_events,
    list_visual_table_form_extractions,
)
from erpguard.product.visual_observation_snapshot import DANGEROUS_LABELS

SECRET_MARKERS = {"password", "api_key", "token", "secret", "authorization", "bearer", "credential"}
VALUE_KEYS = {"value", "raw_value", "input_value", "current_value"}


@dataclass
class VisualTableFormExtractionInput:
    observation_id: str
    created_by: str = "operator_1"
    workflow_trace_id: str = ""
    extraction_goal: str = ""


@dataclass
class VisualTableFormExtraction:
    extraction_id: str
    visual_session_id: str
    observation_id: str
    workflow_trace_id: str
    created_by: str
    status: str
    extraction_goal: str
    table_structures: list[dict[str, Any]]
    form_structures: list[dict[str, Any]]
    button_structures: list[dict[str, Any]]
    field_candidates: list[dict[str, Any]]
    business_surface_hints: list[dict[str, Any]]
    redaction_summary: dict[str, Any]
    safety_summary: dict[str, Any]
    blocking_reasons: list[str] = field(default_factory=list)


class VisualTableFormExtractionService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_extraction(self, input: VisualTableFormExtractionInput) -> VisualTableFormExtraction:
        extraction_id = f"vextract_{uuid.uuid4().hex[:12]}"
        observation = get_visual_observation_snapshot_by_id(self.session, input.observation_id)
        visual_session_id = getattr(observation, "visual_session_id", "")
        self._audit(extraction_id, visual_session_id, input.observation_id, "visual_table_form_extraction_requested", "requested", input.created_by, {})
        reason = self._blocking_reason(input, observation)
        redacted: list[str] = []
        extraction_goal = _sanitize_text(input.extraction_goal, "extraction_goal", redacted)

        structures: dict[str, list] = {
            "tables": [],
            "forms": [],
            "buttons": [],
            "fields": [],
            "hints": [],
        }
        if reason is None:
            credential_reason = self._credential_value_reason(observation)
            if credential_reason:
                reason = credential_reason
            else:
                structures = _derive_structures(observation, redacted)

        status = "blocked" if reason else "created"
        row = create_visual_table_form_extraction(
            self.session,
            extraction_id=extraction_id,
            visual_session_id=visual_session_id,
            observation_id=input.observation_id,
            workflow_trace_id=input.workflow_trace_id,
            created_by=input.created_by,
            status=status,
            extraction_goal="" if reason else extraction_goal,
            table_structures_json=json.dumps([] if reason else structures["tables"], sort_keys=True),
            form_structures_json=json.dumps([] if reason else structures["forms"], sort_keys=True),
            button_structures_json=json.dumps([] if reason else structures["buttons"], sort_keys=True),
            field_candidates_json=json.dumps([] if reason else structures["fields"], sort_keys=True),
            business_surface_hints_json=json.dumps([] if reason else structures["hints"], sort_keys=True),
            redaction_summary_json=json.dumps({"redacted_fields": sorted(set(redacted)), "redaction_performed": bool(redacted)}, sort_keys=True),
            safety_summary_json=json.dumps(_safety_summary(), sort_keys=True),
            blocking_reasons_json=json.dumps([reason] if reason else []),
        )
        self._audit(
            extraction_id,
            visual_session_id,
            input.observation_id,
            "visual_table_form_extraction_blocked" if reason else "visual_table_form_extraction_created",
            status,
            input.created_by,
            {"blocked": bool(reason)},
        )
        return self._row_to_result(row)

    def get_extraction(self, extraction_id: str) -> dict[str, Any] | None:
        row = get_visual_table_form_extraction_by_id(self.session, extraction_id)
        if row is None:
            return None
        self._audit(row.extraction_id, row.visual_session_id, row.observation_id, "visual_table_form_extraction_retrieved", row.status, row.created_by, {})
        return self._row_to_dict(row)

    def list_extractions(self, limit: int = 50) -> list[dict[str, Any]]:
        return [self._row_to_dict(row) for row in list_visual_table_form_extractions(self.session, limit=limit)]

    def _blocking_reason(self, input: VisualTableFormExtractionInput, observation: Any | None) -> str | None:
        if observation is None:
            return "observation_not_found"
        if observation.status != "created":
            return "observation_not_created"
        if input.workflow_trace_id:
            trace = get_visual_workflow_trace_by_id(self.session, input.workflow_trace_id)
            if trace is None:
                return "workflow_trace_not_found"
            if trace.status != "created":
                return "workflow_trace_not_created"
            if trace.visual_session_id != observation.visual_session_id:
                return "workflow_trace_session_mismatch"
        if _contains_forbidden_marker(input.extraction_goal):
            return None
        return None

    def _credential_value_reason(self, observation: Any) -> str | None:
        for form in _json_list(observation.detected_forms_json):
            for form_field in _form_fields(form):
                value_keys = VALUE_KEYS.intersection(form_field.keys())
                if value_keys and (
                    _is_credential_field(form_field)
                    or any(form_field.get(key) == "<redacted>" for key in value_keys)
                ):
                    return "credential_value_detected"
        return None

    def _audit(self, extraction_id: str, visual_session_id: str, observation_id: str, event_type: str, status: str, actor: str, details: dict[str, Any]) -> None:
        create_visual_table_form_extraction_audit_event(
            self.session,
            extraction_id=extraction_id,
            visual_session_id=visual_session_id,
            observation_id=observation_id,
            event_type=event_type,
            status=status,
            actor=actor,
            details_json=json.dumps(_safe_details(details), sort_keys=True),
        )

    def _row_to_result(self, row: Any) -> VisualTableFormExtraction:
        return VisualTableFormExtraction(**self._row_to_dict(row))

    def _row_to_dict(self, row: Any) -> dict[str, Any]:
        return {
            "extraction_id": row.extraction_id,
            "visual_session_id": row.visual_session_id,
            "observation_id": row.observation_id,
            "workflow_trace_id": row.workflow_trace_id,
            "created_by": row.created_by,
            "status": row.status,
            "extraction_goal": row.extraction_goal,
            "table_structures": json.loads(row.table_structures_json),
            "form_structures": json.loads(row.form_structures_json),
            "button_structures": json.loads(row.button_structures_json),
            "field_candidates": json.loads(row.field_candidates_json),
            "business_surface_hints": json.loads(row.business_surface_hints_json),
            "redaction_summary": json.loads(row.redaction_summary_json),
            "safety_summary": json.loads(row.safety_summary_json),
            "blocking_reasons": json.loads(row.blocking_reasons_json),
        }


def _derive_structures(observation: Any, redacted: list[str]) -> dict[str, list[dict[str, Any]]]:
    tables = []
    forms = []
    buttons = []
    fields = []
    hints: dict[str, dict[str, Any]] = {}
    for index, table in enumerate(_json_list(observation.detected_tables_json)):
        columns = [_sanitize_text(str(column), f"tables[{index}].columns[]", redacted) for column in table.get("columns", [])]
        likely, confidence = _infer_object_type(columns)
        structure = {
            "table_id": f"table_{index}",
            "label": _sanitize_text(str(table.get("label", "")), f"tables[{index}].label", redacted),
            "columns": columns,
            "row_count": int(table.get("row_count", 0) or 0),
            "likely_object_type": likely,
            "confidence": confidence,
            "source": "visual_observation_snapshot",
        }
        tables.append(structure)
        if likely:
            hints[likely] = {"object_type": likely, "source": "table_columns", "confidence": confidence}
    for index, form in enumerate(_json_list(observation.detected_forms_json)):
        form_fields = []
        for field_index, form_field in enumerate(_form_fields(form)):
            candidate = _field_metadata(form_field, f"forms[{index}].fields[{field_index}]", redacted)
            form_fields.append(candidate)
            fields.append(candidate)
        labels = [field.get("field_label", "") for field in form_fields]
        likely, confidence = _infer_object_type(labels)
        forms.append({
            "form_id": f"form_{index}",
            "label": _sanitize_text(str(form.get("label", "")), f"forms[{index}].label", redacted),
            "field_count": int(form.get("field_count", len(form_fields)) or 0),
            "fields": form_fields,
            "likely_object_type": likely,
            "confidence": confidence,
            "source": "visual_observation_snapshot",
        })
        if likely:
            hints[likely] = {"object_type": likely, "source": "form_fields", "confidence": confidence}
    dangerous_labels = {str(item.get("label", "")).lower() for item in _json_list(observation.dangerous_action_candidates_json)}
    for button in _json_list(observation.detected_buttons_json):
        label = _sanitize_text(str(button.get("label", "")), "buttons.label", redacted)
        is_dangerous = label.lower() in DANGEROUS_LABELS or label.lower() in dangerous_labels
        buttons.append({
            "button_label": label,
            "risk_level": "high" if is_dangerous else "low",
            "is_dangerous": is_dangerous,
            "requires_human_approval": is_dangerous,
            "auto_execute_allowed": False,
        })
    return {
        "tables": tables,
        "forms": forms,
        "buttons": buttons,
        "fields": fields,
        "hints": list(hints.values()),
    }


def _field_metadata(field: dict[str, Any], path: str, redacted: list[str]) -> dict[str, Any]:
    has_value = any(key in field for key in VALUE_KEYS)
    return {
        "field_label": _sanitize_text(str(field.get("field_label", field.get("label", ""))), f"{path}.field_label", redacted),
        "field_type": _sanitize_text(str(field.get("field_type", field.get("type", ""))), f"{path}.field_type", redacted),
        "required_hint": bool(field.get("required_hint", field.get("required", False))),
        "value_present": bool(field.get("value_present", has_value)),
        "value_redacted": has_value or bool(field.get("value_present", False)),
    }


def _form_fields(form: dict[str, Any]) -> list[dict[str, Any]]:
    fields = form.get("fields", [])
    return fields if isinstance(fields, list) else []


def _infer_object_type(labels: list[str]) -> tuple[str | None, float]:
    normalized = {label.lower() for label in labels}
    checks = [
        ("sale_order", {"referencia", "pedido", "cliente", "estado", "total"}),
        ("invoice", {"factura", "cliente", "total", "pendiente", "fecha"}),
        ("stock_item", {"producto", "cantidad", "ubicación", "ubicacion", "reservado"}),
        ("manufacturing_order", {"producto", "estado", "cantidad", "lista de materiales"}),
        ("partner", {"nombre", "email", "teléfono", "telefono", "empresa"}),
        ("product", {"producto", "código", "codigo", "precio", "disponible"}),
    ]
    best_type: str | None = None
    best_score = 0.0
    for object_type, expected in checks:
        score = len(normalized.intersection(expected)) / len(expected)
        if score > best_score:
            best_type = object_type
            best_score = score
    if best_score >= 0.5:
        return best_type, round(best_score, 2)
    return None, 0.0


def _json_list(raw: str) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return []
    return parsed if isinstance(parsed, list) else []


def _is_credential_field(field: dict[str, Any]) -> bool:
    label = str(field.get("field_label", field.get("label", ""))).lower()
    field_type = str(field.get("field_type", field.get("type", ""))).lower()
    return any(marker in label or marker in field_type for marker in SECRET_MARKERS)


def _sanitize_text(value: str, path: str, redacted: list[str]) -> str:
    if _contains_forbidden_marker(value):
        redacted.append(path)
        return "<redacted>"
    return value


def _contains_forbidden_marker(value: str) -> bool:
    lower = value.lower()
    return any(marker in lower for marker in SECRET_MARKERS)


def _safety_summary() -> dict[str, Any]:
    return {
        "extraction_only": True,
        "browser_launched": False,
        "browser_control_performed": False,
        "automatic_clicks_performed": False,
        "form_submission_performed": False,
        "action_execution_performed": False,
        "real_dom_inspection_performed": False,
        "real_screen_capture_performed": False,
        "workflow_recording_performed": False,
        "credentials_exposed": False,
        "raw_secret_accessed": False,
        "mcp_execution_performed": False,
        "scheduler_used": False,
        "erp_write_performed": False,
    }


def _safe_details(details: dict[str, Any]) -> dict[str, Any]:
    return {"blocked": bool(details.get("blocked", False))} if "blocked" in details else {}


@dataclass
class VisualTableFormExtractionAuditResult:
    events: list[dict[str, Any]]


class VisualTableFormExtractionAuditService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_audit(self, limit: int = 50) -> VisualTableFormExtractionAuditResult:
        return VisualTableFormExtractionAuditResult(events=[
            {
                "event_type": row.event_type,
                "extraction_id": row.extraction_id,
                "visual_session_id": row.visual_session_id,
                "observation_id": row.observation_id,
                "status": row.status,
                "actor": row.actor,
                "details": _safe_details(json.loads(row.details_json)),
                "created_at": row.created_at,
            }
            for row in list_visual_table_form_extraction_audit_events(self.session, limit=limit)
        ])
