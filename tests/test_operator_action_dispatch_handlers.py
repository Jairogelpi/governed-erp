from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from erpguard.db.base import Base
from erpguard.db.models import UISkillVersionRecord
from erpguard.product.agent_candidate_human_decision import record_human_decision
from erpguard.product.operator_action_dispatch_handlers import (
    list_dispatchable_actions,
    run_internal_read_only_handler,
)


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


def _make_version(db, *, name: str = "formula-review", status: str = "candidate", is_active: bool = False):
    version = UISkillVersionRecord(
        id=f"ver_{uuid.uuid4().hex[:16]}",
        skill_id=f"skill_{uuid.uuid4().hex[:8]}",
        compiled_skill_id=f"comp_{uuid.uuid4().hex[:8]}",
        name=name,
        status=status,
        steps_json='[{"type":"read","description":"Read formula order"}]',
        guard_names_json=json.dumps(["formula_guard"]),
        runtime_type="agent_advisory",
        promotion_readiness_json="{}",
        is_active=is_active,
    )
    db.add(version)
    db.commit()
    return version


def test_search_skills_returns_read_only_result(db):
    _make_version(db, name="formula-search-target")
    result = run_internal_read_only_handler("search_skills", {"query": "formula"}, db)
    assert result.action_key == "search_skills"
    assert result.result_payload["total_found"] >= 1
    assert result.system_state_mutated is False


def test_inspect_lifecycle_returns_read_only_result(db):
    version = _make_version(db)
    result = run_internal_read_only_handler("inspect_lifecycle", {"version_id": version.id}, db)
    assert result.action_key == "inspect_lifecycle"
    assert result.result_payload["version_id"] == version.id
    assert result.skill_mutated is False


def test_reuse_suggestions_returns_read_only_result(db):
    version_a = _make_version(db, name="formula-alpha", status="active", is_active=True)
    _make_version(db, name="formula-beta", status="active", is_active=True)
    result = run_internal_read_only_handler("reuse_suggestions", {"version_id": version_a.id}, db)
    assert result.action_key == "reuse_suggestions"
    assert "suggestions" in result.result_payload
    assert result.activation_performed is False


def test_recommend_next_step_returns_read_only_result(db):
    version = _make_version(db)
    result = run_internal_read_only_handler("recommend_next_step", {"version_id": version.id}, db)
    assert result.action_key == "recommend_next_step"
    assert result.result_payload["step_count"] >= 1
    assert result.browser_control_performed is False


def test_check_governance_gaps_returns_read_only_result(db):
    version = _make_version(db)
    record_human_decision(version.id, "approve", "reviewer", session=db)
    result = run_internal_read_only_handler("check_governance_gaps", {"version_id": version.id}, db)
    assert result.action_key == "check_governance_gaps"
    assert result.result_payload["version_id"] == version.id
    assert result.erp_writes_performed is False


def test_dispatchable_actions_allowlist(db):
    actions = list_dispatchable_actions()
    assert actions == sorted([
        "check_governance_gaps",
        "inspect_lifecycle",
        "recommend_next_step",
        "reuse_suggestions",
        "search_skills",
    ])
