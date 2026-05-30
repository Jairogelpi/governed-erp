"""Sprint 76/77 - controlled Odoo business object read mapping.

Reads are available only through an explicitly injected/read-only client and
only for allowlisted objects, lookup keys, and source fields. No arbitrary
models, domains, fields, writes, schema inspection, permission inspection, raw
secret exposure, browser automation, MCP, or scheduler behavior is introduced.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

from sqlalchemy.orm import Session

from erpguard.db.repositories import (
    create_odoo_read_mapping,
    create_odoo_read_mapping_audit_event,
    get_credential_vault_entry_by_ref,
    get_odoo_connection_test_by_id,
    get_odoo_read_mapping_by_id,
    list_odoo_read_mapping_audit_events,
    list_odoo_read_mappings,
)


ALLOWED_OBJECT_TYPES = {
    "partner",
    "product",
    "sale_order",
    "invoice",
    "stock_item",
    "manufacturing_order",
}
BLOCKED_OBJECT_TYPES = {
    "stock_move",
    "journal_entry",
    "payment",
    "purchase_order",
    "custom_object",
}
LOOKUP_ALLOWLISTS = {
    "partner": {"id", "email", "name", "external_reference"},
    "product": {"id", "default_code", "name", "external_reference"},
    "sale_order": {"id", "name", "reference", "external_reference"},
    "invoice": {"id", "name", "reference", "external_reference"},
    "stock_item": {"id", "product_id", "product_code", "external_reference"},
    "manufacturing_order": {"id", "name", "reference", "external_reference"},
}
FIELD_ALLOWLISTS = {
    "partner": {
        "id",
        "display_name",
        "name",
        "email",
        "phone",
        "company_name",
        "country",
        "country_id",
        "external_reference",
    },
    "product": {
        "id",
        "display_name",
        "name",
        "default_code",
        "sale_ok",
        "purchase_ok",
        "external_reference",
    },
    "sale_order": {
        "id",
        "display_name",
        "name",
        "partner_id",
        "state",
        "amount_total",
        "currency_id",
        "date_order",
        "order_line",
        "external_reference",
    },
    "invoice": {
        "id",
        "display_name",
        "name",
        "ref",
        "partner_id",
        "state",
        "move_type",
        "amount_total",
        "amount_residual",
        "currency_id",
        "invoice_date",
        "external_reference",
    },
    "stock_item": {
        "id",
        "display_name",
        "product_id",
        "location_id",
        "quantity",
        "reserved_quantity",
        "external_reference",
    },
    "manufacturing_order": {
        "id",
        "display_name",
        "name",
        "product_id",
        "state",
        "product_qty",
        "qty_produced",
        "bom_id",
        "external_reference",
    },
}


class OdooReadMappingStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class OdooReadMappingInput:
    connection_test_id: str
    requested_by: str = "operator_1"
    object_type: str = "sale_order"
    lookup: dict[str, Any] | None = None
    allow_business_read: bool = False


@dataclass
class OdooReadMappingResult:
    read_mapping_id: str
    connection_test_id: str
    adapter_session_id: str
    activation_id: str
    setup_session_id: str
    credential_ref: str
    object_type: str
    status: str
    allow_business_read: bool
    business_data_read: bool
    canonical_object: dict[str, Any]
    source_snapshot_redacted: dict[str, Any]
    field_allowlist_used: list[str]
    redacted_fields: list[str]
    external_http_performed: bool
    odoo_rpc_performed: bool
    odoo_read_performed: bool
    odoo_write_performed: bool = False
    schema_inspection_performed: bool = False
    permission_inspection_performed: bool = False
    credentials_exposed: bool = False
    raw_secret_accessed: bool = False
    blocking_reasons: list[str] | None = None


class OdooReadClient(Protocol):
    def read_allowed_object(
        self, *, object_type: str, lookup: dict[str, Any], field_allowlist: list[str]
    ) -> dict[str, Any]:
        ...


class NoopOdooReadClient:
    def read_allowed_object(
        self, *, object_type: str, lookup: dict[str, Any], field_allowlist: list[str]
    ) -> dict[str, Any]:
        raise RuntimeError("read_client_not_configured")


class OdooReadMappingService:
    def __init__(self, session: Session, *, read_client: OdooReadClient | None = None) -> None:
        self.session = session
        self.read_client = read_client

    def run_mapping(self, input: OdooReadMappingInput) -> OdooReadMappingResult:
        read_mapping_id = f"odoo_map_{uuid.uuid4().hex[:12]}"
        self._audit_requested(read_mapping_id, input)
        connection = get_odoo_connection_test_by_id(self.session, input.connection_test_id)
        reason = self._blocking_reason(input, connection)
        if reason is not None:
            row = self._persist(
                read_mapping_id=read_mapping_id,
                input=input,
                connection=connection,
                status=OdooReadMappingStatus.BLOCKED.value,
                business_data_read=False,
                canonical_object={},
                source_snapshot_redacted={},
                field_allowlist_used=[],
                redacted_fields=[],
                external_http_performed=False,
                odoo_rpc_performed=False,
                odoo_read_performed=False,
                blocking_reasons=[reason],
            )
            self._audit(row, event_type="odoo_read_mapping_blocked", actor=input.requested_by)
            return self._row_to_result(row)

        field_allowlist = sorted(FIELD_ALLOWLISTS[input.object_type])
        client = self.read_client or self._default_read_client()
        try:
            source = client.read_allowed_object(
                object_type=input.object_type,
                lookup=input.lookup or {},
                field_allowlist=field_allowlist,
            )
        except Exception:
            row = self._persist(
                read_mapping_id=read_mapping_id,
                input=input,
                connection=connection,
                status=OdooReadMappingStatus.FAILED.value,
                business_data_read=False,
                canonical_object={},
                source_snapshot_redacted={},
                field_allowlist_used=field_allowlist,
                redacted_fields=[],
                external_http_performed=True,
                odoo_rpc_performed=True,
                odoo_read_performed=True,
                blocking_reasons=["read_client_failed"],
            )
            self._audit(row, event_type="odoo_read_mapping_failed", actor=input.requested_by)
            return self._row_to_result(row)

        source_snapshot, redacted_fields = _redact_source_snapshot(source, field_allowlist)
        canonical = _canonicalize(input.object_type, source_snapshot)
        if not canonical.get("external_id") or not canonical.get("display_name"):
            row = self._persist(
                read_mapping_id=read_mapping_id,
                input=input,
                connection=connection,
                status=OdooReadMappingStatus.FAILED.value,
                business_data_read=True,
                canonical_object={},
                source_snapshot_redacted=source_snapshot,
                field_allowlist_used=field_allowlist,
                redacted_fields=redacted_fields,
                external_http_performed=True,
                odoo_rpc_performed=True,
                odoo_read_performed=True,
                blocking_reasons=["canonical_identity_missing"],
            )
            self._audit(row, event_type="odoo_read_mapping_failed", actor=input.requested_by)
            return self._row_to_result(row)

        row = self._persist(
            read_mapping_id=read_mapping_id,
            input=input,
            connection=connection,
            status=OdooReadMappingStatus.PASSED.value,
            business_data_read=True,
            canonical_object=canonical,
            source_snapshot_redacted=source_snapshot,
            field_allowlist_used=field_allowlist,
            redacted_fields=redacted_fields,
            external_http_performed=True,
            odoo_rpc_performed=True,
            odoo_read_performed=True,
            blocking_reasons=[],
        )
        self._audit(row, event_type="odoo_read_mapping_passed", actor=input.requested_by)
        return self._row_to_result(row)

    def get_mapping(self, read_mapping_id: str) -> dict[str, Any] | None:
        row = get_odoo_read_mapping_by_id(self.session, read_mapping_id)
        if row is None:
            return None
        self._audit(row, event_type="odoo_read_mapping_retrieved", actor=row.requested_by)
        return self._row_to_dict(row)

    def list_mappings(self, limit: int = 50) -> list[dict[str, Any]]:
        return [self._row_to_dict(row) for row in list_odoo_read_mappings(self.session, limit=limit)]

    def _default_read_client(self) -> OdooReadClient:
        return NoopOdooReadClient()

    def _blocking_reason(self, input: OdooReadMappingInput, connection: Any | None) -> str | None:
        if connection is None:
            return "connection_test_not_found"
        if connection.status != "passed":
            return "connection_test_not_passed"
        if input.object_type not in ALLOWED_OBJECT_TYPES or input.object_type in BLOCKED_OBJECT_TYPES:
            return "object_type_not_allowed"
        if not input.allow_business_read:
            return "business_read_not_allowed"
        credential = get_credential_vault_entry_by_ref(self.session, connection.credential_ref)
        if credential is None:
            return "credential_not_found"
        if credential.status == "revoked":
            return "credential_revoked"
        if not input.lookup:
            return "lookup_missing"
        lookup_keys = set(input.lookup)
        if len(lookup_keys) != 1 or not lookup_keys.issubset(LOOKUP_ALLOWLISTS[input.object_type]):
            return "lookup_not_supported"
        return None

    def _persist(
        self,
        *,
        read_mapping_id: str,
        input: OdooReadMappingInput,
        connection: Any | None,
        status: str,
        business_data_read: bool,
        canonical_object: dict[str, Any],
        source_snapshot_redacted: dict[str, Any],
        field_allowlist_used: list[str],
        redacted_fields: list[str],
        external_http_performed: bool,
        odoo_rpc_performed: bool,
        odoo_read_performed: bool,
        blocking_reasons: list[str],
    ) -> Any:
        return create_odoo_read_mapping(
            self.session,
            read_mapping_id=read_mapping_id,
            connection_test_id=input.connection_test_id,
            adapter_session_id=getattr(connection, "adapter_session_id", ""),
            activation_id=getattr(connection, "activation_id", ""),
            setup_session_id=getattr(connection, "setup_session_id", ""),
            credential_ref=getattr(connection, "credential_ref", ""),
            object_type=input.object_type,
            status=status,
            allow_business_read=input.allow_business_read,
            business_data_read=business_data_read,
            canonical_object_json=json.dumps(canonical_object, sort_keys=True, default=str),
            source_snapshot_redacted_json=json.dumps(source_snapshot_redacted, sort_keys=True, default=str),
            field_allowlist_used_json=json.dumps(field_allowlist_used),
            redacted_fields_json=json.dumps(redacted_fields),
            external_http_performed=external_http_performed,
            odoo_rpc_performed=odoo_rpc_performed,
            odoo_read_performed=odoo_read_performed,
            requested_by=input.requested_by,
            blocking_reasons_json=json.dumps(blocking_reasons),
        )

    def _audit_requested(self, read_mapping_id: str, input: OdooReadMappingInput) -> None:
        create_odoo_read_mapping_audit_event(
            self.session,
            read_mapping_id=read_mapping_id,
            connection_test_id=input.connection_test_id,
            adapter_session_id="",
            activation_id="",
            setup_session_id="",
            credential_ref="",
            object_type=input.object_type,
            event_type="odoo_read_mapping_requested",
            status="requested",
            actor=input.requested_by,
            details_json=json.dumps(
                {
                    "allow_business_read": input.allow_business_read,
                    "lookup_keys": sorted((input.lookup or {}).keys()),
                },
                sort_keys=True,
            ),
        )

    def _audit(self, row: Any, *, event_type: str, actor: str) -> None:
        create_odoo_read_mapping_audit_event(
            self.session,
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
                    "redacted_fields": json.loads(row.redacted_fields_json),
                },
                sort_keys=True,
            ),
        )

    def _row_to_result(self, row: Any) -> OdooReadMappingResult:
        return OdooReadMappingResult(**self._row_to_dict(row))

    def _row_to_dict(self, row: Any) -> dict[str, Any]:
        return {
            "read_mapping_id": row.read_mapping_id,
            "connection_test_id": row.connection_test_id,
            "adapter_session_id": row.adapter_session_id,
            "activation_id": row.activation_id,
            "setup_session_id": row.setup_session_id,
            "credential_ref": row.credential_ref,
            "object_type": row.object_type,
            "status": row.status,
            "allow_business_read": row.allow_business_read,
            "business_data_read": row.business_data_read,
            "canonical_object": json.loads(row.canonical_object_json),
            "source_snapshot_redacted": json.loads(row.source_snapshot_redacted_json),
            "field_allowlist_used": json.loads(row.field_allowlist_used_json),
            "redacted_fields": json.loads(row.redacted_fields_json),
            "external_http_performed": row.external_http_performed,
            "odoo_rpc_performed": row.odoo_rpc_performed,
            "odoo_read_performed": row.odoo_read_performed,
            "odoo_write_performed": False,
            "schema_inspection_performed": False,
            "permission_inspection_performed": False,
            "credentials_exposed": False,
            "raw_secret_accessed": False,
            "blocking_reasons": json.loads(row.blocking_reasons_json),
        }


def _redact_source_snapshot(source: dict[str, Any], field_allowlist: list[str]) -> tuple[dict[str, Any], list[str]]:
    allowed = set(field_allowlist)
    snapshot: dict[str, Any] = {}
    redacted: list[str] = []
    for key, value in source.items():
        if key in allowed:
            snapshot[key] = value
        else:
            snapshot[key] = "<redacted>"
            redacted.append(key)
    return snapshot, sorted(redacted)


def _display_name(source: dict[str, Any]) -> str | None:
    return source.get("display_name") or source.get("name")


def _external_id(source: dict[str, Any]) -> str:
    value = source.get("external_reference") or source.get("id")
    return "" if value is None else str(value)


def _many2one_ref(value: Any) -> str | None:
    if isinstance(value, (list, tuple)) and value:
        return str(value[0])
    if value is None:
        return None
    return str(value)


def _canonicalize(object_type: str, source: dict[str, Any]) -> dict[str, Any]:
    if object_type == "partner":
        return {
            "object_type": "partner",
            "external_id": _external_id(source),
            "display_name": _display_name(source),
            "email": source.get("email"),
            "phone": source.get("phone"),
            "company_name": source.get("company_name"),
            "country": source.get("country") or _many2one_ref(source.get("country_id")),
            "source_adapter": "odoo",
            "source_model_hint": "res.partner",
        }
    if object_type == "product":
        return {
            "object_type": "product",
            "external_id": _external_id(source),
            "display_name": _display_name(source),
            "default_code": source.get("default_code"),
            "sale_ok": source.get("sale_ok"),
            "purchase_ok": source.get("purchase_ok"),
            "source_adapter": "odoo",
            "source_model_hint": "product.template/product.product",
        }
    if object_type == "sale_order":
        order_line = source.get("order_line")
        return {
            "object_type": "sale_order",
            "external_id": _external_id(source),
            "display_name": _display_name(source),
            "partner_ref": _many2one_ref(source.get("partner_id")),
            "state": source.get("state"),
            "amount_total": source.get("amount_total"),
            "currency": _many2one_ref(source.get("currency_id")),
            "order_date": source.get("date_order"),
            "line_count": len(order_line) if isinstance(order_line, list) else None,
            "source_adapter": "odoo",
            "source_model_hint": "sale.order",
        }
    if object_type == "invoice":
        return {
            "object_type": "invoice",
            "external_id": _external_id(source),
            "display_name": _display_name(source),
            "partner_ref": _many2one_ref(source.get("partner_id")),
            "state": source.get("state"),
            "move_type": source.get("move_type"),
            "amount_total": source.get("amount_total"),
            "amount_residual": source.get("amount_residual"),
            "currency": _many2one_ref(source.get("currency_id")),
            "invoice_date": source.get("invoice_date"),
            "source_adapter": "odoo",
            "source_model_hint": "account.move",
        }
    if object_type == "stock_item":
        return {
            "object_type": "stock_item",
            "external_id": _external_id(source),
            "display_name": _display_name(source),
            "product_ref": _many2one_ref(source.get("product_id")),
            "location_ref": _many2one_ref(source.get("location_id")),
            "quantity": source.get("quantity"),
            "reserved_quantity": source.get("reserved_quantity"),
            "source_adapter": "odoo",
            "source_model_hint": "stock.quant",
        }
    return {
        "object_type": "manufacturing_order",
        "external_id": _external_id(source),
        "display_name": _display_name(source),
        "product_ref": _many2one_ref(source.get("product_id")),
        "state": source.get("state"),
        "product_qty": source.get("product_qty"),
        "qty_produced": source.get("qty_produced"),
        "bom_ref": _many2one_ref(source.get("bom_id")),
        "source_adapter": "odoo",
        "source_model_hint": "mrp.production",
    }


@dataclass
class OdooReadMappingAuditResult:
    events: list[dict[str, Any]]


class OdooReadMappingAuditService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_audit(self, limit: int = 50) -> OdooReadMappingAuditResult:
        return OdooReadMappingAuditResult(
            events=[
                {
                    "event_type": row.event_type,
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
                for row in list_odoo_read_mapping_audit_events(self.session, limit=limit)
            ]
        )
