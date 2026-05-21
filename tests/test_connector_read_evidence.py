from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from erpguard.db.base import Base
from erpguard.product.connector_read_evidence import ConnectorReadEvidenceService


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


def test_store_and_retrieve_evidence(session):
    svc = ConnectorReadEvidenceService(session)
    ev = svc.store(
        auth_profile_id="auth_profile_test_001",
        connector_id="google_calendar_readonly",
        operation="read_upcoming_events",
        fixture_mode=True,
        record_count=5,
        redacted_fields_count=12,
        result_summary={"total_count": 5, "fixture_mode": True},
    )
    assert ev.id.startswith("cre_")
    assert ev.auth_profile_id == "auth_profile_test_001"
    assert ev.read_only is True
    assert ev.fixture_mode is True
    assert ev.record_count == 5
    assert ev.redacted_fields_count == 12
    assert ev.policy_passed is True


def test_get_evidence_by_id(session):
    svc = ConnectorReadEvidenceService(session)
    created = svc.store(
        auth_profile_id="profile_001",
        connector_id="google_calendar_readonly",
        operation="read_calendars",
        fixture_mode=True,
        record_count=2,
        redacted_fields_count=0,
        result_summary={},
    )
    retrieved = svc.get(created.id)
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.operation == "read_calendars"


def test_get_nonexistent_returns_none(session):
    svc = ConnectorReadEvidenceService(session)
    assert svc.get("cre_does_not_exist") is None


def test_list_for_profile(session):
    svc = ConnectorReadEvidenceService(session)
    for op in ("read_calendars", "read_upcoming_events"):
        svc.store(
            auth_profile_id="profile_multi",
            connector_id="google_calendar_readonly",
            operation=op,
            fixture_mode=True,
            record_count=3,
            redacted_fields_count=1,
            result_summary={},
        )
    items = svc.list_for_profile("profile_multi")
    assert len(items) == 2
    assert all(e.auth_profile_id == "profile_multi" for e in items)


def test_evidence_read_only_flag(session):
    svc = ConnectorReadEvidenceService(session)
    ev = svc.store(
        auth_profile_id="profile_x",
        connector_id="google_calendar_readonly",
        operation="read_upcoming_events",
        fixture_mode=True,
        record_count=1,
        redacted_fields_count=0,
        result_summary={},
    )
    assert ev.read_only is True


def test_model_dump_has_required_keys(session):
    svc = ConnectorReadEvidenceService(session)
    ev = svc.store(
        auth_profile_id="p1",
        connector_id="google_calendar_readonly",
        operation="read_calendars",
        fixture_mode=True,
        record_count=0,
        redacted_fields_count=0,
        result_summary={},
    )
    d = ev.model_dump()
    for key in ("id", "auth_profile_id", "connector_id", "operation", "fixture_mode",
                "record_count", "redacted_fields_count", "policy_passed", "read_only", "created_at"):
        assert key in d
