"""Sprint 78 - evidence packs for existing Odoo read mappings.

Creates evidence only from persisted read-mapping snapshots. It never calls the
Odoo read client, performs a new ERP read, performs HTTP/RPC, writes, schema or
permission inspection, or exposes raw secrets.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from erpguard.db.repositories import (
    create_odoo_read_evidence_audit_event,
    create_odoo_read_evidence_pack,
    get_odoo_read_evidence_pack_by_id,
    get_odoo_read_mapping_by_id,
    list_odoo_read_evidence_audit_events,
    list_odoo_read_evidence_packs,
)


RAW_SECRET_MARKERS = {
    "password",
    "api_key",
    "token",
    "secret",
    "authorization",
    "credential",
}
SUPPORTED_OBJECTS = {
    "partner",
    "product",
    "sale_order",
    "invoice",
    "stock_item",
    "manufacturing_order",
}


@dataclass
class OdooReadEvidencePackInput:
    read_mapping_id: str
    created_by: str = "operator_1"


@dataclass
class OdooReadEvidencePackResult:
    evidence_pack_id: str
    read_mapping_id: str
    connection_test_id: str
    adapter_session_id: str
    activation_id: str
    setup_session_id: str
    credential_ref: str
    object_type: str
    status: str
    canonical_object_snapshot: dict[str, Any]
    source_snapshot_redacted: dict[str, Any]
    field_allowlist_used: list[str]
    redacted_fields: list[str]
    safety_summary: dict[str, Any]
    chain_summary: dict[str, Any]
    created_by: str
    blocking_reasons: list[str]
    raw_secret_accessed: bool = False


class OdooReadEvidencePackService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_pack(self, input: OdooReadEvidencePackInput) -> OdooReadEvidencePackResult:
        evidence_pack_id = f"odoo_ev_{uuid.uuid4().hex[:12]}"
        self._audit_requested(evidence_pack_id, input)
        mapping = get_odoo_read_mapping_by_id(self.session, input.read_mapping_id)
        reason = self._blocking_reason(mapping)
        if reason is not None:
            row = self._persist(
                evidence_pack_id=evidence_pack_id,
                input=input,
                mapping=mapping,
                status="blocked",
                canonical_object_snapshot={},
                source_snapshot_redacted={},
                field_allowlist_used=[],
                redacted_fields=[],
                safety_summary=_safety_summary(mapping),
                chain_summary=_chain_summary(mapping),
                blocking_reasons=[reason],
            )
            self._audit(row, event_type="odoo_read_evidence_pack_blocked", actor=input.created_by)
            return self._row_to_result(row)

        canonical = json.loads(mapping.canonical_object_json)
        source = json.loads(mapping.source_snapshot_redacted_json)
        fields = json.loads(mapping.field_allowlist_used_json)
        redacted = json.loads(mapping.redacted_fields_json)
        row = self._persist(
            evidence_pack_id=evidence_pack_id,
            input=input,
            mapping=mapping,
            status="created",
            canonical_object_snapshot=canonical,
            source_snapshot_redacted=source,
            field_allowlist_used=fields,
            redacted_fields=redacted,
            safety_summary=_safety_summary(mapping),
            chain_summary=_chain_summary(mapping),
            blocking_reasons=[],
        )
        self._audit(row, event_type="odoo_read_evidence_pack_created", actor=input.created_by)
        return self._row_to_result(row)

    def get_pack(self, evidence_pack_id: str) -> dict[str, Any] | None:
        row = get_odoo_read_evidence_pack_by_id(self.session, evidence_pack_id)
        if row is None:
            return None
        self._audit(row, event_type="odoo_read_evidence_pack_retrieved", actor=row.created_by)
        return self._row_to_dict(row)

    def list_packs(self, limit: int = 50) -> list[dict[str, Any]]:
        return [self._row_to_dict(row) for row in list_odoo_read_evidence_packs(self.session, limit=limit)]

    def _blocking_reason(self, mapping: Any | None) -> str | None:
        if mapping is None:
            return "read_mapping_not_found"
        if mapping.status != "passed":
            return "read_mapping_not_passed"
        if mapping.object_type not in SUPPORTED_OBJECTS:
            return "read_mapping_not_passed"
        canonical = json.loads(mapping.canonical_object_json)
        source = json.loads(mapping.source_snapshot_redacted_json)
        if not canonical:
            return "canonical_object_missing"
        if not source:
            return "source_snapshot_redaction_missing"
        if _raw_secret_marker_detected(canonical) or _raw_secret_marker_detected(source):
            return "raw_secret_marker_detected"
        return None

    def _persist(
        self,
        *,
        evidence_pack_id: str,
        input: OdooReadEvidencePackInput,
        mapping: Any | None,
        status: str,
        canonical_object_snapshot: dict[str, Any],
        source_snapshot_redacted: dict[str, Any],
        field_allowlist_used: list[str],
        redacted_fields: list[str],
        safety_summary: dict[str, Any],
        chain_summary: dict[str, Any],
        blocking_reasons: list[str],
    ) -> Any:
        return create_odoo_read_evidence_pack(
            self.session,
            evidence_pack_id=evidence_pack_id,
            read_mapping_id=input.read_mapping_id,
            connection_test_id=getattr(mapping, "connection_test_id", ""),
            adapter_session_id=getattr(mapping, "adapter_session_id", ""),
            activation_id=getattr(mapping, "activation_id", ""),
            setup_session_id=getattr(mapping, "setup_session_id", ""),
            credential_ref=getattr(mapping, "credential_ref", ""),
            object_type=getattr(mapping, "object_type", ""),
            status=status,
            canonical_object_snapshot_json=json.dumps(canonical_object_snapshot, sort_keys=True, default=str),
            source_snapshot_redacted_json=json.dumps(source_snapshot_redacted, sort_keys=True, default=str),
            field_allowlist_used_json=json.dumps(field_allowlist_used),
            redacted_fields_json=json.dumps(redacted_fields),
            safety_summary_json=json.dumps(safety_summary, sort_keys=True),
            chain_summary_json=json.dumps(chain_summary, sort_keys=True),
            created_by=input.created_by,
            blocking_reasons_json=json.dumps(blocking_reasons),
        )

    def _audit_requested(self, evidence_pack_id: str, input: OdooReadEvidencePackInput) -> None:
        create_odoo_read_evidence_audit_event(
            self.session,
            evidence_pack_id=evidence_pack_id,
            read_mapping_id=input.read_mapping_id,
            connection_test_id="",
            adapter_session_id="",
            activation_id="",
            setup_session_id="",
            credential_ref="",
            object_type="",
            event_type="odoo_read_evidence_pack_requested",
            status="requested",
            actor=input.created_by,
            details_json="{}",
        )

    def _audit(self, row: Any, *, event_type: str, actor: str) -> None:
        create_odoo_read_evidence_audit_event(
            self.session,
            evidence_pack_id=row.evidence_pack_id,
            read_mapping_id=row.read_mapping_id,
            connection_test_id=row.connection_test_id,
            adapter_session_id=row.adapter_session_id,
            activation_id=row.activation_id,
            setup_session_id=row.setup_session_id,
            credential_ref=row.credential_ref,
            object_type=row.object_type,
            event_type=event_type,
            status=row.status,
            actor=actor,
            details_json=json.dumps(
                {
                    "blocking_reasons": json.loads(row.blocking_reasons_json),
                    "evidence_only": True,
                },
                sort_keys=True,
            ),
        )

    def _row_to_result(self, row: Any) -> OdooReadEvidencePackResult:
        return OdooReadEvidencePackResult(**self._row_to_dict(row))

    def _row_to_dict(self, row: Any) -> dict[str, Any]:
        return {
            "evidence_pack_id": row.evidence_pack_id,
            "read_mapping_id": row.read_mapping_id,
            "connection_test_id": row.connection_test_id,
            "adapter_session_id": row.adapter_session_id,
            "activation_id": row.activation_id,
            "setup_session_id": row.setup_session_id,
            "credential_ref": row.credential_ref,
            "object_type": row.object_type,
            "status": row.status,
            "canonical_object_snapshot": json.loads(row.canonical_object_snapshot_json),
            "source_snapshot_redacted": json.loads(row.source_snapshot_redacted_json),
            "field_allowlist_used": json.loads(row.field_allowlist_used_json),
            "redacted_fields": json.loads(row.redacted_fields_json),
            "safety_summary": json.loads(row.safety_summary_json),
            "chain_summary": json.loads(row.chain_summary_json),
            "created_by": row.created_by,
            "blocking_reasons": json.loads(row.blocking_reasons_json),
            "raw_secret_accessed": False,
        }


def _safety_summary(mapping: Any | None) -> dict[str, Any]:
    return {
        "business_data_read": bool(getattr(mapping, "business_data_read", False)),
        "odoo_write_performed": False,
        "schema_inspection_performed": False,
        "permission_inspection_performed": False,
        "credentials_exposed": False,
        "raw_secret_accessed": False,
        "evidence_only": True,
        "new_erp_read_performed": False,
        "new_external_http_performed": False,
        "read_client_called": False,
    }


def _chain_summary(mapping: Any | None) -> dict[str, Any]:
    return {
        "setup_session_id": getattr(mapping, "setup_session_id", ""),
        "credential_ref": getattr(mapping, "credential_ref", ""),
        "activation_id": getattr(mapping, "activation_id", ""),
        "adapter_session_id": getattr(mapping, "adapter_session_id", ""),
        "connection_test_id": getattr(mapping, "connection_test_id", ""),
        "read_mapping_id": getattr(mapping, "read_mapping_id", ""),
        "object_type": getattr(mapping, "object_type", ""),
        "source_adapter": "odoo",
        "evidence_source": "odoo_read_mapping",
    }


def _raw_secret_marker_detected(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            key_lower = str(key).lower()
            if any(marker in key_lower for marker in RAW_SECRET_MARKERS) and item != "<redacted>":
                return True
            if _raw_secret_marker_detected(item):
                return True
    elif isinstance(value, list):
        return any(_raw_secret_marker_detected(item) for item in value)
    elif isinstance(value, str):
        lower = value.lower()
        return any(marker in lower for marker in RAW_SECRET_MARKERS)
    return False


@dataclass
class OdooReadEvidenceAuditResult:
    events: list[dict[str, Any]]


class OdooReadEvidenceAuditService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_audit(self, limit: int = 50) -> OdooReadEvidenceAuditResult:
        return OdooReadEvidenceAuditResult(
            events=[
                {
                    "event_type": row.event_type,
                    "evidence_pack_id": row.evidence_pack_id,
                    "read_mapping_id": row.read_mapping_id,
                    "connection_test_id": row.connection_test_id,
                    "adapter_session_id": row.adapter_session_id,
                    "activation_id": row.activation_id,
                    "setup_session_id": row.setup_session_id,
                    "credential_ref": row.credential_ref,
                    "object_type": row.object_type,
                    "status": row.status,
                    "actor": row.actor,
                    "details": json.loads(row.details_json),
                    "created_at": row.created_at,
                }
                for row in list_odoo_read_evidence_audit_events(self.session, limit=limit)
            ]
        )
