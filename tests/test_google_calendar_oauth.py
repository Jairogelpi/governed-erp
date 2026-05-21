from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from erpguard.db.base import Base
from erpguard.db import repositories as repo
from erpguard.product.google_calendar_oauth import GoogleCalendarOAuthService

_ALLOWED_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


def _make_profile(session) -> str:
    """Create a connector auth profile and return its real DB id."""
    row = repo.create_connector_auth_profile(
        session,
        connector_id="google_calendar_readonly",
        display_name="Test OAuth Profile",
        auth_type="oauth",
        requested_scopes_json='["https://www.googleapis.com/auth/calendar.readonly"]',
        credential_ref="vault_ref_placeholder",
        secret_fingerprint="sha256:placeholder",
        created_by_actor_json='{"id": "test"}',
        oauth_readiness_json='{}',
        status="active",
    )
    return row.id


def test_build_authorization_url_placeholder_mode(session):
    profile_id = _make_profile(session)
    svc = GoogleCalendarOAuthService(session)
    result = svc.build_authorization_url(profile_id=profile_id)
    assert result.placeholder_mode is True
    assert result.token_exposed is False
    assert result.secret_redacted is True
    assert result.state_token
    assert "calendar.readonly" in result.authorization_url
    assert _ALLOWED_SCOPE in result.scope_requested


def test_authorization_url_never_exposes_secret(session):
    profile_id = _make_profile(session)
    svc = GoogleCalendarOAuthService(session)
    result = svc.build_authorization_url(profile_id=profile_id)
    assert "placeholder_client_secret" not in result.authorization_url
    assert "GOOGLE_CLIENT_SECRET" not in result.authorization_url


def test_exchange_code_placeholder_succeeds(session):
    profile_id = _make_profile(session)
    svc = GoogleCalendarOAuthService(session)
    auth = svc.build_authorization_url(profile_id=profile_id)
    result = svc.exchange_code(code="any_placeholder_code", state_token=auth.state_token)
    assert result.profile_id == profile_id
    assert result.placeholder_mode is True
    assert result.token_exposed is False
    assert result.secret_redacted is True
    assert result.scope_compliant is True
    assert _ALLOWED_SCOPE in result.scope_granted


def test_exchange_code_updates_profile_status(session):
    profile_id = _make_profile(session)
    svc = GoogleCalendarOAuthService(session)
    auth = svc.build_authorization_url(profile_id=profile_id)
    svc.exchange_code(code="code", state_token=auth.state_token)
    profile = repo.get_connector_auth_profile(session, profile_id)
    assert profile.status == "oauth_authorized"


def test_exchange_invalid_state_raises(session):
    _make_profile(session)
    svc = GoogleCalendarOAuthService(session)
    with pytest.raises(ValueError, match="Invalid"):
        svc.exchange_code(code="code", state_token="nonexistent_state_xyz")


def test_exchange_used_state_raises(session):
    profile_id = _make_profile(session)
    svc = GoogleCalendarOAuthService(session)
    auth = svc.build_authorization_url(profile_id=profile_id)
    svc.exchange_code(code="code1", state_token=auth.state_token)
    with pytest.raises(ValueError):
        svc.exchange_code(code="code2", state_token=auth.state_token)


def test_get_auth_status_not_authorized(session):
    svc = GoogleCalendarOAuthService(session)
    status = svc.get_auth_status("profile_that_never_authorized")
    assert status.authorized is False
    assert status.status == "not_authorized"
    assert status.token_exposed is False


def test_get_auth_status_authorized_after_exchange(session):
    profile_id = _make_profile(session)
    svc = GoogleCalendarOAuthService(session)
    auth = svc.build_authorization_url(profile_id=profile_id)
    svc.exchange_code(code="code", state_token=auth.state_token)
    status = svc.get_auth_status(profile_id)
    assert status.authorized is True
    assert status.scope_compliant is True
    assert status.token_exposed is False


def test_verify_scope_compliant(session):
    profile_id = _make_profile(session)
    svc = GoogleCalendarOAuthService(session)
    auth = svc.build_authorization_url(profile_id=profile_id)
    svc.exchange_code(code="code", state_token=auth.state_token)
    result = svc.verify_scope(profile_id)
    assert result.scope_compliant is True
    assert result.violations == []
    assert _ALLOWED_SCOPE in result.scope_granted
    assert result.token_exposed is False


def test_verify_scope_no_token(session):
    svc = GoogleCalendarOAuthService(session)
    result = svc.verify_scope("profile_without_token")
    assert result.scope_compliant is False
    assert len(result.violations) > 0


def test_revoke_removes_auth(session):
    profile_id = _make_profile(session)
    svc = GoogleCalendarOAuthService(session)
    auth = svc.build_authorization_url(profile_id=profile_id)
    svc.exchange_code(code="code", state_token=auth.state_token)
    result = svc.revoke(profile_id)
    assert result["revoked"] is True
    assert result["token_exposed"] is False
    assert result["secret_redacted"] is True
    status = svc.get_auth_status(profile_id)
    assert status.authorized is False


def test_no_write_operations_available(session):
    svc = GoogleCalendarOAuthService(session)
    assert not hasattr(svc, "create_event")
    assert not hasattr(svc, "update_event")
    assert not hasattr(svc, "delete_event")
    assert not hasattr(svc, "send_email")
