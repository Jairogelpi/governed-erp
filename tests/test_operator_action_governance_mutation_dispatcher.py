"""Sprint 46 — Internal governance mutation dispatcher tests.

Safety boundary tests come first (per spec), then execution tests.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from erpguard.db.base import Base
from erpguard.db.models import UISkillVersionRecord
from erpguard.db.repositories import (
    create_action_plan_step_token,
    create_agent_candidate_activation_request,
    create_agent_candidate_activation_request_event,
    create_agent_candidate_decision,
    create_agent_candidate_decision_event,
)
from erpguard.product.operator_action_dispatch_execution_audit import get_dispatch_execution_audit
from erpguard.product.operator_action_dispatch_handlers import list_dispatchable_actions
from erpguard.product.operator_action_dispatch_result import get_dispatch_result
from erpguard.product.operator_action_dispatcher import (
    DispatchRequest,
    dispatch_confirmed_action,
)
from erpguard.product.operator_action_governance_mutation_handlers import list_governance_mutation_actions
from erpguard.product.operator_step_confirmation import confirm_token


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


def _make_version(db, *, status: str = "candidate", runtime_type: str = "agent_advisory"):
    version = UISkillVersionRecord(
        id=f"ver_{uuid.uuid4().hex[:16]}",
        skill_id=f"skill_{uuid.uuid4().hex[:8]}",
        compiled_skill_id=f"comp_{uuid.uuid4().hex[:8]}",
        name="test-skill",
        status=status,
        steps_json='[{"type":"read","description":"Read data"}]',
        guard_names_json=json.dumps(["test_guard"]),
        runtime_type=runtime_type,
        promotion_readiness_json="{}",
        is_active=False,
    )
    db.add(version)
    db.commit()
    return version


def _make_token(db, *, endpoint_hint: str, method_hint: str = "POST", confirmed: bool = True):
    token_id = f"tok_{uuid.uuid4().hex[:16]}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    create_action_plan_step_token(
        db,
        token_id=token_id,
        plan_id="aplan_mutation_test",
        step_number=1,
        step_title="Mutation test",
        endpoint_hint=endpoint_hint,
        method_hint=method_hint,
        severity="blocking",
        risk_level="high",
        risk_summary="governance mutation",
        expires_at=expires_at,
    )
    if confirmed:
        confirm_token(token_id, db)
    return token_id


def _dispatch(db, *, action_key: str, version_id: str | None = None, parameters: dict | None = None,
              confirmed: bool = True, endpoint_hint: str = "POST /governance/dispatch"):
    token_id = _make_token(db, endpoint_hint=endpoint_hint, confirmed=confirmed)
    request = DispatchRequest(
        plan_id="aplan_mutation_test",
        step_number=1,
        action_key=action_key,
        endpoint_hint=endpoint_hint,
        method_hint="POST",
        token_id=token_id,
        version_id=version_id,
        parameters=parameters or {},
    )
    return dispatch_confirmed_action(request, session=db)


def _seed_approved_version(db):
    """Create a candidate version with approve decision and gate evaluated event."""
    version = _make_version(db)
    create_agent_candidate_decision(
        db,
        version_id=version.id,
        decision="approve",
        actor="test_reviewer",
        rationale="Meets all criteria",
        detail_json="{}",
    )
    create_agent_candidate_decision_event(
        db,
        version_id=version.id,
        step="activation_gate_evaluated",
        status="completed",
        detail_json="{}",
    )
    return version


def _seed_fully_eligible_version(db):
    """Create a version ready for activate_candidate."""
    version = _seed_approved_version(db)
    create_agent_candidate_activation_request(
        db,
        version_id=version.id,
        skill_id=version.skill_id,
        requested_by="test_operator",
        rationale="Ready to activate",
    )
    create_agent_candidate_activation_request_event(
        db,
        version_id=version.id,
        step="final_activation_gate_evaluated",
        status="completed",
        detail_json="{}",
    )
    return version


# ─── Safety boundary tests ─────────────────────────────────────────────────

def test_mutation_actions_not_in_read_only_registry():
    read_only = set(list_dispatchable_actions())
    for key in ["record_human_decision", "create_activation_request", "activate_candidate"]:
        assert key not in read_only, (
            f"'{key}' must not appear in read-only dispatch registry"
        )


def test_read_only_actions_not_in_mutation_registry():
    mutation = set(list_governance_mutation_actions())
    for key in ["search_skills", "check_governance_gaps", "inspect_lifecycle",
                "recommend_next_step", "reuse_suggestions", "run_preview"]:
        assert key not in mutation, (
            f"'{key}' must not appear in governance mutation registry"
        )


def test_mutation_registries_are_disjoint():
    read_only = set(list_dispatchable_actions())
    mutation = set(list_governance_mutation_actions())
    overlap = read_only & mutation
    assert not overlap, f"Registries overlap: {overlap}"


def test_mutation_action_blocked_without_confirmed_token(db):
    version = _make_version(db)
    result = _dispatch(
        db,
        action_key="record_human_decision",
        version_id=version.id,
        parameters={"decision": "approve", "actor": "reviewer", "rationale": "ok"},
        confirmed=False,
    )
    assert result.status == "blocked"
    assert result.dispatch_performed is False


def test_mutation_handler_type_is_internal_governance_mutation_on_success(db):
    version = _make_version(db)
    result = _dispatch(
        db,
        action_key="record_human_decision",
        version_id=version.id,
        parameters={"decision": "approve", "actor": "reviewer", "rationale": "all good"},
    )
    assert result.status == "completed"
    assert result.handler_type == "internal_governance_mutation"


def test_read_only_handler_type_remains_internal_read_only(db):
    _make_version(db)
    result = _dispatch(
        db,
        action_key="search_skills",
        parameters={"query": "formula"},
        endpoint_hint="GET /v1/agent-builder/discovery/search",
    )
    assert result.handler_type == "internal_read_only"


def test_run_preview_remains_read_only(db):
    version = _seed_approved_version(db)
    create_agent_candidate_activation_request(
        db,
        version_id=version.id,
        skill_id=version.skill_id,
        requested_by="test_operator",
        rationale="Ready to preview",
    )
    version.status = "active"
    version.is_active = True
    db.commit()
    result = _dispatch(
        db,
        action_key="run_preview",
        version_id=version.id,
        parameters={"version_id": version.id},
        endpoint_hint="GET /v1/agent-builder/run-preview",
    )
    assert result.status == "completed"
    assert result.handler_type == "internal_read_only"
    assert result.result_payload["will_execute"] is False
    assert result.result_payload["can_execute"] is False


# ─── record_human_decision ──────────────────────────────────────────────────

def test_record_human_decision_approve_dispatches_correctly(db):
    version = _make_version(db)
    result = _dispatch(
        db,
        action_key="record_human_decision",
        version_id=version.id,
        parameters={"decision": "approve", "actor": "reviewer", "rationale": "meets criteria"},
    )
    assert result.status == "completed"
    assert result.dispatch_performed is True
    assert result.token_confirmed is True
    assert result.eligibility_passed is True
    assert result.result_payload["decision"] == "approve"
    assert result.result_payload["governance_status"] == "approved_pending_activation"
    assert result.result_payload["decision_id"] != ""


def test_record_human_decision_reject_dispatches_correctly(db):
    version = _make_version(db)
    result = _dispatch(
        db,
        action_key="record_human_decision",
        version_id=version.id,
        parameters={"decision": "reject", "actor": "reviewer", "rationale": "incomplete docs"},
    )
    assert result.status == "completed"
    assert result.result_payload["governance_status"] == "rejected"


def test_record_human_decision_missing_actor_blocks(db):
    version = _make_version(db)
    result = _dispatch(
        db,
        action_key="record_human_decision",
        version_id=version.id,
        parameters={"decision": "approve", "actor": "", "rationale": "ok"},
    )
    assert result.status == "blocked"
    assert result.dispatch_performed is False


def test_record_human_decision_missing_version_id_blocks(db):
    result = _dispatch(
        db,
        action_key="record_human_decision",
        version_id=None,
        parameters={"decision": "approve", "actor": "reviewer", "rationale": "ok"},
    )
    assert result.status == "blocked"
    assert result.dispatch_performed is False


def test_record_human_decision_system_state_mutated_is_true(db):
    version = _make_version(db)
    result = _dispatch(
        db,
        action_key="record_human_decision",
        version_id=version.id,
        parameters={"decision": "approve", "actor": "reviewer", "rationale": "ok"},
    )
    assert result.system_state_mutated is True
    assert result.erp_writes_performed is False
    assert result.browser_control_performed is False
    assert result.mcp_execution_performed is False
    assert result.scheduling_performed is False


def test_record_human_decision_result_is_persisted(db):
    version = _make_version(db)
    result = _dispatch(
        db,
        action_key="record_human_decision",
        version_id=version.id,
        parameters={"decision": "approve", "actor": "reviewer", "rationale": "ok"},
    )
    loaded = get_dispatch_result(result.dispatch_id, db)
    assert loaded is not None
    assert loaded.dispatch_id == result.dispatch_id
    assert loaded.handler_type == "internal_governance_mutation"


# ─── create_activation_request ─────────────────────────────────────────────

def test_create_activation_request_dispatches_correctly(db):
    version = _seed_approved_version(db)
    result = _dispatch(
        db,
        action_key="create_activation_request",
        version_id=version.id,
        parameters={"requested_by": "operator", "rationale": "ready"},
    )
    assert result.status == "completed"
    assert result.dispatch_performed is True
    assert result.result_payload["eligible"] is True
    assert result.result_payload["request_id"] != ""
    assert result.result_payload["request_status"] == "pending_review"


def test_create_activation_request_blocked_without_approve_decision(db):
    version = _make_version(db)  # no approve decision
    result = _dispatch(
        db,
        action_key="create_activation_request",
        version_id=version.id,
        parameters={"requested_by": "operator", "rationale": "premature"},
    )
    assert result.status == "blocked"
    assert result.dispatch_performed is False


def test_create_activation_request_idempotent_returns_existing(db):
    version = _seed_approved_version(db)
    result1 = _dispatch(
        db,
        action_key="create_activation_request",
        version_id=version.id,
        parameters={"requested_by": "operator", "rationale": "first"},
    )
    result2 = _dispatch(
        db,
        action_key="create_activation_request",
        version_id=version.id,
        parameters={"requested_by": "operator", "rationale": "second"},
    )
    assert result1.result_payload["request_id"] == result2.result_payload["request_id"]


def test_create_activation_request_system_state_mutated_is_true(db):
    version = _seed_approved_version(db)
    result = _dispatch(
        db,
        action_key="create_activation_request",
        version_id=version.id,
        parameters={"requested_by": "operator", "rationale": "ready"},
    )
    assert result.system_state_mutated is True
    assert result.activation_performed is False  # request ≠ activation
    assert result.erp_writes_performed is False


# ─── activate_candidate ────────────────────────────────────────────────────

def test_activate_candidate_dispatches_correctly(db):
    version = _seed_fully_eligible_version(db)
    result = _dispatch(
        db,
        action_key="activate_candidate",
        version_id=version.id,
        parameters={"actor": "operator"},
    )
    assert result.status == "completed"
    assert result.dispatch_performed is True
    assert result.result_payload["activated"] is True
    assert result.result_payload["version_status"] == "active"
    assert result.result_payload["is_active"] is True
    assert result.result_payload["is_executed"] is False


def test_activate_candidate_activation_performed_is_true(db):
    version = _seed_fully_eligible_version(db)
    result = _dispatch(
        db,
        action_key="activate_candidate",
        version_id=version.id,
        parameters={"actor": "operator"},
    )
    assert result.activation_performed is True
    assert result.skill_mutated is True


def test_activate_candidate_blocked_without_activation_request(db):
    version = _seed_approved_version(db)  # approve decision + gate, but no activation request
    result = _dispatch(
        db,
        action_key="activate_candidate",
        version_id=version.id,
        parameters={"actor": "operator"},
    )
    assert result.status == "blocked"
    assert result.dispatch_performed is False


def test_activate_candidate_requires_explicit_actor(db):
    version = _seed_fully_eligible_version(db)
    result = _dispatch(
        db,
        action_key="activate_candidate",
        version_id=version.id,
        parameters={},
    )
    assert result.status == "blocked"
    assert result.dispatch_performed is False
    assert result.result_summary == "activate_candidate_requires_actor"


def test_activate_candidate_idempotent_already_active(db):
    version = _seed_fully_eligible_version(db)
    # First activation
    _dispatch(db, action_key="activate_candidate", version_id=version.id,
              parameters={"actor": "operator"})
    # Second call — already active, should return success idempotently
    result = _dispatch(
        db,
        action_key="activate_candidate",
        version_id=version.id,
        parameters={"actor": "operator"},
    )
    assert result.status == "completed"
    assert result.result_payload["activated"] is True


def test_activate_candidate_erp_never_written(db):
    version = _seed_fully_eligible_version(db)
    result = _dispatch(
        db,
        action_key="activate_candidate",
        version_id=version.id,
        parameters={"actor": "operator"},
    )
    assert result.erp_writes_performed is False
    assert result.browser_control_performed is False
    assert result.mcp_execution_performed is False
    assert result.scheduling_performed is False


def test_activate_candidate_is_not_chained_from_create_activation_request(db):
    """Each action requires its own confirmed token — no automatic chaining."""
    version = _seed_approved_version(db)
    # create_activation_request succeeds
    req_result = _dispatch(
        db,
        action_key="create_activation_request",
        version_id=version.id,
        parameters={"requested_by": "operator", "rationale": "ready"},
    )
    assert req_result.status == "completed"
    # activate_candidate still requires its own token + final_gate_evaluated event
    # (which was NOT created by create_activation_request)
    act_result = _dispatch(
        db,
        action_key="activate_candidate",
        version_id=version.id,
        parameters={"actor": "operator"},
    )
    # Blocked: final_gate_evaluated event missing
    assert act_result.status == "blocked"
    assert act_result.dispatch_performed is False


def test_completed_governance_mutation_audit_contains_previous_and_new_state(db):
    version = _seed_approved_version(db)
    result = _dispatch(
        db,
        action_key="create_activation_request",
        version_id=version.id,
        parameters={"requested_by": "operator", "rationale": "ready"},
    )
    audit = get_dispatch_execution_audit(db)
    completed = next(
        entry for entry in audit.entries
        if entry.dispatch_id == result.dispatch_id and entry.event_type == "completed"
    )
    assert completed.detail["previous_state"] == {"activation_request_exists": False}
    assert completed.detail["new_state"]["activation_request_exists"] is True
    assert completed.detail["underlying_artifact_type"] == "activation_request"
    assert completed.detail["underlying_artifact_id"] == result.result_payload["request_id"]
    assert completed.detail["actor"] == "operator"
