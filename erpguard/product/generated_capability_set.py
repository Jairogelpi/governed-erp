"""Sprint 58 - generated capabilities from safe discovery.

Generates advisory-only capability artifacts from Sprint 57 safe discovery
plans. It never connects to ERP systems, logs in, inspects live schemas or
permissions, reads ERP data, activates connectors, writes, or reads raw secrets.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from erpguard.db.repositories import (
    create_generated_capability_audit_event,
    create_generated_capability_set,
    get_credential_vault_entry_by_ref,
    get_generated_capability_set_by_id,
    get_safe_discovery_plan_by_id,
    list_generated_capability_sets,
)


@dataclass
class GeneratedAdapterCapability:
    adapter_id: str
    adapter_type: str
    operation_type: str
    object_type: str
    supported: bool
    safety_tier: str
    requires_credentials: bool
    requires_confirmed_token: bool
    supports_preview: bool
    supports_execution: bool
    supports_schema_inspection: bool
    supports_permission_inspection: bool
    field_read_allowlist: list[str]
    field_write_allowlist: list[str]
    blocking_reasons: list[str]
    is_generated: bool
    source_discovery_plan_id: str
    is_advisory_only: bool
    will_execute: bool
    can_execute: bool


@dataclass
class GeneratedBlockedCapability:
    operation_type: str
    object_type: str
    supported: bool
    safety_tier: str
    blocked: bool
    blocking_reasons: list[str]
    is_generated: bool
    source_discovery_plan_id: str
    supports_execution: bool = False


@dataclass
class GeneratedCapabilityInput:
    discovery_plan_id: str
    created_by: str = "operator_1"


@dataclass
class GeneratedCapabilitySetResult:
    capability_set_id: str
    discovery_plan_id: str
    fingerprint_plan_id: str
    setup_session_id: str
    credential_ref: str
    adapter_id: str
    adapter_type: str
    status: str
    capabilities: list[dict[str, Any]]
    blocked_capabilities: list[dict[str, Any]]
    source_surface_snapshot: dict[str, Any]
    policy_summary: dict[str, Any]
    blocking_reasons: list[str]
    is_advisory_only: bool = True
    will_execute: bool = False
    can_execute: bool = False
    external_http_performed: bool = False
    login_attempted: bool = False
    schema_inspection_performed: bool = False
    permission_inspection_performed: bool = False
    sample_data_read: bool = False
    capability_generation_performed: bool = True
    read_only_activation_performed: bool = False
    erp_write_performed: bool = False
    credentials_exposed: bool = False
    raw_secret_accessed: bool = False


def _asdict_list(items: list[Any]) -> list[dict[str, Any]]:
    return [vars(item) for item in items]


def _field_read_allowlist(
    object_type: str, fields: list[dict[str, Any]]
) -> list[str]:
    return [
        field["field_name"]
        for field in fields
        if field.get("object_type") == object_type
        and field.get("readable_planned") is True
        and field.get("redaction_required") is False
    ]


def _capability(
    *,
    adapter_id: str,
    adapter_type: str,
    operation_type: str,
    object_type: str,
    source_discovery_plan_id: str,
    field_read_allowlist: list[str],
    supports_schema_inspection: bool = False,
    supports_permission_inspection: bool = False,
) -> GeneratedAdapterCapability:
    return GeneratedAdapterCapability(
        adapter_id=adapter_id,
        adapter_type=adapter_type,
        operation_type=operation_type,
        object_type=object_type,
        supported=True,
        safety_tier="read_only",
        requires_credentials=True,
        requires_confirmed_token=False,
        supports_preview=True,
        supports_execution=False,
        supports_schema_inspection=supports_schema_inspection,
        supports_permission_inspection=supports_permission_inspection,
        field_read_allowlist=field_read_allowlist,
        field_write_allowlist=[],
        blocking_reasons=[],
        is_generated=True,
        source_discovery_plan_id=source_discovery_plan_id,
        is_advisory_only=True,
        will_execute=False,
        can_execute=False,
    )


def _policy_summary() -> dict[str, Any]:
    return {
        "is_advisory_only": True,
        "will_execute": False,
        "can_execute": False,
        "supports_execution": False,
        "generated_from_safe_discovery": True,
        "real_erp_touched": False,
        "external_http_performed": False,
        "credentials_used": False,
        "raw_secret_accessed": False,
        "capability_generation_performed": True,
        "read_only_activation_performed": False,
        "erp_write_performed": False,
    }


def _blocked_result(
    generation_input: GeneratedCapabilityInput,
    reason: str,
    safe_plan: Any | None = None,
) -> GeneratedCapabilitySetResult:
    return GeneratedCapabilitySetResult(
        capability_set_id="",
        discovery_plan_id=generation_input.discovery_plan_id,
        fingerprint_plan_id=getattr(safe_plan, "fingerprint_plan_id", ""),
        setup_session_id=getattr(safe_plan, "setup_session_id", ""),
        credential_ref=getattr(safe_plan, "credential_ref", ""),
        adapter_id="",
        adapter_type=getattr(safe_plan, "selected_adapter_type", ""),
        status="blocked",
        capabilities=[],
        blocked_capabilities=[],
        source_surface_snapshot={},
        policy_summary=_policy_summary(),
        blocking_reasons=[reason],
    )


class GeneratedCapabilitySetService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def generate(
        self, generation_input: GeneratedCapabilityInput
    ) -> GeneratedCapabilitySetResult:
        create_generated_capability_audit_event(
            self.session,
            capability_set_id="",
            discovery_plan_id=generation_input.discovery_plan_id,
            fingerprint_plan_id="",
            setup_session_id="",
            credential_ref="",
            event_type="generated_capabilities_requested",
            status="requested",
            created_by=generation_input.created_by,
            details_json="{}",
        )
        safe_plan = get_safe_discovery_plan_by_id(
            self.session, generation_input.discovery_plan_id
        )
        if safe_plan is None:
            return self._blocked(
                generation_input, "safe_discovery_plan_not_found", None
            )
        if safe_plan.status != "planned":
            return self._blocked(
                generation_input, "safe_discovery_plan_not_ready", safe_plan
            )
        if not safe_plan.credential_ref:
            return self._blocked(generation_input, "credential_ref_required", safe_plan)
        credential = get_credential_vault_entry_by_ref(
            self.session, safe_plan.credential_ref
        )
        if credential is None:
            return self._blocked(generation_input, "credential_not_found", safe_plan)
        if credential.status == "revoked":
            return self._blocked(generation_input, "credential_revoked", safe_plan)

        read_only_surface = json.loads(safe_plan.read_only_surface_json)
        objects = read_only_surface.get("objects", [])
        fields = read_only_surface.get("fields", [])
        if not objects:
            return self._blocked(
                generation_input, "read_only_surface_required", safe_plan
            )

        capability_set_id = f"gcaps_{uuid.uuid4().hex[:12]}"
        adapter_type = safe_plan.selected_adapter_type
        adapter_id = f"generated_{adapter_type}_{uuid.uuid4().hex[:8]}"
        capabilities = self._build_capabilities(
            adapter_id=adapter_id,
            adapter_type=adapter_type,
            discovery_plan_id=safe_plan.discovery_plan_id,
            objects=objects,
            fields=fields,
        )
        blocked_capabilities = self._build_blocked_capabilities(safe_plan)
        source_snapshot = {
            "read_only_surface": read_only_surface,
            "blocked_write_surface": json.loads(safe_plan.blocked_write_surface_json),
            "permission_surface": json.loads(safe_plan.permission_surface_json),
        }
        policy_summary = _policy_summary()

        row = create_generated_capability_set(
            self.session,
            capability_set_id=capability_set_id,
            discovery_plan_id=safe_plan.discovery_plan_id,
            fingerprint_plan_id=safe_plan.fingerprint_plan_id,
            setup_session_id=safe_plan.setup_session_id,
            credential_ref=safe_plan.credential_ref,
            adapter_id=adapter_id,
            adapter_type=adapter_type,
            status="generated",
            capabilities_json=json.dumps(_asdict_list(capabilities)),
            blocked_capabilities_json=json.dumps(_asdict_list(blocked_capabilities)),
            source_surface_snapshot_json=json.dumps(source_snapshot),
            policy_summary_json=json.dumps(policy_summary),
            created_by=generation_input.created_by,
            blocking_reasons_json="[]",
        )
        create_generated_capability_audit_event(
            self.session,
            capability_set_id=row.capability_set_id,
            discovery_plan_id=row.discovery_plan_id,
            fingerprint_plan_id=row.fingerprint_plan_id,
            setup_session_id=row.setup_session_id,
            credential_ref=row.credential_ref,
            event_type="generated_capabilities_created",
            status="generated",
            created_by=generation_input.created_by,
            details_json=json.dumps(
                {
                    "adapter_type": adapter_type,
                    "capability_count": len(capabilities),
                    "blocked_capability_count": len(blocked_capabilities),
                }
            ),
        )
        return self._row_to_result(row)

    def get(self, capability_set_id: str) -> dict[str, Any] | None:
        row = get_generated_capability_set_by_id(self.session, capability_set_id)
        if row is None:
            return None
        create_generated_capability_audit_event(
            self.session,
            capability_set_id=row.capability_set_id,
            discovery_plan_id=row.discovery_plan_id,
            fingerprint_plan_id=row.fingerprint_plan_id,
            setup_session_id=row.setup_session_id,
            credential_ref=row.credential_ref,
            event_type="generated_capabilities_retrieved",
            status=row.status,
            created_by=row.created_by,
            details_json="{}",
        )
        return self._row_to_dict(row)

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = list_generated_capability_sets(self.session, limit=limit)
        return [
            {
                "capability_set_id": row.capability_set_id,
                "discovery_plan_id": row.discovery_plan_id,
                "fingerprint_plan_id": row.fingerprint_plan_id,
                "setup_session_id": row.setup_session_id,
                "credential_ref": row.credential_ref,
                "adapter_id": row.adapter_id,
                "adapter_type": row.adapter_type,
                "status": row.status,
            }
            for row in rows
        ]

    def _build_capabilities(
        self,
        *,
        adapter_id: str,
        adapter_type: str,
        discovery_plan_id: str,
        objects: list[dict[str, Any]],
        fields: list[dict[str, Any]],
    ) -> list[GeneratedAdapterCapability]:
        capabilities = []
        for obj in objects:
            object_type = obj["object_type"]
            allowlist = _field_read_allowlist(object_type, fields)
            if obj.get("read_supported_planned") is True:
                capabilities.append(
                    _capability(
                        adapter_id=adapter_id,
                        adapter_type=adapter_type,
                        operation_type="read_object",
                        object_type=object_type,
                        source_discovery_plan_id=discovery_plan_id,
                        field_read_allowlist=allowlist,
                    )
                )
            if obj.get("search_supported_planned") is True:
                capabilities.append(
                    _capability(
                        adapter_id=adapter_id,
                        adapter_type=adapter_type,
                        operation_type="search_objects",
                        object_type=object_type,
                        source_discovery_plan_id=discovery_plan_id,
                        field_read_allowlist=allowlist,
                    )
                )
            if obj.get("schema_inspection_planned") is True:
                capabilities.append(
                    _capability(
                        adapter_id=adapter_id,
                        adapter_type=adapter_type,
                        operation_type="inspect_schema",
                        object_type=object_type,
                        source_discovery_plan_id=discovery_plan_id,
                        field_read_allowlist=allowlist,
                        supports_schema_inspection=True,
                    )
                )
            if obj.get("permission_inspection_planned") is True:
                capabilities.append(
                    _capability(
                        adapter_id=adapter_id,
                        adapter_type=adapter_type,
                        operation_type="inspect_permissions",
                        object_type=object_type,
                        source_discovery_plan_id=discovery_plan_id,
                        field_read_allowlist=allowlist,
                        supports_permission_inspection=True,
                    )
                )
        return capabilities

    def _build_blocked_capabilities(
        self, safe_plan: Any
    ) -> list[GeneratedBlockedCapability]:
        blocked_surface = json.loads(safe_plan.blocked_write_surface_json)
        return [
            GeneratedBlockedCapability(
                operation_type=item["operation_type"],
                object_type=item["object_type"],
                supported=False,
                safety_tier="blocked_write",
                blocked=True,
                blocking_reasons=["write_blocked_by_safe_discovery_plan"],
                is_generated=True,
                source_discovery_plan_id=safe_plan.discovery_plan_id,
            )
            for item in blocked_surface
            if item.get("blocked") is True
        ]

    def _blocked(
        self,
        generation_input: GeneratedCapabilityInput,
        reason: str,
        safe_plan: Any | None,
    ) -> GeneratedCapabilitySetResult:
        result = _blocked_result(generation_input, reason, safe_plan)
        create_generated_capability_audit_event(
            self.session,
            capability_set_id="",
            discovery_plan_id=generation_input.discovery_plan_id,
            fingerprint_plan_id=result.fingerprint_plan_id,
            setup_session_id=result.setup_session_id,
            credential_ref=result.credential_ref,
            event_type="generated_capabilities_blocked",
            status="blocked",
            created_by=generation_input.created_by,
            details_json=json.dumps({"blocking_reasons": [reason]}),
        )
        return result

    def _row_to_result(self, row: Any) -> GeneratedCapabilitySetResult:
        return GeneratedCapabilitySetResult(**self._row_to_dict(row))

    def _row_to_dict(self, row: Any) -> dict[str, Any]:
        return {
            "capability_set_id": row.capability_set_id,
            "discovery_plan_id": row.discovery_plan_id,
            "fingerprint_plan_id": row.fingerprint_plan_id,
            "setup_session_id": row.setup_session_id,
            "credential_ref": row.credential_ref,
            "adapter_id": row.adapter_id,
            "adapter_type": row.adapter_type,
            "status": row.status,
            "capabilities": json.loads(row.capabilities_json),
            "blocked_capabilities": json.loads(row.blocked_capabilities_json),
            "source_surface_snapshot": json.loads(row.source_surface_snapshot_json),
            "policy_summary": json.loads(row.policy_summary_json),
            "blocking_reasons": json.loads(row.blocking_reasons_json),
            "is_advisory_only": True,
            "will_execute": False,
            "can_execute": False,
            "external_http_performed": False,
            "login_attempted": False,
            "schema_inspection_performed": False,
            "permission_inspection_performed": False,
            "sample_data_read": False,
            "capability_generation_performed": True,
            "read_only_activation_performed": False,
            "erp_write_performed": False,
            "credentials_exposed": False,
            "raw_secret_accessed": False,
        }
