from __future__ import annotations

from fastapi import APIRouter, HTTPException

from apps.api.schemas.agent_candidate_activation import (
    ActivationAuditEntrySchema,
    ActivationCheckSchema,
    ActivationRequestBody,
    CandidateActivationAuditResponse,
    CandidateActivationEligibilityResponse,
    CandidateActivationResponse,
    CandidateActivationStatusResponse,
    PostActivationSummaryResponse,
)
from erpguard.db.repositories import get_ui_skill_version_record
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.agent_candidate_activation_audit import get_candidate_activation_audit
from erpguard.product.agent_candidate_activation_service import activate_candidate_version
from erpguard.product.agent_candidate_activation_status import get_candidate_activation_status
from erpguard.product.agent_candidate_activation_validator import validate_candidate_for_activation
from erpguard.product.agent_candidate_post_activation_summary import get_post_activation_summary

router = APIRouter(
    prefix="/v1/agent-builder/advisory",
    tags=["agent-candidate-activation"],
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
    "/candidates/{version_id}/activation/eligibility",
    response_model=CandidateActivationEligibilityResponse,
)
def get_activation_eligibility(version_id: str):
    init_db()
    db = SessionLocal()
    try:
        _get_version_or_404(version_id, db)
        r = validate_candidate_for_activation(version_id, db)
        return CandidateActivationEligibilityResponse(
            version_id=r.version_id,
            skill_id=r.skill_id,
            eligible=r.eligible,
            checks=[
                ActivationCheckSchema(check=c.check, passed=c.passed, detail=c.detail)
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
    "/candidates/{version_id}/activation/activate",
    response_model=CandidateActivationResponse,
)
def post_activate_candidate(version_id: str, body: ActivationRequestBody):
    init_db()
    db = SessionLocal()
    try:
        _get_version_or_404(version_id, db)
        r = activate_candidate_version(
            version_id=version_id,
            actor=body.actor,
            session=db,
        )
        return CandidateActivationResponse(
            version_id=r.version_id,
            skill_id=r.skill_id,
            activated=r.activated,
            prior_version_deactivated=r.prior_version_deactivated,
            prior_version_id=r.prior_version_id,
            version_status=r.version_status,
            is_active=r.is_active,
            is_executed=r.is_executed,
            can_execute=r.can_execute,
            can_approve=r.can_approve,
            is_advisory_only=r.is_advisory_only,
            blocking_reason=r.blocking_reason,
        )
    finally:
        db.close()


@router.get(
    "/candidates/{version_id}/activation/status",
    response_model=CandidateActivationStatusResponse,
)
def get_activation_status(version_id: str):
    init_db()
    db = SessionLocal()
    try:
        _get_version_or_404(version_id, db)
        r = get_candidate_activation_status(version_id, db)
        return CandidateActivationStatusResponse(
            version_id=r.version_id,
            skill_id=r.skill_id,
            version_status=r.version_status,
            is_active=r.is_active,
            latest_decision=r.latest_decision,
            request_id=r.request_id,
            request_status=r.request_status,
            event_count=r.event_count,
            is_executed=r.is_executed,
            can_execute=r.can_execute,
            can_approve=r.can_approve,
            is_advisory_only=r.is_advisory_only,
        )
    finally:
        db.close()


@router.get(
    "/candidates/{version_id}/activation/audit",
    response_model=CandidateActivationAuditResponse,
)
def get_activation_audit(version_id: str):
    init_db()
    db = SessionLocal()
    try:
        _get_version_or_404(version_id, db)
        r = get_candidate_activation_audit(version_id, db)
        return CandidateActivationAuditResponse(
            version_id=r.version_id,
            skill_id=r.skill_id,
            event_count=r.event_count,
            lifecycle_event_count=r.lifecycle_event_count,
            entries=[
                ActivationAuditEntrySchema(
                    event_id=e.event_id,
                    version_id=e.version_id,
                    step=e.step,
                    status=e.status,
                    detail=e.detail,
                    created_at=e.created_at,
                    source=e.source,
                )
                for e in r.entries
            ],
            can_execute=r.can_execute,
            is_advisory_only=r.is_advisory_only,
        )
    finally:
        db.close()


@router.get(
    "/candidates/{version_id}/activation/summary",
    response_model=PostActivationSummaryResponse,
)
def get_activation_summary(version_id: str):
    init_db()
    db = SessionLocal()
    try:
        _get_version_or_404(version_id, db)
        r = get_post_activation_summary(version_id, db)
        return PostActivationSummaryResponse(
            version_id=r.version_id,
            skill_id=r.skill_id,
            version_status=r.version_status,
            runtime_type=r.runtime_type,
            is_active=r.is_active,
            latest_decision=r.latest_decision,
            governance_status=r.governance_status,
            request_id=r.request_id,
            request_status=r.request_status,
            activation_event_count=r.activation_event_count,
            lifecycle_event_count=r.lifecycle_event_count,
            summary_notes=r.summary_notes,
            is_executed=r.is_executed,
            can_execute=r.can_execute,
            can_approve=r.can_approve,
            is_advisory_only=r.is_advisory_only,
        )
    finally:
        db.close()
