import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from erpguard.canonical.enums import ERPType, InvariantSeverity, InvariantStatus
from erpguard.core.results import PreflightResult
from erpguard.db.models import AuditEvent, Connection, InvariantResult, PreflightCase, Skill, SkillRun, SkillRunStep, SkillVersion
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


def create_skill(session: Session, name: str, description: str | None, status: str = "draft") -> Skill:
    skill = Skill(
        id=f"skill_{uuid4().hex}",
        name=name,
        description=description,
        status=status,
    )
    session.add(skill)
    session.commit()
    session.refresh(skill)
    return skill


def get_skill(session: Session, skill_id: str) -> Skill | None:
    return session.get(Skill, skill_id)


def list_skills(session: Session) -> list[Skill]:
    return list(session.query(Skill).order_by(Skill.created_at.desc()).all())


def create_skill_version(
    session: Session,
    skill_id: str,
    version: str,
    skill_package_json: str,
    runtime_type: str,
    llm_required_for_repeated_runs: bool,
) -> SkillVersion:
    skill_version = SkillVersion(
        id=f"skill_version_{uuid4().hex}",
        skill_id=skill_id,
        version=version,
        skill_package_json=skill_package_json,
        runtime_type=runtime_type,
        llm_required_for_repeated_runs=llm_required_for_repeated_runs,
    )
    session.add(skill_version)
    session.commit()
    session.refresh(skill_version)
    return skill_version


def get_latest_skill_version(session: Session, skill_id: str) -> SkillVersion | None:
    return (
        session.query(SkillVersion)
        .filter(SkillVersion.skill_id == skill_id)
        .order_by(SkillVersion.created_at.desc())
        .first()
    )


def create_skill_run(
    session: Session,
    skill_id: str,
    skill_version_id: str,
    status: str,
    input_json: str | None = None,
    output_json: str | None = None,
    decision: str | None = None,
    error_text: str | None = None,
    estimated_tokens_saved: int | None = None,
    finished_at: datetime | None = None,
) -> SkillRun:
    skill_run = SkillRun(
        id=f"skill_run_{uuid4().hex}",
        skill_id=skill_id,
        skill_version_id=skill_version_id,
        status=status,
        input_json=input_json,
        output_json=output_json,
        decision=decision,
        error_text=error_text,
        estimated_tokens_saved=estimated_tokens_saved,
        finished_at=finished_at,
    )
    session.add(skill_run)
    session.commit()
    session.refresh(skill_run)
    return skill_run


def create_skill_run_step(
    session: Session,
    skill_run_id: str,
    step_id: str,
    step_type: str,
    status: str,
    input_json: str | None = None,
    output_json: str | None = None,
    error_text: str | None = None,
) -> SkillRunStep:
    skill_run_step = SkillRunStep(
        id=f"skill_run_step_{uuid4().hex}",
        skill_run_id=skill_run_id,
        step_id=step_id,
        step_type=step_type,
        status=status,
        input_json=input_json,
        output_json=output_json,
        error_text=error_text,
    )
    session.add(skill_run_step)
    session.commit()
    session.refresh(skill_run_step)
    return skill_run_step


def finish_skill_run(
    session: Session,
    skill_run_id: str,
    status: str,
    output_json: str | None = None,
    decision: str | None = None,
    error_text: str | None = None,
    estimated_tokens_saved: int | None = None,
):
    skill_run = session.get(SkillRun, skill_run_id)
    if skill_run is None:
        return None
    skill_run.status = status
    skill_run.output_json = output_json
    skill_run.decision = decision
    skill_run.error_text = error_text
    skill_run.estimated_tokens_saved = estimated_tokens_saved
    skill_run.finished_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(skill_run)
    return skill_run


def get_skill_run(session: Session, skill_run_id: str) -> SkillRun | None:
    return session.get(SkillRun, skill_run_id)


def list_skill_run_steps(session: Session, skill_run_id: str) -> list[SkillRunStep]:
    return list(
        session.query(SkillRunStep)
        .filter(SkillRunStep.skill_run_id == skill_run_id)
        .order_by(SkillRunStep.created_at.asc())
        .all()
    )


def _to_json(value) -> str:
    return json.dumps(value, default=str)
