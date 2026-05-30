"""Sprint 75 - controlled Odoo connection/auth test.

This service is intentionally narrow. With allow_network_test=false it performs
no network work. With allow_network_test=true it delegates only to an injectable
connection/auth client and still records no business reads, schema inspection,
permission inspection, writes, browser, MCP, scheduler, or raw secret exposure.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from erpguard.db.repositories import (
    create_odoo_connection_test,
    create_odoo_connection_test_audit_event,
    get_connector_setup_session,
    get_credential_vault_entry_by_ref,
    get_odoo_connection_test_by_id,
    get_odoo_read_only_adapter_session_by_id,
    list_odoo_connection_test_audit_events,
    list_odoo_connection_tests,
)


class OdooConnectionTestStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class OdooConnectionTestInput:
    adapter_session_id: str
    requested_by: str = "operator_1"
    allow_network_test: bool = False


@dataclass
class OdooConnectionTestResult:
    connection_test_id: str
    adapter_session_id: str
    activation_id: str
    setup_session_id: str
    credential_ref: str
    adapter_type: str
    status: str
    network_test_allowed: bool
    external_http_performed: bool
    login_attempted: bool
    login_succeeded: bool
    odoo_rpc_performed: bool
    odoo_server_version: str | None
    business_data_read: bool = False
    schema_inspection_performed: bool = False
    permission_inspection_performed: bool = False
    odoo_write_performed: bool = False
    credentials_exposed: bool = False
    raw_secret_accessed: bool = False
    blocking_reasons: list[str] | None = None


class OdooConnectionClient(Protocol):
    def test_authentication(self, *, adapter_session: Any, credential_metadata: Any) -> dict[str, Any]:
        ...


class NoopOdooConnectionClient:
    """Default client keeps production safe unless a real client is explicitly wired."""

    def test_authentication(self, *, adapter_session: Any, credential_metadata: Any) -> dict[str, Any]:
        return {
            "login_succeeded": False,
            "blocking_reason": "connection_failed",
        }


def _safe_event_details(details: dict[str, Any]) -> str:
    return json.dumps(details, sort_keys=True)


def _is_safe_url(value: str | None) -> bool:
    if not value:
        return False
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        return False
    host = parsed.hostname or ""
    if not host or host in {"localhost", "127.0.0.1", "::1"}:
        return False
    return True


class OdooConnectionTestService:
    def __init__(
        self,
        session: Session,
        *,
        connection_client: OdooConnectionClient | None = None,
    ) -> None:
        self.session = session
        self.connection_client = connection_client

    def run_test(self, input: OdooConnectionTestInput) -> OdooConnectionTestResult:
        connection_test_id = f"odoo_ct_{uuid.uuid4().hex[:12]}"
        create_odoo_connection_test_audit_event(
            self.session,
            connection_test_id=connection_test_id,
            adapter_session_id=input.adapter_session_id,
            activation_id="",
            setup_session_id="",
            credential_ref="",
            event_type="odoo_connection_test_requested",
            status="requested",
            actor=input.requested_by,
            details_json=_safe_event_details(
                {"network_test_allowed": input.allow_network_test}
            ),
        )

        adapter_session = get_odoo_read_only_adapter_session_by_id(
            self.session, input.adapter_session_id
        )
        credential_metadata = None
        reason = None
        if adapter_session is None:
            reason = "adapter_session_not_found"
        elif adapter_session.status != "prepared":
            reason = "adapter_session_not_prepared"
        elif adapter_session.adapter_type != "odoo":
            reason = "adapter_type_not_odoo"
        elif adapter_session.mode != "read_only":
            reason = "mode_not_read_only"
        elif not input.allow_network_test:
            reason = "network_test_not_allowed"
        else:
            credential_metadata = get_credential_vault_entry_by_ref(
                self.session, adapter_session.credential_ref
            )
            if credential_metadata is None:
                reason = "credential_not_found"
            elif credential_metadata.status == "revoked":
                reason = "credential_revoked"
            else:
                setup_session = get_connector_setup_session(
                    self.session, adapter_session.setup_session_id
                )
                if setup_session is None or not _is_safe_url(setup_session.erp_url):
                    reason = "unsafe_or_invalid_url"

        if reason is not None:
            row = self._persist(
                connection_test_id=connection_test_id,
                adapter_session=adapter_session,
                input=input,
                status=OdooConnectionTestStatus.BLOCKED.value,
                network_test_allowed=input.allow_network_test,
                external_http_performed=False,
                login_attempted=False,
                login_succeeded=False,
                odoo_rpc_performed=False,
                odoo_server_version=None,
                blocking_reasons=[reason],
            )
            self._audit(
                row,
                event_type="odoo_connection_test_blocked",
                actor=input.requested_by,
                details={"blocking_reasons": [reason]},
            )
            return self._row_to_result(row)

        client = self.connection_client or self._default_connection_client()
        external_http_performed = True
        login_attempted = True
        odoo_rpc_performed = True
        try:
            response = client.test_authentication(
                adapter_session=adapter_session,
                credential_metadata=credential_metadata,
            )
        except Exception:
            response = {
                "login_succeeded": False,
                "blocking_reason": "connection_failed",
            }

        login_succeeded = bool(response.get("login_succeeded"))
        if login_succeeded:
            status = OdooConnectionTestStatus.PASSED.value
            blocking_reasons: list[str] = []
            event_type = "odoo_connection_test_passed"
        else:
            status = OdooConnectionTestStatus.FAILED.value
            blocking_reasons = [str(response.get("blocking_reason") or "authentication_failed")]
            event_type = "odoo_connection_test_failed"

        row = self._persist(
            connection_test_id=connection_test_id,
            adapter_session=adapter_session,
            input=input,
            status=status,
            network_test_allowed=True,
            external_http_performed=external_http_performed,
            login_attempted=login_attempted,
            login_succeeded=login_succeeded,
            odoo_rpc_performed=odoo_rpc_performed,
            odoo_server_version=response.get("odoo_server_version"),
            blocking_reasons=blocking_reasons,
        )
        self._audit(
            row,
            event_type=event_type,
            actor=input.requested_by,
            details={
                "business_data_read": False,
                "schema_inspection_performed": False,
                "permission_inspection_performed": False,
                "odoo_write_performed": False,
            },
        )
        return self._row_to_result(row)

    def get_test(self, connection_test_id: str) -> dict[str, Any] | None:
        row = get_odoo_connection_test_by_id(self.session, connection_test_id)
        if row is None:
            return None
        self._audit(row, event_type="odoo_connection_test_retrieved", actor=row.requested_by)
        return self._row_to_dict(row)

    def list_tests(self, limit: int = 50) -> list[dict[str, Any]]:
        return [self._row_to_dict(row) for row in list_odoo_connection_tests(self.session, limit=limit)]

    def _default_connection_client(self) -> OdooConnectionClient:
        return NoopOdooConnectionClient()

    def _persist(
        self,
        *,
        connection_test_id: str,
        adapter_session: Any | None,
        input: OdooConnectionTestInput,
        status: str,
        network_test_allowed: bool,
        external_http_performed: bool,
        login_attempted: bool,
        login_succeeded: bool,
        odoo_rpc_performed: bool,
        odoo_server_version: str | None,
        blocking_reasons: list[str],
    ) -> Any:
        return create_odoo_connection_test(
            self.session,
            connection_test_id=connection_test_id,
            adapter_session_id=input.adapter_session_id,
            activation_id=getattr(adapter_session, "activation_id", ""),
            setup_session_id=getattr(adapter_session, "setup_session_id", ""),
            credential_ref=getattr(adapter_session, "credential_ref", ""),
            adapter_type=getattr(adapter_session, "adapter_type", "odoo"),
            status=status,
            network_test_allowed=network_test_allowed,
            external_http_performed=external_http_performed,
            login_attempted=login_attempted,
            login_succeeded=login_succeeded,
            odoo_rpc_performed=odoo_rpc_performed,
            odoo_server_version=odoo_server_version,
            requested_by=input.requested_by,
            blocking_reasons_json=json.dumps(blocking_reasons),
        )

    def _audit(
        self,
        row: Any,
        *,
        event_type: str,
        actor: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        create_odoo_connection_test_audit_event(
            self.session,
            connection_test_id=row.connection_test_id,
            adapter_session_id=row.adapter_session_id,
            activation_id=row.activation_id,
            setup_session_id=row.setup_session_id,
            credential_ref=row.credential_ref,
            event_type=event_type,
            status=row.status,
            actor=actor,
            details_json=_safe_event_details(details or {}),
        )

    def _row_to_result(self, row: Any) -> OdooConnectionTestResult:
        return OdooConnectionTestResult(**self._row_to_dict(row))

    def _row_to_dict(self, row: Any) -> dict[str, Any]:
        return {
            "connection_test_id": row.connection_test_id,
            "adapter_session_id": row.adapter_session_id,
            "activation_id": row.activation_id,
            "setup_session_id": row.setup_session_id,
            "credential_ref": row.credential_ref,
            "adapter_type": row.adapter_type,
            "status": row.status,
            "network_test_allowed": row.network_test_allowed,
            "external_http_performed": row.external_http_performed,
            "login_attempted": row.login_attempted,
            "login_succeeded": row.login_succeeded,
            "odoo_rpc_performed": row.odoo_rpc_performed,
            "odoo_server_version": row.odoo_server_version,
            "business_data_read": False,
            "schema_inspection_performed": False,
            "permission_inspection_performed": False,
            "odoo_write_performed": False,
            "credentials_exposed": False,
            "raw_secret_accessed": False,
            "blocking_reasons": json.loads(row.blocking_reasons_json),
        }


@dataclass
class OdooConnectionTestAuditResult:
    events: list[dict[str, Any]]


class OdooConnectionTestAuditService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_audit(self, limit: int = 50) -> OdooConnectionTestAuditResult:
        return OdooConnectionTestAuditResult(
            events=[
                {
                    "event_type": row.event_type,
                    "connection_test_id": row.connection_test_id,
                    "adapter_session_id": row.adapter_session_id,
                    "activation_id": row.activation_id,
                    "setup_session_id": row.setup_session_id,
                    "credential_ref": row.credential_ref,
                    "status": row.status,
                    "actor": row.actor,
                    "details": json.loads(row.details_json),
                    "created_at": row.created_at,
                }
                for row in list_odoo_connection_test_audit_events(self.session, limit=limit)
            ]
        )
