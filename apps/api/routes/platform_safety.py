from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.schemas.platform_safety import (
    AuditExportBody,
    AuditExportResponse,
    CreateTenantBody,
    KillSwitchBody,
    KillSwitchEventResponse,
    PolicyEvaluationBody,
    PolicyEvaluationResponse,
    RuntimeSafetyResponse,
    TenantResponse,
    TenantSafetySummaryResponse,
)
from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import list_platform_audit_events_for_tenant
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.models import PolicyEvaluationRequestModel
from erpguard.product.platform_audit_export import AuditExportService
from erpguard.product.platform_kill_switch import KillSwitchService
from erpguard.product.platform_policy import PlatformPolicyService
from erpguard.product.platform_runtime_safety import RuntimeSafetyService
from erpguard.product.platform_tenant import TenantService

router = APIRouter(prefix="/v1/platform", tags=["platform-safety"])


@router.post("/tenants", response_model=TenantResponse)
def create_tenant(body: CreateTenantBody):
    init_db()
    session = SessionLocal()
    try:
        tenant = TenantService(session).create(name=body.name, environment=body.environment)
        return _tenant_to_dict(tenant)
    finally:
        session.close()


@router.get("/tenants/{tenant_id}", response_model=TenantResponse)
def get_tenant(tenant_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            tenant = TenantService(session).get(tenant_id)
        except ObjectNotFoundError as exc:
            return _not_found("tenant_not_found", str(exc))
        return _tenant_to_dict(tenant)
    finally:
        session.close()


@router.post("/tenants/{tenant_id}/kill-switch", response_model=KillSwitchEventResponse)
def manage_kill_switch(tenant_id: str, body: KillSwitchBody):
    init_db()
    session = SessionLocal()
    try:
        try:
            svc = KillSwitchService(session)
            if body.action == "activate":
                ev = svc.activate(tenant_id, body.switch_name, body.activated_by, body.reason)
            elif body.action == "deactivate":
                ev = svc.deactivate(tenant_id, body.switch_name, body.activated_by, body.reason)
            else:
                return JSONResponse(status_code=400, content={"error": {"code": "invalid_action", "message": f"Action must be 'activate' or 'deactivate', got '{body.action}'."}})
        except ObjectNotFoundError as exc:
            return _not_found("tenant_not_found", str(exc))
        except ValueError as exc:
            return JSONResponse(status_code=400, content={"error": {"code": "invalid_switch", "message": str(exc)}})
        return ev.model_dump()
    finally:
        session.close()


@router.get("/tenants/{tenant_id}/safety-summary", response_model=TenantSafetySummaryResponse)
def get_tenant_safety_summary(tenant_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            tenant = TenantService(session).get(tenant_id)
        except ObjectNotFoundError as exc:
            return _not_found("tenant_not_found", str(exc))
        ks_svc = KillSwitchService(session)
        active_switches = ks_svc.active_switches_for_tenant(tenant_id)
        ks_events = ks_svc.list_events(tenant_id)
        return {
            "tenant_id": tenant.tenant_id,
            "tenant_name": tenant.name,
            "environment": tenant.environment,
            "status": tenant.status,
            "kill_switches": tenant.kill_switches.model_dump(),
            "any_kill_switch_active": len(active_switches) > 0,
            "rate_limits": tenant.rate_limits.model_dump(),
            "secret_redaction_enforced": tenant.secret_redaction_enforced,
            "recent_kill_switch_events": len(ks_events),
            "allow_generic_real_odoo_writes": False,
            "allow_r3_r4_real_writes": False,
        }
    finally:
        session.close()


@router.get("/tenants/{tenant_id}/audit-events")
def get_tenant_audit_events(tenant_id: str):
    init_db()
    session = SessionLocal()
    try:
        rows = list_platform_audit_events_for_tenant(session, tenant_id, limit=50)
        import json
        return [
            {
                "event_id": r.id,
                "tenant_id": r.tenant_id,
                "event_category": r.event_category,
                "event_type": r.event_type,
                "severity": r.severity,
                "details": json.loads(r.details_json),
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
    finally:
        session.close()


@router.post("/tenants/{tenant_id}/audit-export", response_model=AuditExportResponse)
def generate_audit_export(tenant_id: str, body: AuditExportBody):
    init_db()
    session = SessionLocal()
    try:
        try:
            result = AuditExportService(session).generate(tenant_id, filters=body.filters)
        except ObjectNotFoundError as exc:
            return _not_found("tenant_not_found", str(exc))
        except ValueError as exc:
            return JSONResponse(status_code=400, content={"error": {"code": "export_disabled", "message": str(exc)}})
        return result.model_dump()
    finally:
        session.close()


@router.get("/audit-exports/{export_id}", response_model=AuditExportResponse)
def get_audit_export(export_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            result = AuditExportService(session).get(export_id)
        except ObjectNotFoundError as exc:
            return _not_found("export_not_found", str(exc))
        return result.model_dump()
    finally:
        session.close()


@router.post("/policy/evaluate", response_model=PolicyEvaluationResponse)
def evaluate_policy(body: PolicyEvaluationBody):
    init_db()
    session = SessionLocal()
    try:
        request = PolicyEvaluationRequestModel(
            actor=body.actor,
            action=body.action,
            resource=body.resource,
            context=body.context,
        )
        result = PlatformPolicyService(session).evaluate(request, tenant_id=body.tenant_id)
        return result.model_dump()
    finally:
        session.close()


@router.get("/runtime-safety", response_model=RuntimeSafetyResponse)
def get_runtime_safety():
    init_db()
    session = SessionLocal()
    try:
        summary = RuntimeSafetyService(session).summary()
        return summary.model_dump()
    finally:
        session.close()


def _not_found(code: str, message: str):
    return JSONResponse(status_code=404, content={"error": {"code": code, "message": message}})


def _tenant_to_dict(tenant) -> dict:
    return {
        "tenant_id": tenant.tenant_id,
        "name": tenant.name,
        "environment": tenant.environment,
        "status": tenant.status,
        "kill_switches": tenant.kill_switches.model_dump(),
        "rate_limits": tenant.rate_limits.model_dump(),
        "roles": [r.model_dump() for r in tenant.roles],
        "secret_redaction_enforced": tenant.secret_redaction_enforced,
        "created_at": tenant.created_at,
        "updated_at": tenant.updated_at,
    }
