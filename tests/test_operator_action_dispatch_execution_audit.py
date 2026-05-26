from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from erpguard.db.base import Base
from erpguard.product.operator_action_dispatch_execution_audit import (
    get_dispatch_execution_audit,
    persist_dispatch_execution_event,
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


def test_execution_audit_persists_and_lists(db):
    persist_dispatch_execution_event(
        dispatch_id="disp_audit_test",
        action_key="search_skills",
        event_type="completed",
        status="completed",
        handler_type="internal_read_only",
        endpoint_hint="POST /never/executed",
        method_hint="POST",
        token_id="tok_123",
        version_id="ver_123",
        detail={"handler_selected_by": "action_key", "endpoint_hint_executed": False},
        session=db,
    )
    result = get_dispatch_execution_audit(db)
    assert result.event_count == 1
    assert result.entries[0].dispatch_id == "disp_audit_test"
    assert result.entries[0].detail["endpoint_hint_executed"] is False
    assert result.is_advisory_only is True
