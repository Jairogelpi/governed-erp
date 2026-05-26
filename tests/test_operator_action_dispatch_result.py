from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from erpguard.db.base import Base
from erpguard.product.operator_action_dispatch_result import (
    get_dispatch_result,
    persist_dispatch_result,
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


def test_dispatch_result_persists_and_loads(db):
    saved = persist_dispatch_result(
        dispatch_id="disp_result_test",
        action_key="search_skills",
        status="completed",
        dispatch_performed=True,
        handler_type="internal_read_only",
        token_confirmed=True,
        eligibility_passed=True,
        result_payload={"query": "formula", "total_found": 1},
        result_summary="Search finished.",
        blocking_reasons=[],
        endpoint_hint="POST /never/executed",
        method_hint="POST",
        token_id="tok_123",
        version_id="ver_123",
        parameters={"query": "formula"},
        audit_recorded=True,
        session=db,
    )
    loaded = get_dispatch_result(saved.dispatch_id, db)
    assert loaded is not None
    assert loaded.dispatch_id == "disp_result_test"
    assert loaded.result_payload["total_found"] == 1
    assert loaded.browser_control_performed is False
    assert loaded.is_advisory_only is False
