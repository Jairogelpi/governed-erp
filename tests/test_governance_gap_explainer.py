"""Sprint 40 — Governance Gap Explainer unit tests."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from erpguard.db.base import Base
from erpguard.db.models import UISkillVersionRecord
from erpguard.product.agent_candidate_activation_gate_bridge import evaluate_activation_gate
from erpguard.product.agent_candidate_activation_request import create_activation_request
from erpguard.product.agent_candidate_activation_service import activate_candidate_version
from erpguard.product.agent_candidate_final_activation_gate import evaluate_final_activation_gate
from erpguard.product.agent_candidate_human_decision import record_human_decision
from erpguard.product.agent_skill_run_preview import get_run_preview
from erpguard.product.governance_gap_explainer import explain_governance_gaps


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    import erpguard.db.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _make_version(db):
    vid = f"ver_{uuid.uuid4().hex[:16]}"
    rec = UISkillVersionRecord(
        id=vid,
        skill_id=f"skill_{uuid.uuid4().hex[:8]}",
        compiled_skill_id=f"comp_{uuid.uuid4().hex[:8]}",
        name="test-candidate",
        status="candidate",
        steps_json="[]",
        guard_names_json="[]",
        runtime_type="agent_advisory",
        promotion_readiness_json="{}",
    )
    db.add(rec)
    db.commit()
    return rec


def _full_activate(db, rec):
    record_human_decision(rec.id, "approve", "reviewer", session=db)
    evaluate_activation_gate(rec.id, db)
    create_activation_request(rec.id, "operator", session=db)
    evaluate_final_activation_gate(rec.id, db)
    activate_candidate_version(rec.id, "operator", session=db)


def test_gaps_present_for_raw_candidate(db):
    rec = _make_version(db)
    r = explain_governance_gaps(rec.id, db)
    assert r.gap_count > 0
    assert r.is_fully_governed is False


def test_no_human_decision_gap(db):
    rec = _make_version(db)
    r = explain_governance_gaps(rec.id, db)
    gap_types = [g.gap_type for g in r.gaps]
    assert "no_human_decision" in gap_types


def test_gaps_reduce_after_decision(db):
    rec = _make_version(db)
    gaps_before = explain_governance_gaps(rec.id, db).gap_count
    record_human_decision(rec.id, "approve", "reviewer", session=db)
    evaluate_activation_gate(rec.id, db)
    gaps_after = explain_governance_gaps(rec.id, db).gap_count
    assert gaps_after < gaps_before


def test_fully_governed_after_full_flow(db):
    rec = _make_version(db)
    _full_activate(db, rec)
    get_run_preview(rec.id, db)
    r = explain_governance_gaps(rec.id, db)
    assert r.is_fully_governed is True
    assert r.gap_count == 0


def test_safety_invariants(db):
    rec = _make_version(db)
    r = explain_governance_gaps(rec.id, db)
    assert r.will_execute is False
    assert r.can_execute is False
    assert r.is_advisory_only is True


def test_version_not_found(db):
    r = explain_governance_gaps("nonexistent-id", db)
    assert r.blocking_reason == "version_not_found"
    assert r.gaps == []


def test_gap_fields_populated(db):
    rec = _make_version(db)
    r = explain_governance_gaps(rec.id, db)
    assert len(r.gaps) > 0
    gap = r.gaps[0]
    assert gap.gap_type != ""
    assert gap.description != ""
    assert gap.severity in ("blocking", "warning", "info")
    assert gap.suggested_action != ""


def test_preview_gap_present_without_preview(db):
    rec = _make_version(db)
    _full_activate(db, rec)
    r = explain_governance_gaps(rec.id, db)
    gap_types = [g.gap_type for g in r.gaps]
    assert "preview_not_run" in gap_types
