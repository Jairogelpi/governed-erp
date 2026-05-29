from __future__ import annotations

from fastapi import APIRouter, Query

from apps.api.schemas.operator_action_dispatch import (
    ActionRegistryEntrySchema,
    ActionRegistryResponse,
    DispatchAuditEntrySchema,
    DispatchAuditResponse,
    DispatchEligibilityRequest,
    DispatchEligibilityResponse,
)
from erpguard.db.session import SessionLocal, init_db
from erpguard.db.repositories import count_action_dispatch_eligibility_events
from erpguard.product.operator_action_dispatch_audit import get_dispatch_audit, persist_eligibility_event
from erpguard.product.operator_action_dispatch_eligibility import check_eligibility
from erpguard.product.operator_action_registry import list_all_actions

router = APIRouter(
    prefix="/v1/operator-console",
    tags=["operator-action-dispatch"],
)


@router.get("/action-registry", response_model=ActionRegistryResponse)
def get_action_registry():
    actions = list_all_actions()
    return ActionRegistryResponse(
        actions=[
            ActionRegistryEntrySchema(
                action_key=a.action_key,
                display_name=a.display_name,
                description=a.description,
                endpoint_template=a.endpoint_template,
                method=a.method,
                requires_confirmed_token=a.requires_confirmed_token,
                safety_tier=a.safety_tier,
                allowed=a.allowed,
            )
            for a in actions
        ],
        total=len(actions),
    )


@router.post("/action-plan/dispatch-eligibility", response_model=DispatchEligibilityResponse)
def dispatch_eligibility(body: DispatchEligibilityRequest):
    init_db()
    db = SessionLocal()
    try:
        result = check_eligibility(
            action_key=body.action_key,
            endpoint_hint=body.endpoint_hint,
            method_hint=body.method_hint,
            token_id=body.token_id,
            version_id=body.version_id,
            session=db,
        )
        persist_eligibility_event(result, db)
        return DispatchEligibilityResponse(
            action_key=result.action_key,
            endpoint_hint=result.endpoint_hint,
            eligible=result.eligible,
            blocked_reason=result.blocked_reason,
            policy_name=result.policy_name,
            requires_confirmed_token=result.requires_confirmed_token,
            safety_tier=result.safety_tier,
            token_id=result.token_id,
            token_status=result.token_status,
            version_id=result.version_id,
        )
    finally:
        db.close()


@router.get("/action-plan/dispatch-audit", response_model=DispatchAuditResponse)
def dispatch_audit(limit: int = Query(default=50, ge=1, le=200)):
    init_db()
    db = SessionLocal()
    try:
        result = get_dispatch_audit(db, limit=limit)
        return DispatchAuditResponse(
            entries=[
                DispatchAuditEntrySchema(
                    event_id=e.event_id,
                    action_key=e.action_key,
                    endpoint_hint=e.endpoint_hint,
                    token_id=e.token_id,
                    version_id=e.version_id,
                    eligible=e.eligible,
                    blocked_reason=e.blocked_reason,
                    policy_name=e.policy_name,
                    created_at=e.created_at,
                )
                for e in result.entries
            ],
            event_count=count_action_dispatch_eligibility_events(db),
        )
    finally:
        db.close()
