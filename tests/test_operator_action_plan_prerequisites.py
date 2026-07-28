"""Sprint 42 — Action plan prerequisites inspector tests."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from erpguard.db.base import Base
from erpguard.product.operator_action_plan_prerequisites import inspect_prerequisites


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_no_version_id_returns_defaults(db):
    pre = inspect_prerequisites(None, db)
    assert pre.version_exists is False
    assert pre.has_human_decision is False
    assert pre.governance_gaps == []


def test_unknown_version_id_returns_defaults(db):
    pre = inspect_prerequisites("nonexistent-xyz", db)
    assert pre.version_exists is False


def test_returns_prerequisite_state_object(db):
    pre = inspect_prerequisites(None, db)
    assert hasattr(pre, "version_exists")
    assert hasattr(pre, "has_human_decision")
    assert hasattr(pre, "decision_approved")
    assert hasattr(pre, "has_activation_request")
    assert hasattr(pre, "has_run_preview")
    assert hasattr(pre, "is_active")
    assert hasattr(pre, "governance_gaps")
