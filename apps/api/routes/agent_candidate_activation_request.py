from __future__ import annotations

from fastapi import APIRouter, HTTPException

from apps.api.schemas.agent_candidate_activation_request import (
    ActivationRequestAuditResponse,
    ActivationRequestBody,
    ActivationRequestEligibilityResponse,
    ActivationRequestResponse,
    ActivationRequestStatusResponse,
    FinalActivationGateResponse,
)
from erpguard.db.repositories import get_ui_skill_version_record
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.agent_candidate_activation_request import create_activation_request
from erpguard.product.agent_candidate_activation_request_audit import get_activation_request_audit
from erpguard.product.agent_candidate_activation_request_status import get_activation_request_status
from erpguard.product.agent_candidate_activation_request_validator import (
    validate_activation_request_eligibility,
)
from erpguard.product.agent_candidate_final_activation_gate import evaluate_final_activation_gate

router = APIRouter(
    prefix="/v1/agent-builder/advisory",
    tags=["agent-candidate-activation-request"],
)


def _get_version_or_404(version_id: str, db):
    row = get_ui_skill_version_record(db, version_id)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Candidate version '{version_id}' not found.",
        )
    return row


@router.get(
    "/candidates/{version_id}/activation-request/eligibility",
    response_model=ActivationRequestEligibilityResponse,
)
def get_activation_request_eligibility(version_id: str):
    init_db()
    db = SessionLocal()
    try:
        _get_version_or_404(version_id, db)
        r = validate_activation_request_eligibility(version_id, db)
        return ActivationRequestEligibilityResponse(
            version_id=r.version_id,
            skill_id=r.skill_id,
            eligible=r.eligible,
            checks=[
                {"check": c.check, "passed": c.passed, "detail": c.detail}
                for c in r.checks
            ],
            blocking_reasons=r.blocking_reasons,
            can_execute=r.can_execute,
            can_approve=r.can_approve,
            is_advisory_only=r.is_advisory_only,
        )
    finally:
        db.close()


@router.post(
    "/candidates/{version_id}/activation-request",
    response_model=ActivationRequestResponse,
)
def post_activation_request(version_id: str, body: ActivationRequestBody):
    init_db()
    db = SessionLocal()
    try:
        _get_version_or_404(version_id, db)
        r = create_activation_request(
            version_id=version_id,
            requested_by=body.requested_by,
            rationale=body.rationale,
            session=db,
        )
        return ActivationRequestResponse(
            version_id=r.version_id,
            skill_id=r.skill_id,
            request_id=r.request_id,
            request_status=r.request_status,
            requested_by=r.requested_by,
            rationale=r.rationale,
            eligible=r.eligible,
            can_execute=r.can_execute,
            can_approve=r.can_approve,
            is_advisory_only=r.is_advisory_only,
            blocking_reason=r.blocking_reason,
        )
    finally:
        db.close()


@router.get(
    "/candidates/{version_id}/activation-request/status",
    response_model=ActivationRequestStatusResponse,
)
def get_candidate_activation_request_status(version_id: str):
    init_db()
    db = SessionLocal()
    try:
        _get_version_or_404(version_id, db)
        r = get_activation_request_status(version_id, db)
        return ActivationRequestStatusResponse(
            version_id=r.version_id,
            skill_id=r.skill_id,
            request_id=r.request_id,
            request_status=r.request_status,
            requested_by=r.requested_by,
            rationale=r.rationale,
            event_count=r.event_count,
            latest_decision=r.latest_decision,
            version_status=r.version_status,
            can_execute=r.can_execute,
            can_approve=r.can_approve,
            is_advisory_only=r.is_advisory_only,
        )
    finally:
        db.close()


@router.get(
    "/candidates/{version_id}/activation-request/final-gate",
    response_model=FinalActivationGateResponse,
)
def get_final_activation_gate(version_id: str):
    init_db()
    db = SessionLocal()
    try:
        _get_version_or_404(version_id, db)
        r = evaluate_final_activation_gate(version_id, db)
        return FinalActivationGateResponse(
            version_id=r.version_id,
            skill_id=r.skill_id,
            gate_passed=r.gate_passed,
            activation_allowed=r.activation_allowed,
            checks=[
                {"check": c.check, "passed": c.passed, "detail": c.detail}
                for c in r.checks
            ],
            blocking_reasons=r.blocking_reasons,
            request_id=r.request_id,
            request_status=r.request_status,
            can_execute=r.can_execute,
            can_approve=r.can_approve,
            is_advisory_only=r.is_advisory_only,
            blocking_reason=r.blocking_reason,
        )
    finally:
        db.close()


@router.get(
    "/candidates/{version_id}/activation-request/audit",
    response_model=ActivationRequestAuditResponse,
)
def get_candidate_activation_request_audit(version_id: str):
    init_db()
    db = SessionLocal()
    try:
        _get_version_or_404(version_id, db)
        r = get_activation_request_audit(version_id, db)
        return ActivationRequestAuditResponse(
            version_id=r.version_id,
            skill_id=r.skill_id,
            event_count=r.event_count,
            events=[
                {
                    "event_id": e.event_id,
                    "version_id": e.version_id,
                    "step": e.step,
                    "status": e.status,
                    "detail": e.detail,
                    "created_at": e.created_at,
                }
                for e in r.events
            ],
            can_execute=r.can_execute,
            is_advisory_only=r.is_advisory_only,
        )
    finally:
        db.close()
