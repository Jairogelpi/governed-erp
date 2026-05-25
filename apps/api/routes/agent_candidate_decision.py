from __future__ import annotations

from fastapi import APIRouter, HTTPException

from apps.api.schemas.agent_candidate_decision import (
    ActivationGateResponse,
    DecisionAuditResponse,
    DecisionHistoryResponse,
    GovernanceSummaryResponse,
    HumanDecisionRequest,
    HumanDecisionResponse,
)
from erpguard.db.repositories import get_ui_skill_version_record
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.agent_candidate_activation_gate_bridge import evaluate_activation_gate
from erpguard.product.agent_candidate_decision_audit import get_decision_audit
from erpguard.product.agent_candidate_decision_history import get_decision_history
from erpguard.product.agent_candidate_governance_summary import get_governance_summary
from erpguard.product.agent_candidate_human_decision import record_human_decision

router = APIRouter(
    prefix="/v1/agent-builder/advisory",
    tags=["agent-candidate-decision"],
)


def _get_version_or_404(version_id: str, db):
    row = get_ui_skill_version_record(db, version_id)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Candidate version '{version_id}' not found.",
        )
    return row


@router.post(
    "/candidates/{version_id}/decision",
    response_model=HumanDecisionResponse,
)
def post_human_decision(version_id: str, body: HumanDecisionRequest):
    init_db()
    db = SessionLocal()
    try:
        _get_version_or_404(version_id, db)
        r = record_human_decision(
            version_id=version_id,
            decision=body.decision,
            actor=body.actor,
            rationale=body.rationale,
            session=db,
        )
        return HumanDecisionResponse(
            version_id=r.version_id,
            skill_id=r.skill_id,
            decision_id=r.decision_id,
            decision=r.decision,
            actor=r.actor,
            rationale=r.rationale,
            governance_status=r.governance_status,
            version_status=r.version_status,
            can_execute=r.can_execute,
            can_approve=r.can_approve,
            is_advisory_only=r.is_advisory_only,
            blocking_reason=r.blocking_reason,
        )
    finally:
        db.close()


@router.get(
    "/candidates/{version_id}/decision-history",
    response_model=DecisionHistoryResponse,
)
def get_candidate_decision_history(version_id: str):
    init_db()
    db = SessionLocal()
    try:
        _get_version_or_404(version_id, db)
        r = get_decision_history(version_id, db)
        return DecisionHistoryResponse(
            version_id=r.version_id,
            skill_id=r.skill_id,
            decision_count=r.decision_count,
            latest_decision=r.latest_decision,
            latest_governance_status=r.latest_governance_status,
            entries=[
                {
                    "decision_id": e.decision_id,
                    "version_id": e.version_id,
                    "decision": e.decision,
                    "actor": e.actor,
                    "rationale": e.rationale,
                    "governance_status": e.governance_status,
                    "created_at": e.created_at,
                }
                for e in r.entries
            ],
            can_execute=r.can_execute,
            is_advisory_only=r.is_advisory_only,
        )
    finally:
        db.close()


@router.get(
    "/candidates/{version_id}/activation-gate",
    response_model=ActivationGateResponse,
)
def get_activation_gate(version_id: str):
    init_db()
    db = SessionLocal()
    try:
        _get_version_or_404(version_id, db)
        r = evaluate_activation_gate(version_id, db)
        return ActivationGateResponse(
            version_id=r.version_id,
            skill_id=r.skill_id,
            gate_passed=r.gate_passed,
            activation_allowed=r.activation_allowed,
            checks=[
                {"check": c.check, "passed": c.passed, "detail": c.detail}
                for c in r.checks
            ],
            blocking_reasons=r.blocking_reasons,
            latest_decision=r.latest_decision,
            can_execute=r.can_execute,
            can_approve=r.can_approve,
            is_advisory_only=r.is_advisory_only,
            blocking_reason=r.blocking_reason,
        )
    finally:
        db.close()


@router.get(
    "/candidates/{version_id}/governance-summary",
    response_model=GovernanceSummaryResponse,
)
def get_candidate_governance_summary(version_id: str):
    init_db()
    db = SessionLocal()
    try:
        _get_version_or_404(version_id, db)
        r = get_governance_summary(version_id, db)
        return GovernanceSummaryResponse(
            version_id=r.version_id,
            skill_id=r.skill_id,
            version_status=r.version_status,
            runtime_type=r.runtime_type,
            approval_packet_exists=r.approval_packet_exists,
            decision_count=r.decision_count,
            latest_decision=r.latest_decision,
            governance_status=r.governance_status,
            governance_label=r.governance_label,
            is_ready_for_activation_gate=r.is_ready_for_activation_gate,
            summary_notes=r.summary_notes,
            can_execute=r.can_execute,
            can_approve=r.can_approve,
            is_advisory_only=r.is_advisory_only,
        )
    finally:
        db.close()


@router.get(
    "/candidates/{version_id}/decision-audit",
    response_model=DecisionAuditResponse,
)
def get_candidate_decision_audit(version_id: str):
    init_db()
    db = SessionLocal()
    try:
        _get_version_or_404(version_id, db)
        r = get_decision_audit(version_id, db)
        return DecisionAuditResponse(
            version_id=r.version_id,
            skill_id=r.skill_id,
            decision_count=r.decision_count,
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
