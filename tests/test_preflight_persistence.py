import json

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from erpguard.adapters.fake import FakeERPAdapter
from erpguard.canonical.enums import CanonicalAction
from erpguard.core.preflight import PREFLIGHT_CREATED, PREFLIGHT_DECIDED, run_preflight
from erpguard.db.base import Base
from erpguard.db.models import AuditEvent, InvariantResult, PreflightCase
from erpguard.db.repositories import (
    create_audit_event,
    create_invariant_results_from_policy_issues,
    create_preflight_case,
    get_preflight_case,
)


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    return session_factory()


def test_persistence_stores_preflight_case():
    session = make_session()
    result = run_preflight(
        adapter=FakeERPAdapter(),
        actor={"type": "user", "id": "actor_1"},
        canonical_action=CanonicalAction.CONFIRM_SALES_ORDER,
        target_id="so_valid",
    )

    case = create_preflight_case(session, result)
    loaded = get_preflight_case(session, case.id)

    assert loaded is not None
    assert loaded.id == case.id
    assert loaded.decision == "require_approval"
    assert loaded.risk_level == "R3"
    assert json.loads(loaded.actor_json)["id"] == "actor_1"


def test_persistence_stores_invariant_results_for_policy_issues():
    session = make_session()
    result = run_preflight(
        adapter=FakeERPAdapter(),
        actor={"type": "user", "id": "actor_1"},
        canonical_action=CanonicalAction.CONFIRM_SALES_ORDER,
        target_id="so_formula_mismatch",
    )
    case = create_preflight_case(session, result)

    rows = create_invariant_results_from_policy_issues(session, case.id, result.issues)

    stored = session.scalars(select(InvariantResult)).all()
    assert len(rows) == 1
    assert len(stored) == 1
    assert stored[0].preflight_case_id == case.id
    assert stored[0].invariant_id == "formula_ml_per_unit_mismatch"
    assert stored[0].status == "failed"
    assert stored[0].severity == "blocking"


def test_persistence_stores_audit_event():
    session = make_session()
    result = run_preflight(
        adapter=FakeERPAdapter(),
        actor={"type": "user", "id": "actor_1"},
        canonical_action=CanonicalAction.CONFIRM_SALES_ORDER,
        target_id="so_valid",
    )
    case = create_preflight_case(session, result)

    created_event = create_audit_event(session, case.id, PREFLIGHT_CREATED, {"case_id": case.id})
    decided_event = create_audit_event(session, case.id, PREFLIGHT_DECIDED, result.model_dump(mode="json"))

    stored_events = session.scalars(select(AuditEvent)).all()
    stored_cases = session.scalars(select(PreflightCase)).all()

    assert len(stored_cases) == 1
    assert len(stored_events) == 2
    assert created_event.event_type == PREFLIGHT_CREATED
    assert decided_event.event_type == PREFLIGHT_DECIDED
    assert json.loads(decided_event.event_json)["decision"] == "require_approval"
