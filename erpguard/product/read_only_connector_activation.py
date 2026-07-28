"""Sprint 59 - Read-only connector activation artifact.

Activation is an internal governed artifact only. It never opens a real ERP
connection, enables live reads, enables writes, executes browser/MCP/scheduler
work, or accesses raw secrets.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from erpguard.db.repositories import (
    create_read_only_activation_audit_event,
    create_read_only_activation_request,
    create_read_only_connector_activation,
    get_credential_vault_entry_by_ref,
    get_generated_capability_set_by_id,
    get_read_only_activation_request_by_id,
    get_read_only_connector_activation_by_id,
    list_read_only_connector_activations,
    update_read_only_activation_request_status,
)


@dataclass
class ReadOnlyActivationRequestInput:
    capability_set_id: str
    requested_by: str = "operator_1"
    mode: str = "read_only"


@dataclass
class ReadOnlyActivationApprovalInput:
    activation_request_id: str
    approved_by: str


@dataclass
class ReadOnlyActivationRequestResult:
    activation_request_id: str
    capability_set_id: str
    setup_session_id: str
    credential_ref: str
    adapter_id: str
    adapter_type: str
    mode: str
    requested_by: str
    status: str
    requires_human_approval: bool
    blocking_reasons: list[str]
    will_connect: bool = False
    can_read_real_erp: bool = False
    can_write_real_erp: bool = False
    external_http_performed: bool = False
    login_attempted: bool = False
    real_erp_connection_established: bool = False
    real_erp_read_enabled: bool = False
    real_erp_write_enabled: bool = False
    browser_control_performed: bool = False
    mcp_execution_performed: bool = False
    scheduler_used: bool = False
    credentials_exposed: bool = False
    raw_secret_accessed: bool = False


@dataclass
class ReadOnlyActivationResult:
    activation_id: str
    activation_request_id: str
    capability_set_id: str
    setup_session_id: str
    credential_ref: str
    adapter_id: str
    adapter_type: str
    mode: str
    status: str
    approved_by: str
    blocking_reasons: list[str]
    external_http_performed: bool = False
    login_attempted: bool = False
    real_erp_connection_established: bool = False
    real_erp_read_enabled: bool = False
    real_erp_write_enabled: bool = False
    browser_control_performed: bool = False
    mcp_execution_performed: bool = False
    scheduler_used: bool = False
    credentials_exposed: bool = False
    raw_secret_accessed: bool = False


_WRITE_OPERATIONS = {
    "create_object",
    "update_object",
    "delete_object",
    "post_document",
    "confirm_document",
    "reconcile_payment",
    "produce_manufacturing_order",
}


def _request_blocked(
    request: ReadOnlyActivationRequestInput, reason: str, capability_set: Any | None = None
) -> ReadOnlyActivationRequestResult:
    return ReadOnlyActivationRequestResult(
        activation_request_id="",
        capability_set_id=request.capability_set_id,
        setup_session_id=getattr(capability_set, "setup_session_id", ""),
        credential_ref=getattr(capability_set, "credential_ref", ""),
        adapter_id=getattr(capability_set, "adapter_id", ""),
        adapter_type=getattr(capability_set, "adapter_type", ""),
        mode=request.mode,
        requested_by=request.requested_by,
        status="blocked",
        requires_human_approval=True,
        blocking_reasons=[reason],
    )


def _activation_blocked(
    approval: ReadOnlyActivationApprovalInput, reason: str, request: Any | None = None
) -> ReadOnlyActivationResult:
    return ReadOnlyActivationResult(
        activation_id="",
        activation_request_id=approval.activation_request_id,
        capability_set_id=getattr(request, "capability_set_id", ""),
        setup_session_id=getattr(request, "setup_session_id", ""),
        credential_ref=getattr(request, "credential_ref", ""),
        adapter_id=getattr(request, "adapter_id", ""),
        adapter_type=getattr(request, "adapter_type", ""),
        mode=getattr(request, "mode", "read_only"),
        status="blocked",
        approved_by=approval.approved_by,
        blocking_reasons=[reason],
    )


def _has_executable_write_capability(capability_set: Any) -> bool:
    capabilities = json.loads(capability_set.capabilities_json)
    for cap in capabilities:
        if (
            cap.get("operation_type") in _WRITE_OPERATIONS
            and cap.get("supports_execution") is True
        ):
            return True
    return False


class ReadOnlyConnectorActivationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_request(
        self, request: ReadOnlyActivationRequestInput
    ) -> ReadOnlyActivationRequestResult:
        capability_set = get_generated_capability_set_by_id(
            self.session, request.capability_set_id
        )
        reason = None
        if request.mode != "read_only":
            reason = "mode_not_allowed"
        elif capability_set is None:
            reason = "capability_set_not_found"
        elif capability_set.status != "generated":
            reason = "capability_set_not_ready"
        elif not capability_set.credential_ref:
            reason = "credential_not_found"
        else:
            credential = get_credential_vault_entry_by_ref(
                self.session, capability_set.credential_ref
            )
            if credential is None:
                reason = "credential_not_found"
            elif credential.status == "revoked":
                reason = "credential_revoked"
            elif not json.loads(capability_set.capabilities_json):
                reason = "generated_capabilities_required"
            elif _has_executable_write_capability(capability_set):
                reason = "executable_write_capability_detected"

        if reason is not None:
            result = _request_blocked(request, reason, capability_set)
            create_read_only_activation_audit_event(
                self.session,
                activation_request_id="",
                activation_id="",
                capability_set_id=request.capability_set_id,
                setup_session_id=result.setup_session_id,
                credential_ref=result.credential_ref,
                event_type="read_only_activation_request_blocked",
                status="blocked",
                actor=request.requested_by,
                details_json=json.dumps({"blocking_reasons": [reason]}),
            )
            return result

        assert capability_set is not None  # reason is None only reachable past the capability_set-None branch above
        activation_request_id = f"roactreq_{uuid.uuid4().hex[:12]}"
        row = create_read_only_activation_request(
            self.session,
            activation_request_id=activation_request_id,
            capability_set_id=capability_set.capability_set_id,
            setup_session_id=capability_set.setup_session_id,
            credential_ref=capability_set.credential_ref,
            adapter_id=capability_set.adapter_id,
            adapter_type=capability_set.adapter_type,
            mode="read_only",
            requested_by=request.requested_by,
            status="requested",
            requires_human_approval=True,
            blocking_reasons_json="[]",
        )
        create_read_only_activation_audit_event(
            self.session,
            activation_request_id=row.activation_request_id,
            activation_id="",
            capability_set_id=row.capability_set_id,
            setup_session_id=row.setup_session_id,
            credential_ref=row.credential_ref,
            event_type="read_only_activation_request_created",
            status="requested",
            actor=request.requested_by,
            details_json=json.dumps({"requires_human_approval": True}),
        )
        return self._request_row_to_result(row)

    def approve(self, approval: ReadOnlyActivationApprovalInput) -> ReadOnlyActivationResult:
        request = get_read_only_activation_request_by_id(
            self.session, approval.activation_request_id
        )
        if request is None:
            return self._approval_blocked(
                approval, "activation_request_not_found", None
            )
        if request.status != "requested":
            return self._approval_blocked(
                approval, "activation_request_not_ready", request
            )
        if not approval.approved_by:
            return self._approval_blocked(approval, "approval_actor_required", request)

        update_read_only_activation_request_status(
            self.session, request.activation_request_id, "approved"
        )
        activation_id = f"roconn_{uuid.uuid4().hex[:12]}"
        row = create_read_only_connector_activation(
            self.session,
            activation_id=activation_id,
            activation_request_id=request.activation_request_id,
            capability_set_id=request.capability_set_id,
            setup_session_id=request.setup_session_id,
            credential_ref=request.credential_ref,
            adapter_id=request.adapter_id,
            adapter_type=request.adapter_type,
            mode="read_only",
            status="active_read_only",
            approved_by=approval.approved_by,
            blocking_reasons_json="[]",
        )
        for event_type in (
            "read_only_activation_approved",
            "read_only_connector_activated",
        ):
            create_read_only_activation_audit_event(
                self.session,
                activation_request_id=request.activation_request_id,
                activation_id=row.activation_id,
                capability_set_id=request.capability_set_id,
                setup_session_id=request.setup_session_id,
                credential_ref=request.credential_ref,
                event_type=event_type,
                status=row.status,
                actor=approval.approved_by,
                details_json="{}",
            )
        return self._activation_row_to_result(row)

    def get_activation(self, activation_id: str) -> dict[str, Any] | None:
        row = get_read_only_connector_activation_by_id(self.session, activation_id)
        if row is None:
            return None
        create_read_only_activation_audit_event(
            self.session,
            activation_request_id=row.activation_request_id,
            activation_id=row.activation_id,
            capability_set_id=row.capability_set_id,
            setup_session_id=row.setup_session_id,
            credential_ref=row.credential_ref,
            event_type="read_only_activation_retrieved",
            status=row.status,
            actor=row.approved_by,
            details_json="{}",
        )
        return self._activation_row_to_dict(row)

    def list_activations(self, limit: int = 50) -> list[dict[str, Any]]:
        return [
            self._activation_row_to_dict(row)
            for row in list_read_only_connector_activations(self.session, limit=limit)
        ]

    def _approval_blocked(
        self,
        approval: ReadOnlyActivationApprovalInput,
        reason: str,
        request: Any | None,
    ) -> ReadOnlyActivationResult:
        result = _activation_blocked(approval, reason, request)
        create_read_only_activation_audit_event(
            self.session,
            activation_request_id=approval.activation_request_id,
            activation_id="",
            capability_set_id=result.capability_set_id,
            setup_session_id=result.setup_session_id,
            credential_ref=result.credential_ref,
            event_type="read_only_activation_request_blocked",
            status="blocked",
            actor=approval.approved_by,
            details_json=json.dumps({"blocking_reasons": [reason]}),
        )
        return result

    def _request_row_to_result(self, row: Any) -> ReadOnlyActivationRequestResult:
        return ReadOnlyActivationRequestResult(
            activation_request_id=row.activation_request_id,
            capability_set_id=row.capability_set_id,
            setup_session_id=row.setup_session_id,
            credential_ref=row.credential_ref,
            adapter_id=row.adapter_id,
            adapter_type=row.adapter_type,
            mode=row.mode,
            requested_by=row.requested_by,
            status=row.status,
            requires_human_approval=row.requires_human_approval,
            blocking_reasons=json.loads(row.blocking_reasons_json),
        )

    def _activation_row_to_result(self, row: Any) -> ReadOnlyActivationResult:
        return ReadOnlyActivationResult(**self._activation_row_to_dict(row))

    def _activation_row_to_dict(self, row: Any) -> dict[str, Any]:
        return {
            "activation_id": row.activation_id,
            "activation_request_id": row.activation_request_id,
            "capability_set_id": row.capability_set_id,
            "setup_session_id": row.setup_session_id,
            "credential_ref": row.credential_ref,
            "adapter_id": row.adapter_id,
            "adapter_type": row.adapter_type,
            "mode": row.mode,
            "status": row.status,
            "approved_by": row.approved_by,
            "blocking_reasons": json.loads(row.blocking_reasons_json),
            "external_http_performed": False,
            "login_attempted": False,
            "real_erp_connection_established": False,
            "real_erp_read_enabled": False,
            "real_erp_write_enabled": False,
            "browser_control_performed": False,
            "mcp_execution_performed": False,
            "scheduler_used": False,
            "credentials_exposed": False,
            "raw_secret_accessed": False,
        }
