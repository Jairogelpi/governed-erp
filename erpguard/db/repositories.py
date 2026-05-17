import json
from uuid import uuid4

from sqlalchemy.orm import Session

from erpguard.canonical.enums import InvariantSeverity, InvariantStatus
from erpguard.core.results import PreflightResult
from erpguard.db.models import AuditEvent, InvariantResult, PreflightCase
from erpguard.policies.results import PolicyIssue


def create_preflight_case(session: Session, result: PreflightResult, connection_id: str = "fake") -> PreflightCase:
    case = PreflightCase(
        id=result.id,
        connection_id=connection_id,
        actor_json=_to_json(result.actor),
        action_json=_to_json({"canonical_action": result.canonical_action.value, "target_id": result.target_id}),
        canonical_action=result.canonical_action.value,
        canonical_object="SalesOrder",
        state_snapshot_json=_to_json(result.evidence.get("target", {})),
        simulation_json=_to_json(result.evidence),
        decision=result.decision.value,
        risk_level=result.risk_level.value,
        summary=result.summary,
    )
    session.add(case)
    session.commit()
    session.refresh(case)
    return case


def create_invariant_results_from_policy_issues(
    session: Session,
    preflight_case_id: str,
    issues: list[PolicyIssue],
) -> list[InvariantResult]:
    rows = [
        InvariantResult(
            id=f"inv_{uuid4().hex}",
            preflight_case_id=preflight_case_id,
            invariant_id=issue.code,
            invariant_type="business",
            status=InvariantStatus.FAILED.value,
            severity=InvariantSeverity.BLOCKING.value,
            message=issue.message,
            evidence_json=_to_json(issue.evidence),
        )
        for issue in issues
    ]
    session.add_all(rows)
    session.commit()
    for row in rows:
        session.refresh(row)
    return rows


def create_audit_event(session: Session, case_id: str, event_type: str, event: dict) -> AuditEvent:
    audit_event = AuditEvent(
        id=f"audit_{uuid4().hex}",
        case_id=case_id,
        event_type=event_type,
        event_json=_to_json(event),
    )
    session.add(audit_event)
    session.commit()
    session.refresh(audit_event)
    return audit_event


def get_preflight_case(session: Session, case_id: str) -> PreflightCase | None:
    return session.get(PreflightCase, case_id)


def _to_json(value) -> str:
    return json.dumps(value, default=str)
