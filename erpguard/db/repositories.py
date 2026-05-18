import json
from uuid import uuid4

from sqlalchemy.orm import Session

from erpguard.canonical.enums import ERPType, InvariantSeverity, InvariantStatus
from erpguard.core.results import PreflightResult
from erpguard.db.models import AuditEvent, Connection, InvariantResult, PreflightCase
from erpguard.policies.results import PolicyIssue


def create_connection(session: Session, name: str, erp_type: ERPType, config: dict, status: str = "created") -> Connection:
    # TODO: Encrypt connection secrets or move them to a dedicated secret manager.
    connection = Connection(
        id=f"conn_{uuid4().hex}",
        erp_type=erp_type.value,
        name=name,
        config_json=_to_json(config),
        status=status,
    )
    session.add(connection)
    session.commit()
    session.refresh(connection)
    return connection


def get_connection(session: Session, connection_id: str) -> Connection | None:
    return session.get(Connection, connection_id)


def list_connections(session: Session) -> list[Connection]:
    return list(session.query(Connection).order_by(Connection.created_at.desc()).all())


def create_preflight_case(session: Session, result: PreflightResult, connection_id: str = "fake") -> PreflightCase:
    case = PreflightCase(
        id=result.id,
        connection_id=connection_id,
        actor_json=_to_json(result.actor),
        action_json=_to_json(result.action),
        canonical_action=result.canonical_action.value,
        canonical_object=result.canonical_object,
        state_snapshot_json=_to_json(result.evidence.get("target", {})),
        simulation_json=_to_json(
            {
                "predicted_impact": result.predicted_impact,
                "evidence": result.evidence,
            }
        ),
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


def list_invariant_results(session: Session, case_id: str) -> list[InvariantResult]:
    return list(
        session.query(InvariantResult)
        .filter(InvariantResult.preflight_case_id == case_id)
        .order_by(InvariantResult.created_at.asc())
        .all()
    )


def list_audit_events(session: Session, case_id: str) -> list[AuditEvent]:
    return list(
        session.query(AuditEvent)
        .filter(AuditEvent.case_id == case_id)
        .order_by(AuditEvent.created_at.asc())
        .all()
    )


def _to_json(value) -> str:
    return json.dumps(value, default=str)
