"""Sprint 74 - Odoo read-only adapter shell.

Prepares an Odoo adapter session from an internal active_read_only artifact.
This shell does not perform HTTP, XML-RPC, JSON-RPC, login, schema inspection,
permission inspection, Odoo reads, Odoo writes, or raw secret access.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from sqlalchemy.orm import Session

from erpguard.db.repositories import (
    create_odoo_read_only_adapter_audit_event,
    create_odoo_read_only_adapter_session,
    get_credential_vault_entry_by_ref,
    get_odoo_read_only_adapter_session_by_id,
    get_read_only_connector_activation_by_id,
    list_odoo_read_only_adapter_sessions,
)


class OdooReadOnlyAdapterStatus(StrEnum):
    PREPARED = "prepared"
    BLOCKED = "blocked"


@dataclass
class OdooReadOnlyAdapterConfig:
    adapter_type: str = "odoo"
    mode: str = "read_only"


@dataclass
class OdooReadOnlyConnectionIntent:
    activation_id: str
    created_by: str = "operator_1"


@dataclass
class OdooReadOnlyAdapter:
    adapter_session_id: str
    activation_id: str
    capability_set_id: str
    setup_session_id: str
    credential_ref: str
    adapter_id: str
    adapter_type: str
    mode: str
    status: str
    created_by: str
    blocking_reasons: list[str]
    can_connect_later: bool
    will_connect_now: bool = False
    external_http_performed: bool = False
    login_attempted: bool = False
    odoo_rpc_performed: bool = False
    odoo_read_performed: bool = False
    odoo_write_performed: bool = False
    schema_inspection_performed: bool = False
    permission_inspection_performed: bool = False
    credentials_exposed: bool = False
    raw_secret_accessed: bool = False


def _blocked(intent: OdooReadOnlyConnectionIntent, reason: str, activation: Any | None = None) -> OdooReadOnlyAdapter:
    return OdooReadOnlyAdapter(
        adapter_session_id="",
        activation_id=intent.activation_id,
        capability_set_id=getattr(activation, "capability_set_id", ""),
        setup_session_id=getattr(activation, "setup_session_id", ""),
        credential_ref=getattr(activation, "credential_ref", ""),
        adapter_id=getattr(activation, "adapter_id", ""),
        adapter_type=getattr(activation, "adapter_type", "odoo"),
        mode=getattr(activation, "mode", "read_only"),
        status=OdooReadOnlyAdapterStatus.BLOCKED.value,
        created_by=intent.created_by,
        blocking_reasons=[reason],
        can_connect_later=False,
    )


class OdooReadOnlyAdapterService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def prepare_session(self, intent: OdooReadOnlyConnectionIntent) -> OdooReadOnlyAdapter:
        create_odoo_read_only_adapter_audit_event(
            self.session,
            adapter_session_id="",
            activation_id=intent.activation_id,
            capability_set_id="",
            setup_session_id="",
            credential_ref="",
            event_type="odoo_read_only_adapter_session_requested",
            status="requested",
            actor=intent.created_by,
            details_json="{}",
        )
        activation = get_read_only_connector_activation_by_id(
            self.session, intent.activation_id
        )
        reason = None
        if activation is None:
            reason = "activation_not_found"
        elif activation.status != "active_read_only":
            reason = "activation_not_active_read_only"
        elif activation.adapter_type != "odoo":
            reason = "adapter_type_not_odoo"
        elif activation.mode != "read_only":
            reason = "mode_not_read_only"
        elif not activation.credential_ref:
            reason = "credential_ref_required"
        else:
            credential = get_credential_vault_entry_by_ref(
                self.session, activation.credential_ref
            )
            if credential is None:
                reason = "credential_not_found"
            elif credential.status == "revoked":
                reason = "credential_revoked"

        if reason is not None:
            result = _blocked(intent, reason, activation)
            create_odoo_read_only_adapter_audit_event(
                self.session,
                adapter_session_id="",
                activation_id=intent.activation_id,
                capability_set_id=result.capability_set_id,
                setup_session_id=result.setup_session_id,
                credential_ref=result.credential_ref,
                event_type="odoo_read_only_adapter_session_blocked",
                status="blocked",
                actor=intent.created_by,
                details_json=json.dumps({"blocking_reasons": [reason]}),
            )
            return result

        adapter_session_id = f"odoo_ro_{uuid.uuid4().hex[:12]}"
        row = create_odoo_read_only_adapter_session(
            self.session,
            adapter_session_id=adapter_session_id,
            activation_id=activation.activation_id,
            capability_set_id=activation.capability_set_id,
            setup_session_id=activation.setup_session_id,
            credential_ref=activation.credential_ref,
            adapter_id=activation.adapter_id,
            adapter_type="odoo",
            mode="read_only",
            status="prepared",
            created_by=intent.created_by,
            blocking_reasons_json="[]",
        )
        create_odoo_read_only_adapter_audit_event(
            self.session,
            adapter_session_id=row.adapter_session_id,
            activation_id=row.activation_id,
            capability_set_id=row.capability_set_id,
            setup_session_id=row.setup_session_id,
            credential_ref=row.credential_ref,
            event_type="odoo_read_only_adapter_session_created",
            status="prepared",
            actor=intent.created_by,
            details_json=json.dumps({"shell_only": True}),
        )
        return self._row_to_result(row)

    def get_session(self, adapter_session_id: str) -> dict[str, Any] | None:
        row = get_odoo_read_only_adapter_session_by_id(self.session, adapter_session_id)
        if row is None:
            return None
        create_odoo_read_only_adapter_audit_event(
            self.session,
            adapter_session_id=row.adapter_session_id,
            activation_id=row.activation_id,
            capability_set_id=row.capability_set_id,
            setup_session_id=row.setup_session_id,
            credential_ref=row.credential_ref,
            event_type="odoo_read_only_adapter_session_retrieved",
            status=row.status,
            actor=row.created_by,
            details_json="{}",
        )
        return self._row_to_dict(row)

    def list_sessions(self, limit: int = 50) -> list[dict[str, Any]]:
        return [
            self._row_to_dict(row)
            for row in list_odoo_read_only_adapter_sessions(self.session, limit=limit)
        ]

    def _row_to_result(self, row: Any) -> OdooReadOnlyAdapter:
        return OdooReadOnlyAdapter(**self._row_to_dict(row))

    def _row_to_dict(self, row: Any) -> dict[str, Any]:
        return {
            "adapter_session_id": row.adapter_session_id,
            "activation_id": row.activation_id,
            "capability_set_id": row.capability_set_id,
            "setup_session_id": row.setup_session_id,
            "credential_ref": row.credential_ref,
            "adapter_id": row.adapter_id,
            "adapter_type": row.adapter_type,
            "mode": row.mode,
            "status": row.status,
            "created_by": row.created_by,
            "blocking_reasons": json.loads(row.blocking_reasons_json),
            "can_connect_later": row.status == "prepared",
            "will_connect_now": False,
            "external_http_performed": False,
            "login_attempted": False,
            "odoo_rpc_performed": False,
            "odoo_read_performed": False,
            "odoo_write_performed": False,
            "schema_inspection_performed": False,
            "permission_inspection_performed": False,
            "credentials_exposed": False,
            "raw_secret_accessed": False,
        }
