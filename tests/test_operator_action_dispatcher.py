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
from erpguard.db.repositories import create_action_plan_step_token
from erpguard.product.operator_action_dispatch_execution_audit import get_dispatch_execution_audit
from erpguard.product.operator_action_dispatch_result import get_dispatch_result
from erpguard.product.operator_action_dispatcher import (
    DispatchRequest,
    dispatch_confirmed_read_only_action,
)
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


def _make_token(db, *, endpoint_hint: str, method_hint: str = "GET", confirmed: bool = False, expired: bool = False):
    token_id = f"tok_{uuid.uuid4().hex[:16]}"
    expires_at = datetime.now(timezone.utc) - timedelta(minutes=1) if expired else datetime.now(timezone.utc) + timedelta(minutes=10)
    create_action_plan_step_token(
        db,
        token_id=token_id,
        plan_id="aplan_dispatch",
        step_number=1,
        step_title="Dispatch read-only action",
        endpoint_hint=endpoint_hint,
        method_hint=method_hint,
        severity="blocking",
        risk_level="medium",
        risk_summary="manual confirmation required",
        expires_at=expires_at,
    )
    if confirmed:
        confirm_token(token_id, db)
    return token_id


def _dispatch(db, **overrides):
    request = DispatchRequest(
        plan_id="aplan_dispatch",
        step_number=1,
        action_key=overrides.get("action_key", "search_skills"),
        endpoint_hint=overrides.get("endpoint_hint", "POST /malicious/should/not/run"),
        method_hint=overrides.get("method_hint", "POST"),
        token_id=overrides["token_id"],
        version_id=overrides.get("version_id"),
        parameters=overrides.get("parameters", {"query": "formula"}),
    )
    return dispatch_confirmed_read_only_action(request, session=db)


def test_read_only_action_with_confirmed_token_dispatches_correctly(db):
    _make_version(db, name="formula-search-target")
    token_id = _make_token(db, endpoint_hint="GET /v1/agent-builder/discovery/search", confirmed=True)
    result = _dispatch(db, token_id=token_id)
    assert result.status == "completed"
    assert result.dispatch_performed is True
    assert result.token_confirmed is True
    assert result.eligibility_passed is True
    assert result.is_advisory_only is False


def test_missing_token_blocks(db):
    result = _dispatch(db, token_id="tok_missing")
    assert result.status == "blocked"
    assert result.dispatch_performed is False
    assert "Token was not found" in result.result_summary


def test_pending_token_blocks(db):
    token_id = _make_token(db, endpoint_hint="GET /v1/agent-builder/discovery/search", confirmed=False)
    result = _dispatch(db, token_id=token_id)
    assert result.status == "blocked"
    assert "pending" in result.result_summary


def test_expired_token_blocks(db):
    token_id = _make_token(db, endpoint_hint="GET /v1/agent-builder/discovery/search", expired=True)
    result = _dispatch(db, token_id=token_id)
    assert result.status == "blocked"
    assert "expired" in result.result_summary


def test_unknown_action_key_blocks(db):
    token_id = _make_token(db, endpoint_hint="GET /v1/agent-builder/discovery/search", confirmed=True)
    result = _dispatch(db, token_id=token_id, action_key="unknown_action")
    assert result.status == "blocked"
    assert result.action_key == "unknown_action"


def test_activate_candidate_without_version_id_blocks(db):
    token_id = _make_token(db, endpoint_hint="POST /v1/agent-candidate-activation/ver_1", method_hint="POST", confirmed=True)
    result = _dispatch(db, token_id=token_id, action_key="activate_candidate")
    assert result.status == "blocked"
    assert result.dispatch_performed is False
    assert "not allowed in Sprint 45" not in result.result_summary


def test_record_human_decision_without_version_id_blocks(db):
    token_id = _make_token(db, endpoint_hint="POST /v1/agent-candidate-decision/ver_1", method_hint="POST", confirmed=True)
    result = _dispatch(db, token_id=token_id, action_key="record_human_decision")
    assert result.status == "blocked"
    assert result.dispatch_performed is False


def test_create_activation_request_without_version_id_blocks(db):
    token_id = _make_token(db, endpoint_hint="POST /v1/agent-candidate-activation-request/ver_1", method_hint="POST", confirmed=True)
    result = _dispatch(db, token_id=token_id, action_key="create_activation_request")
    assert result.status == "blocked"
    assert result.dispatch_performed is False


def test_endpoint_hint_never_executed_as_http(db):
    _make_version(db, name="formula-search-target")
    token_id = _make_token(db, endpoint_hint="POST /totally/arbitrary/http/path", method_hint="POST", confirmed=True)
    result = _dispatch(
        db,
        token_id=token_id,
        action_key="search_skills",
        endpoint_hint="POST https://evil.example/api/run",
        method_hint="POST",
    )
    assert result.status == "completed"
    audit = get_dispatch_execution_audit(db)
    assert any(entry.detail.get("endpoint_hint_executed") is False for entry in audit.entries)


def test_handler_selected_only_by_action_key(db):
    version = _make_version(db)
    token_id = _make_token(db, endpoint_hint="GET /v1/agent-builder/discovery/search", confirmed=True)
    result = _dispatch(
        db,
        token_id=token_id,
        action_key="inspect_lifecycle",
        endpoint_hint="GET /v1/agent-builder/discovery/search",
        parameters={"query": "ignored", "version_id": version.id},
        version_id=version.id,
    )
    assert result.status == "completed"
    assert result.result_payload["version_id"] == version.id


def test_dispatch_result_is_persisted(db):
    _make_version(db, name="formula-search-target")
    token_id = _make_token(db, endpoint_hint="GET /v1/agent-builder/discovery/search", confirmed=True)
    result = _dispatch(db, token_id=token_id)
    loaded = get_dispatch_result(result.dispatch_id, db)
    assert loaded is not None
    assert loaded.dispatch_id == result.dispatch_id


def test_execution_audit_is_persisted(db):
    _make_version(db, name="formula-search-target")
    token_id = _make_token(db, endpoint_hint="GET /v1/agent-builder/discovery/search", confirmed=True)
    _dispatch(db, token_id=token_id)
    audit = get_dispatch_execution_audit(db)
    assert audit.event_count >= 2
    assert audit.entries[0].action_key == "search_skills"


def test_no_erp_writes_browser_mcp_llm_or_mutation(db):
    _make_version(db, name="formula-search-target")
    token_id = _make_token(db, endpoint_hint="GET /v1/agent-builder/discovery/search", confirmed=True)
    result = _dispatch(db, token_id=token_id)
    assert result.erp_writes_performed is False
    assert result.browser_control_performed is False
    assert result.mcp_execution_performed is False
    assert result.llm_runtime_used is False
    assert result.system_state_mutated is False
    assert result.skill_mutated is False
    assert result.activation_performed is False
    assert result.scheduling_performed is False
