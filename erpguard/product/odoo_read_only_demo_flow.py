"""Sprint 79 - operator-facing Odoo read-only demo flow.

This service orchestrates the existing Block G services. It does not create a
parallel Odoo runtime, perform writes, add arbitrary models/domains, use
browser/MCP/scheduler behavior, or expose raw secrets.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from sqlalchemy.orm import Session

from erpguard.db.repositories import (
    create_odoo_read_only_demo_audit_event,
    create_odoo_read_only_demo_flow,
    get_odoo_read_only_demo_flow_by_id,
    list_odoo_read_only_demo_audit_events,
    list_odoo_read_only_demo_flows,
)
from erpguard.product.odoo_connection_test import (
    OdooConnectionClient,
    OdooConnectionTestInput,
    OdooConnectionTestService,
)
from erpguard.product.odoo_read_evidence_pack import (
    OdooReadEvidencePackInput,
    OdooReadEvidencePackService,
)
from erpguard.product.odoo_read_mapping import (
    OdooReadClient,
    OdooReadMappingInput,
    OdooReadMappingService,
)
from erpguard.product.odoo_read_only_adapter import (
    OdooReadOnlyAdapterService,
    OdooReadOnlyConnectionIntent,
)


DEFAULT_OBJECT_TYPES = ["partner", "product", "sale_order"]
SUPPORTED_OBJECT_TYPES = {
    "partner",
    "product",
    "sale_order",
    "invoice",
    "stock_item",
    "manufacturing_order",
}
DEFAULT_LOOKUPS = {
    "partner": {"id": 1},
    "product": {"id": 2},
    "sale_order": {"id": 3},
    "invoice": {"id": 4},
    "stock_item": {"id": 5},
    "manufacturing_order": {"id": 6},
}


class OdooReadOnlyDemoFlowStatus(StrEnum):
    COMPLETED = "completed"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    FAILED = "failed"


@dataclass
class OdooReadOnlyDemoFlowInput:
    activation_id: str
    requested_by: str = "operator_1"
    object_types: list[str] | None = None
    allow_network_test: bool = False
    allow_business_read: bool = False


@dataclass
class OdooReadOnlyDemoFlowResult:
    demo_flow_id: str
    activation_id: str
    adapter_session_id: str
    connection_test_id: str
    read_mapping_ids: list[str]
    evidence_pack_ids: list[str]
    requested_object_types: list[str]
    object_summaries: list[dict[str, Any]]
    status: str
    safety_summary: dict[str, Any]
    created_by: str
    blocking_reasons: list[str] = field(default_factory=list)


class OdooReadOnlyDemoFlowService:
    def __init__(
        self,
        session: Session,
        *,
        connection_client: OdooConnectionClient | None = None,
        read_client: OdooReadClient | None = None,
    ) -> None:
        self.session = session
        self.connection_client = connection_client
        self.read_client = read_client

    def run_flow(self, input: OdooReadOnlyDemoFlowInput) -> OdooReadOnlyDemoFlowResult:
        demo_flow_id = f"odoo_demo_{uuid.uuid4().hex[:12]}"
        object_types = input.object_types or list(DEFAULT_OBJECT_TYPES)
        safety_summary = _safety_summary(input)
        self._audit_requested(demo_flow_id, input, object_types)

        unsupported = [item for item in object_types if item not in SUPPORTED_OBJECT_TYPES]
        if unsupported:
            return self._persist_and_audit(
                demo_flow_id=demo_flow_id,
                input=input,
                object_types=object_types,
                adapter_session_id="",
                connection_test_id="",
                read_mapping_ids=[],
                evidence_pack_ids=[],
                object_summaries=[
                    _summary(item, "blocked", blocking_reasons=["unsupported_object_type"])
                    for item in unsupported
                ],
                status=OdooReadOnlyDemoFlowStatus.BLOCKED.value,
                safety_summary=safety_summary,
                blocking_reasons=["unsupported_object_type"],
            )

        if not input.allow_network_test:
            return self._persist_and_audit(
                demo_flow_id=demo_flow_id,
                input=input,
                object_types=object_types,
                adapter_session_id="",
                connection_test_id="",
                read_mapping_ids=[],
                evidence_pack_ids=[],
                object_summaries=[],
                status=OdooReadOnlyDemoFlowStatus.BLOCKED.value,
                safety_summary=safety_summary,
                blocking_reasons=["network_test_not_allowed"],
            )

        adapter = OdooReadOnlyAdapterService(self.session).prepare_session(
            OdooReadOnlyConnectionIntent(
                activation_id=input.activation_id,
                created_by=input.requested_by,
            )
        )
        if adapter.status != "prepared":
            return self._persist_and_audit(
                demo_flow_id=demo_flow_id,
                input=input,
                object_types=object_types,
                adapter_session_id=adapter.adapter_session_id,
                connection_test_id="",
                read_mapping_ids=[],
                evidence_pack_ids=[],
                object_summaries=[],
                status=OdooReadOnlyDemoFlowStatus.BLOCKED.value,
                safety_summary=safety_summary,
                blocking_reasons=adapter.blocking_reasons,
            )

        connection = OdooConnectionTestService(
            self.session,
            connection_client=self.connection_client or self._default_connection_client(),
        ).run_test(
            OdooConnectionTestInput(
                adapter_session_id=adapter.adapter_session_id,
                requested_by=input.requested_by,
                allow_network_test=True,
            )
        )
        if connection.status != "passed":
            return self._persist_and_audit(
                demo_flow_id=demo_flow_id,
                input=input,
                object_types=object_types,
                adapter_session_id=adapter.adapter_session_id,
                connection_test_id=connection.connection_test_id,
                read_mapping_ids=[],
                evidence_pack_ids=[],
                object_summaries=[],
                status=OdooReadOnlyDemoFlowStatus.FAILED.value,
                safety_summary=safety_summary,
                blocking_reasons=["connection_test_failed"],
            )

        if not input.allow_business_read:
            return self._persist_and_audit(
                demo_flow_id=demo_flow_id,
                input=input,
                object_types=object_types,
                adapter_session_id=adapter.adapter_session_id,
                connection_test_id=connection.connection_test_id,
                read_mapping_ids=[],
                evidence_pack_ids=[],
                object_summaries=[],
                status=OdooReadOnlyDemoFlowStatus.BLOCKED.value,
                safety_summary=safety_summary,
                blocking_reasons=["business_read_not_allowed"],
            )

        read_mapping_ids: list[str] = []
        evidence_pack_ids: list[str] = []
        object_summaries: list[dict[str, Any]] = []
        flow_reasons: list[str] = []
        read_client = self.read_client or self._default_read_client()

        for object_type in object_types:
            mapping = OdooReadMappingService(
                self.session,
                read_client=read_client,
            ).run_mapping(
                OdooReadMappingInput(
                    connection_test_id=connection.connection_test_id,
                    requested_by=input.requested_by,
                    object_type=object_type,
                    lookup=DEFAULT_LOOKUPS[object_type],
                    allow_business_read=True,
                )
            )
            if mapping.read_mapping_id:
                read_mapping_ids.append(mapping.read_mapping_id)
            if mapping.status != "passed":
                flow_reasons.append("read_mapping_failed")
                object_summaries.append(
                    _summary(
                        object_type,
                        mapping.status,
                        read_mapping_id=mapping.read_mapping_id,
                        blocking_reasons=["read_mapping_failed", *(mapping.blocking_reasons or [])],
                    )
                )
                continue

            evidence = OdooReadEvidencePackService(self.session).create_pack(
                OdooReadEvidencePackInput(
                    read_mapping_id=mapping.read_mapping_id,
                    created_by=input.requested_by,
                )
            )
            if evidence.evidence_pack_id:
                evidence_pack_ids.append(evidence.evidence_pack_id)
            if evidence.status != "created":
                flow_reasons.append("evidence_pack_failed")
                object_summaries.append(
                    _summary(
                        object_type,
                        "failed",
                        read_mapping_id=mapping.read_mapping_id,
                        evidence_pack_id=evidence.evidence_pack_id,
                        blocking_reasons=["evidence_pack_failed", *evidence.blocking_reasons],
                    )
                )
                continue

            canonical = mapping.canonical_object
            object_summaries.append(
                _summary(
                    object_type,
                    "completed",
                    read_mapping_id=mapping.read_mapping_id,
                    evidence_pack_id=evidence.evidence_pack_id,
                    external_id=canonical.get("external_id"),
                    display_name=canonical.get("display_name"),
                )
            )

        completed = len(evidence_pack_ids)
        if flow_reasons and completed:
            status = OdooReadOnlyDemoFlowStatus.PARTIAL.value
            blocking_reasons = sorted(set(flow_reasons))
        elif flow_reasons:
            status = OdooReadOnlyDemoFlowStatus.FAILED.value
            blocking_reasons = sorted(set(flow_reasons))
        else:
            status = OdooReadOnlyDemoFlowStatus.COMPLETED.value
            blocking_reasons = []

        return self._persist_and_audit(
            demo_flow_id=demo_flow_id,
            input=input,
            object_types=object_types,
            adapter_session_id=adapter.adapter_session_id,
            connection_test_id=connection.connection_test_id,
            read_mapping_ids=read_mapping_ids,
            evidence_pack_ids=evidence_pack_ids,
            object_summaries=object_summaries,
            status=status,
            safety_summary=safety_summary,
            blocking_reasons=blocking_reasons,
        )

    def get_flow(self, demo_flow_id: str) -> dict[str, Any] | None:
        row = get_odoo_read_only_demo_flow_by_id(self.session, demo_flow_id)
        if row is None:
            return None
        self._audit(row, event_type="odoo_read_only_demo_flow_retrieved", actor=row.created_by)
        return self._row_to_dict(row)

    def list_flows(self, limit: int = 50) -> list[dict[str, Any]]:
        return [
            self._row_to_dict(row)
            for row in list_odoo_read_only_demo_flows(self.session, limit=limit)
        ]

    def _default_connection_client(self) -> OdooConnectionClient:
        return OdooConnectionTestService(self.session)._default_connection_client()

    def _default_read_client(self) -> OdooReadClient:
        return OdooReadMappingService(self.session)._default_read_client()

    def _audit_requested(
        self,
        demo_flow_id: str,
        input: OdooReadOnlyDemoFlowInput,
        object_types: list[str],
    ) -> None:
        create_odoo_read_only_demo_audit_event(
            self.session,
            demo_flow_id=demo_flow_id,
            activation_id=input.activation_id,
            adapter_session_id="",
            connection_test_id="",
            event_type="odoo_read_only_demo_flow_requested",
            status="requested",
            actor=input.requested_by,
            details_json=json.dumps(
                {
                    "object_types": object_types,
                    "network_test_allowed": input.allow_network_test,
                    "business_read_allowed": input.allow_business_read,
                },
                sort_keys=True,
            ),
        )

    def _persist_and_audit(
        self,
        *,
        demo_flow_id: str,
        input: OdooReadOnlyDemoFlowInput,
        object_types: list[str],
        adapter_session_id: str,
        connection_test_id: str,
        read_mapping_ids: list[str],
        evidence_pack_ids: list[str],
        object_summaries: list[dict[str, Any]],
        status: str,
        safety_summary: dict[str, Any],
        blocking_reasons: list[str],
    ) -> OdooReadOnlyDemoFlowResult:
        row = create_odoo_read_only_demo_flow(
            self.session,
            demo_flow_id=demo_flow_id,
            activation_id=input.activation_id,
            adapter_session_id=adapter_session_id,
            connection_test_id=connection_test_id,
            read_mapping_ids_json=json.dumps(read_mapping_ids),
            evidence_pack_ids_json=json.dumps(evidence_pack_ids),
            requested_object_types_json=json.dumps(object_types),
            object_summaries_json=json.dumps(object_summaries, sort_keys=True, default=str),
            status=status,
            safety_summary_json=json.dumps(safety_summary, sort_keys=True),
            created_by=input.requested_by,
            blocking_reasons_json=json.dumps(blocking_reasons),
        )
        self._audit(row, event_type=_event_type_for_status(status), actor=input.requested_by)
        return self._row_to_result(row)

    def _audit(self, row: Any, *, event_type: str, actor: str) -> None:
        create_odoo_read_only_demo_audit_event(
            self.session,
            demo_flow_id=row.demo_flow_id,
            activation_id=row.activation_id,
            adapter_session_id=row.adapter_session_id,
            connection_test_id=row.connection_test_id,
            event_type=event_type,
            status=row.status,
            actor=actor,
            details_json=json.dumps(
                {
                    "blocking_reasons": json.loads(row.blocking_reasons_json),
                    "demo_only": True,
                },
                sort_keys=True,
            ),
        )

    def _row_to_result(self, row: Any) -> OdooReadOnlyDemoFlowResult:
        return OdooReadOnlyDemoFlowResult(**self._row_to_dict(row))

    def _row_to_dict(self, row: Any) -> dict[str, Any]:
        return {
            "demo_flow_id": row.demo_flow_id,
            "activation_id": row.activation_id,
            "adapter_session_id": row.adapter_session_id,
            "connection_test_id": row.connection_test_id,
            "read_mapping_ids": json.loads(row.read_mapping_ids_json),
            "evidence_pack_ids": json.loads(row.evidence_pack_ids_json),
            "requested_object_types": json.loads(row.requested_object_types_json),
            "object_summaries": json.loads(row.object_summaries_json),
            "status": row.status,
            "safety_summary": json.loads(row.safety_summary_json),
            "created_by": row.created_by,
            "blocking_reasons": json.loads(row.blocking_reasons_json),
        }


def _event_type_for_status(status: str) -> str:
    return {
        "completed": "odoo_read_only_demo_flow_completed",
        "partial": "odoo_read_only_demo_flow_partial",
        "blocked": "odoo_read_only_demo_flow_blocked",
        "failed": "odoo_read_only_demo_flow_failed",
    }[status]


def _safety_summary(input: OdooReadOnlyDemoFlowInput) -> dict[str, Any]:
    return {
        "demo_only": True,
        "network_test_allowed": input.allow_network_test,
        "business_read_allowed": input.allow_business_read,
        "odoo_write_performed": False,
        "write_preview_performed": False,
        "arbitrary_model_access": False,
        "arbitrary_domain_execution": False,
        "browser_control_performed": False,
        "mcp_execution_performed": False,
        "scheduler_used": False,
        "credentials_exposed": False,
        "raw_secret_accessed": False,
    }


def _summary(
    object_type: str,
    status: str,
    *,
    read_mapping_id: str | None = None,
    evidence_pack_id: str | None = None,
    external_id: Any | None = None,
    display_name: Any | None = None,
    blocking_reasons: list[str] | None = None,
) -> dict[str, Any]:
    summary = {
        "object_type": object_type,
        "status": status,
        "blocking_reasons": blocking_reasons or [],
    }
    if read_mapping_id:
        summary["read_mapping_id"] = read_mapping_id
    if evidence_pack_id:
        summary["evidence_pack_id"] = evidence_pack_id
    if external_id is not None:
        summary["external_id"] = str(external_id)
    if display_name is not None:
        summary["display_name"] = str(display_name)
    return summary


@dataclass
class OdooReadOnlyDemoAuditResult:
    events: list[dict[str, Any]]


class OdooReadOnlyDemoAuditService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_audit(self, limit: int = 50) -> OdooReadOnlyDemoAuditResult:
        return OdooReadOnlyDemoAuditResult(
            events=[
                {
                    "event_type": row.event_type,
                    "demo_flow_id": row.demo_flow_id,
                    "activation_id": row.activation_id,
                    "adapter_session_id": row.adapter_session_id,
                    "connection_test_id": row.connection_test_id,
                    "status": row.status,
                    "actor": row.actor,
                    "details": json.loads(row.details_json),
                    "created_at": row.created_at,
                }
                for row in list_odoo_read_only_demo_audit_events(self.session, limit=limit)
            ]
        )
