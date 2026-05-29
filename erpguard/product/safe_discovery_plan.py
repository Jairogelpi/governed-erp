"""Sprint 57 - Safe Discovery Plan and read-only surface model.

Builds static plan-only models from Sprint 56 fingerprinting plans.
No network, login, schema inspection, permission inspection, data read,
capability generation, connector activation, writes, or raw secret access.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from erpguard.db.repositories import (
    create_safe_discovery_audit_event,
    create_safe_discovery_plan,
    get_credential_vault_entry_by_ref,
    get_erp_fingerprinting_plan_by_id,
    get_safe_discovery_plan_by_id,
    list_safe_discovery_plans,
)


@dataclass
class DiscoveredObjectCandidate:
    object_type: str
    adapter_native_hint: str
    read_supported_planned: bool
    search_supported_planned: bool
    schema_inspection_planned: bool
    permission_inspection_planned: bool
    confidence: float
    risk_level: str


@dataclass
class DiscoveredFieldCandidate:
    object_type: str
    field_name: str
    field_label: str
    field_type: str
    readable_planned: bool
    writable_planned: bool
    sensitive_planned: bool
    redaction_required: bool


@dataclass
class PermissionSurfaceCandidate:
    object_type: str
    read_permission_check_planned: bool
    write_permission_check_planned: bool
    credential_scope_check_planned: bool


@dataclass
class BlockedWriteSurface:
    operation_type: str
    object_type: str
    blocked: bool
    reason: str


@dataclass
class SafeDiscoveryPlanInput:
    fingerprint_plan_id: str
    selected_adapter_type: str | None = None
    created_by: str = "operator_1"


@dataclass
class SafeDiscoveryPlanResult:
    discovery_plan_id: str
    fingerprint_plan_id: str
    setup_session_id: str
    credential_ref: str
    selected_adapter_type: str
    connector_name: str
    erp_url_host: str
    environment_type: str
    status: str
    read_only_surface: dict[str, Any]
    blocked_write_surface: list[dict[str, Any]]
    permission_surface: list[dict[str, Any]]
    planned_discovery_steps: list[dict[str, Any]]
    risk_summary: dict[str, Any]
    next_safe_step: str | None
    blocking_reasons: list[str]
    will_connect: bool = False
    external_http_performed: bool = False
    login_attempted: bool = False
    schema_inspection_performed: bool = False
    permission_inspection_performed: bool = False
    sample_data_read: bool = False
    capability_generation_performed: bool = False
    read_only_activation_performed: bool = False
    erp_write_performed: bool = False
    credentials_exposed: bool = False
    raw_secret_accessed: bool = False


_SURFACE_TEMPLATES: dict[str, list[tuple[str, str, float, str]]] = {
    "odoo": [
        ("partner", "res.partner", 0.8, "low"),
        ("product", "product.template/product.product", 0.8, "low"),
        ("sale_order", "sale.order", 0.8, "low"),
        ("invoice", "account.move", 0.75, "medium"),
        ("stock_item", "stock.quant", 0.7, "medium"),
        ("manufacturing_order", "mrp.production", 0.7, "medium"),
    ],
    "holded": [
        ("partner", "partner", 0.75, "low"),
        ("product", "product", 0.75, "low"),
        ("invoice", "invoice", 0.75, "medium"),
        ("payment", "payment", 0.65, "medium"),
        ("custom_object", "custom", 0.4, "medium"),
    ],
    "sap": [
        ("partner", "business_partner", 0.7, "low"),
        ("product", "material", 0.7, "low"),
        ("sale_order", "sales_order", 0.65, "medium"),
        ("purchase_order", "purchase_order", 0.65, "medium"),
        ("stock_item", "inventory", 0.6, "medium"),
        ("journal_entry", "journal_entry", 0.55, "medium"),
        ("custom_object", "custom", 0.4, "medium"),
    ],
    "dynamics": [
        ("partner", "account/contact", 0.7, "low"),
        ("sale_order", "salesorder", 0.65, "medium"),
        ("invoice", "invoice", 0.65, "medium"),
        ("product", "product", 0.7, "low"),
        ("custom_object", "custom", 0.4, "medium"),
    ],
    "netsuite": [
        ("partner", "customer/vendor", 0.7, "low"),
        ("invoice", "invoice", 0.65, "medium"),
        ("payment", "payment", 0.6, "medium"),
        ("product", "item", 0.7, "low"),
        ("custom_object", "customrecord", 0.4, "medium"),
    ],
    "custom_rest": [
        ("custom_object", "resource", 0.5, "medium"),
        ("partner", "partner_resource_optional", 0.25, "low"),
        ("product", "product_resource_optional", 0.25, "low"),
    ],
    "unknown": [
        ("custom_object", "unknown_resource", 0.3, "medium"),
        ("partner", "partner_resource_optional", 0.2, "low"),
        ("product", "product_resource_optional", 0.2, "low"),
    ],
}

_WRITE_OPERATIONS = [
    "create_object",
    "update_object",
    "delete_object",
    "post_document",
    "confirm_document",
    "reconcile_payment",
    "produce_manufacturing_order",
]

_PLANNED_STEPS = [
    ("inspect_login_context_future", True, True, False, "medium"),
    ("inspect_schema_metadata_future", True, True, False, "medium"),
    ("inspect_read_permissions_future", True, True, False, "medium"),
    ("sample_read_only_records_future", True, True, True, "medium"),
    ("build_read_only_surface_future", False, False, False, "low"),
    ("build_blocked_write_surface_future", False, False, False, "low"),
]


def _asdict_list(items: list[Any]) -> list[dict[str, Any]]:
    return [vars(item) for item in items]


def _blocked_result(
    *,
    plan_input: SafeDiscoveryPlanInput,
    reason: str,
    fingerprint_plan: Any | None = None,
) -> SafeDiscoveryPlanResult:
    return SafeDiscoveryPlanResult(
        discovery_plan_id="",
        fingerprint_plan_id=plan_input.fingerprint_plan_id,
        setup_session_id=getattr(fingerprint_plan, "setup_session_id", ""),
        credential_ref=getattr(fingerprint_plan, "credential_ref", ""),
        selected_adapter_type=plan_input.selected_adapter_type or "",
        connector_name=getattr(fingerprint_plan, "connector_name", ""),
        erp_url_host=getattr(fingerprint_plan, "erp_url_host", ""),
        environment_type=getattr(fingerprint_plan, "environment_type", ""),
        status="blocked",
        read_only_surface={"objects": [], "fields": []},
        blocked_write_surface=[],
        permission_surface=[],
        planned_discovery_steps=[],
        risk_summary={},
        next_safe_step=None,
        blocking_reasons=[reason],
    )


def _select_adapter(
    candidates: list[dict[str, Any]], selected_adapter_type: str | None
) -> str | None:
    if not candidates:
        return None
    if selected_adapter_type:
        candidate_types = {c.get("adapter_type") for c in candidates}
        return selected_adapter_type if selected_adapter_type in candidate_types else None
    best = sorted(candidates, key=lambda c: c.get("confidence", 0), reverse=True)[0]
    return best.get("adapter_type")


def _build_objects(adapter_type: str) -> list[DiscoveredObjectCandidate]:
    template = _SURFACE_TEMPLATES.get(adapter_type, _SURFACE_TEMPLATES["unknown"])
    return [
        DiscoveredObjectCandidate(
            object_type=object_type,
            adapter_native_hint=native_hint,
            read_supported_planned=True,
            search_supported_planned=True,
            schema_inspection_planned=True,
            permission_inspection_planned=True,
            confidence=confidence,
            risk_level=risk_level,
        )
        for object_type, native_hint, confidence, risk_level in template
    ]


def _build_fields(objects: list[DiscoveredObjectCandidate]) -> list[DiscoveredFieldCandidate]:
    fields = []
    for obj in objects:
        fields.extend(
            [
                DiscoveredFieldCandidate(
                    object_type=obj.object_type,
                    field_name="id",
                    field_label="ID",
                    field_type="identifier",
                    readable_planned=True,
                    writable_planned=False,
                    sensitive_planned=False,
                    redaction_required=False,
                ),
                DiscoveredFieldCandidate(
                    object_type=obj.object_type,
                    field_name="display_name",
                    field_label="Display Name",
                    field_type="string",
                    readable_planned=True,
                    writable_planned=False,
                    sensitive_planned=False,
                    redaction_required=False,
                ),
                DiscoveredFieldCandidate(
                    object_type=obj.object_type,
                    field_name="external_reference",
                    field_label="External Reference",
                    field_type="string",
                    readable_planned=True,
                    writable_planned=False,
                    sensitive_planned=True,
                    redaction_required=True,
                ),
            ]
        )
    return fields


def _build_permission_surface(
    objects: list[DiscoveredObjectCandidate],
) -> list[PermissionSurfaceCandidate]:
    return [
        PermissionSurfaceCandidate(
            object_type=obj.object_type,
            read_permission_check_planned=True,
            write_permission_check_planned=False,
            credential_scope_check_planned=True,
        )
        for obj in objects
    ]


def _build_blocked_writes(
    objects: list[DiscoveredObjectCandidate],
) -> list[BlockedWriteSurface]:
    result = []
    object_types = [obj.object_type for obj in objects] or ["custom_object"]
    for operation in _WRITE_OPERATIONS:
        for object_type in object_types:
            result.append(
                BlockedWriteSurface(
                    operation_type=operation,
                    object_type=object_type,
                    blocked=True,
                    reason="Sprint 57 is plan/model only; write-like operations are blocked.",
                )
            )
    return result


def _build_planned_steps() -> list[dict[str, Any]]:
    return [
        {
            "step_type": step_type,
            "method": "plan_only",
            "would_require_network": would_require_network,
            "would_use_credentials": would_use_credentials,
            "would_read_data": would_read_data,
            "would_write_data": False,
            "risk_level": risk_level,
            "status": "planned",
        }
        for (
            step_type,
            would_require_network,
            would_use_credentials,
            would_read_data,
            risk_level,
        ) in _PLANNED_STEPS
    ]


class SafeDiscoveryPlanService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_plan(self, plan_input: SafeDiscoveryPlanInput) -> SafeDiscoveryPlanResult:
        create_safe_discovery_audit_event(
            self.session,
            discovery_plan_id="",
            fingerprint_plan_id=plan_input.fingerprint_plan_id,
            setup_session_id="",
            credential_ref="",
            event_type="safe_discovery_plan_requested",
            status="requested",
            created_by=plan_input.created_by,
            details_json=json.dumps(
                {"selected_adapter_type": plan_input.selected_adapter_type}
            ),
        )
        fingerprint_plan = get_erp_fingerprinting_plan_by_id(
            self.session, plan_input.fingerprint_plan_id
        )
        if fingerprint_plan is None:
            return self._blocked(plan_input, "fingerprinting_plan_not_found")
        if fingerprint_plan.status != "planned":
            return self._blocked(
                plan_input, "fingerprinting_plan_not_ready", fingerprint_plan
            )

        candidates = json.loads(fingerprint_plan.adapter_candidates_json)
        if not candidates:
            return self._blocked(
                plan_input, "adapter_candidate_required", fingerprint_plan
            )
        if not fingerprint_plan.credential_ref:
            return self._blocked(plan_input, "credential_ref_required", fingerprint_plan)

        credential = get_credential_vault_entry_by_ref(
            self.session, fingerprint_plan.credential_ref
        )
        if credential is None:
            return self._blocked(plan_input, "credential_not_found", fingerprint_plan)
        if credential.status == "revoked":
            return self._blocked(plan_input, "credential_revoked", fingerprint_plan)

        selected_adapter = _select_adapter(candidates, plan_input.selected_adapter_type)
        if selected_adapter is None:
            return self._blocked(
                plan_input, "adapter_candidate_required", fingerprint_plan
            )

        objects = _build_objects(selected_adapter)
        fields = _build_fields(objects)
        permission_surface = _build_permission_surface(objects)
        blocked_write_surface = _build_blocked_writes(objects)
        planned_steps = _build_planned_steps()
        read_only_surface = {
            "objects": _asdict_list(objects),
            "fields": _asdict_list(fields),
        }
        risk_summary = {
            "overall_risk": "medium",
            "plan_only": True,
            "needs_network_future": True,
            "uses_credentials_future": True,
            "would_read_data_future": True,
            "writes_blocked": True,
        }
        discovery_plan_id = f"dplan_{uuid.uuid4().hex[:12]}"

        row = create_safe_discovery_plan(
            self.session,
            discovery_plan_id=discovery_plan_id,
            fingerprint_plan_id=fingerprint_plan.fingerprint_plan_id,
            setup_session_id=fingerprint_plan.setup_session_id,
            credential_ref=fingerprint_plan.credential_ref,
            selected_adapter_type=selected_adapter,
            connector_name=fingerprint_plan.connector_name,
            erp_url_host=fingerprint_plan.erp_url_host,
            environment_type=fingerprint_plan.environment_type,
            status="planned",
            read_only_surface_json=json.dumps(read_only_surface),
            blocked_write_surface_json=json.dumps(_asdict_list(blocked_write_surface)),
            permission_surface_json=json.dumps(_asdict_list(permission_surface)),
            planned_discovery_steps_json=json.dumps(planned_steps),
            risk_summary_json=json.dumps(risk_summary),
            next_safe_step="read_only_surface_review",
            created_by=plan_input.created_by,
            blocking_reasons_json="[]",
        )
        create_safe_discovery_audit_event(
            self.session,
            discovery_plan_id=row.discovery_plan_id,
            fingerprint_plan_id=row.fingerprint_plan_id,
            setup_session_id=row.setup_session_id,
            credential_ref=row.credential_ref,
            event_type="safe_discovery_plan_created",
            status="planned",
            created_by=plan_input.created_by,
            details_json=json.dumps(
                {
                    "selected_adapter_type": selected_adapter,
                    "object_count": len(objects),
                    "write_surface_blocked": True,
                }
            ),
        )
        return self._row_to_result(row)

    def get_plan(self, discovery_plan_id: str) -> dict[str, Any] | None:
        row = get_safe_discovery_plan_by_id(self.session, discovery_plan_id)
        if row is None:
            return None
        create_safe_discovery_audit_event(
            self.session,
            discovery_plan_id=row.discovery_plan_id,
            fingerprint_plan_id=row.fingerprint_plan_id,
            setup_session_id=row.setup_session_id,
            credential_ref=row.credential_ref,
            event_type="safe_discovery_plan_retrieved",
            status=row.status,
            created_by=row.created_by,
            details_json="{}",
        )
        return self._row_to_dict(row)

    def list_plans(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = list_safe_discovery_plans(self.session, limit=limit)
        return [
            {
                "discovery_plan_id": row.discovery_plan_id,
                "fingerprint_plan_id": row.fingerprint_plan_id,
                "setup_session_id": row.setup_session_id,
                "credential_ref": row.credential_ref,
                "selected_adapter_type": row.selected_adapter_type,
                "connector_name": row.connector_name,
                "erp_url_host": row.erp_url_host,
                "status": row.status,
            }
            for row in rows
        ]

    def _blocked(
        self,
        plan_input: SafeDiscoveryPlanInput,
        reason: str,
        fingerprint_plan: Any | None = None,
    ) -> SafeDiscoveryPlanResult:
        result = _blocked_result(
            plan_input=plan_input, reason=reason, fingerprint_plan=fingerprint_plan
        )
        create_safe_discovery_audit_event(
            self.session,
            discovery_plan_id="",
            fingerprint_plan_id=plan_input.fingerprint_plan_id,
            setup_session_id=result.setup_session_id,
            credential_ref=result.credential_ref,
            event_type="safe_discovery_plan_blocked",
            status="blocked",
            created_by=plan_input.created_by,
            details_json=json.dumps({"blocking_reasons": [reason]}),
        )
        return result

    def _row_to_result(self, row: Any) -> SafeDiscoveryPlanResult:
        data = self._row_to_dict(row)
        return SafeDiscoveryPlanResult(**data)

    def _row_to_dict(self, row: Any) -> dict[str, Any]:
        return {
            "discovery_plan_id": row.discovery_plan_id,
            "fingerprint_plan_id": row.fingerprint_plan_id,
            "setup_session_id": row.setup_session_id,
            "credential_ref": row.credential_ref,
            "selected_adapter_type": row.selected_adapter_type,
            "connector_name": row.connector_name,
            "erp_url_host": row.erp_url_host,
            "environment_type": row.environment_type,
            "status": row.status,
            "read_only_surface": json.loads(row.read_only_surface_json),
            "blocked_write_surface": json.loads(row.blocked_write_surface_json),
            "permission_surface": json.loads(row.permission_surface_json),
            "planned_discovery_steps": json.loads(row.planned_discovery_steps_json),
            "risk_summary": json.loads(row.risk_summary_json),
            "next_safe_step": row.next_safe_step,
            "blocking_reasons": json.loads(row.blocking_reasons_json),
            "will_connect": False,
            "external_http_performed": False,
            "login_attempted": False,
            "schema_inspection_performed": False,
            "permission_inspection_performed": False,
            "sample_data_read": False,
            "capability_generation_performed": False,
            "read_only_activation_performed": False,
            "erp_write_performed": False,
            "credentials_exposed": False,
            "raw_secret_accessed": False,
        }
