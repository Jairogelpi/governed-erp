from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from erpguard.db.base import Base
from erpguard.product.oauth_token_vault import OAuthTokenVault, _check_scope_compliance, _TOKEN_STORE


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


_ALLOWED_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"


def _vault(session) -> OAuthTokenVault:
    return OAuthTokenVault(session)


def _token_data(scope: str = _ALLOWED_SCOPE) -> dict:
    return {
        "access_token": "secret_token_never_expose",
        "refresh_token": "secret_refresh_never_expose",
        "token_type": "Bearer",
        "scope": scope,
        "expires_in": 3600,
    }


def test_store_returns_vault_record(session):
    vault = _vault(session)
    record = vault.store(
        profile_id="profile_001",
        connector_id="google_calendar_readonly",
        token_data=_token_data(),
        placeholder_mode=True,
    )
    assert record.vault_ref.startswith("vault_ref_")
    assert record.secret_fingerprint.startswith("sha256:")
    assert record.token_exposed is False
    assert record.secret_redacted is True
    assert record.scope_compliant is True


def test_access_token_never_in_vault_ref(session):
    vault = _vault(session)
    record = vault.store(
        profile_id="profile_002",
        connector_id="google_calendar_readonly",
        token_data=_token_data(),
        placeholder_mode=True,
    )
    assert "secret_token_never_expose" not in record.vault_ref
    assert "secret_token_never_expose" not in record.secret_fingerprint
    assert "secret_token_never_expose" not in str(record.model_dump())


def test_scope_compliant_for_calendar_readonly(session):
    vault = _vault(session)
    record = vault.store(
        profile_id="p1",
        connector_id="google_calendar_readonly",
        token_data=_token_data(_ALLOWED_SCOPE),
        placeholder_mode=True,
    )
    assert record.scope_compliant is True
    assert _ALLOWED_SCOPE in record.scope_granted


def test_scope_non_compliant_for_write_scope(session):
    vault = _vault(session)
    bad_scope = "https://www.googleapis.com/auth/calendar"
    record = vault.store(
        profile_id="p2",
        connector_id="google_calendar_readonly",
        token_data=_token_data(f"{_ALLOWED_SCOPE} {bad_scope}"),
        placeholder_mode=True,
    )
    assert record.scope_compliant is False


def test_retrieve_token_internal_only(session):
    vault = _vault(session)
    token = {"access_token": "raw_token_xyz", "scope": _ALLOWED_SCOPE, "token_type": "Bearer"}
    record = vault.store(
        profile_id="p3",
        connector_id="google_calendar_readonly",
        token_data=token,
        placeholder_mode=True,
    )
    retrieved = vault.retrieve_token(record.vault_ref)
    assert retrieved is not None
    assert retrieved["access_token"] == "raw_token_xyz"


def test_revoke_removes_token_from_store(session):
    vault = _vault(session)
    token = {"access_token": "token_to_revoke", "scope": _ALLOWED_SCOPE, "token_type": "Bearer"}
    record = vault.store(
        profile_id="p4",
        connector_id="google_calendar_readonly",
        token_data=token,
        placeholder_mode=True,
    )
    vault_ref = record.vault_ref
    assert vault.retrieve_token(vault_ref) is not None
    vault.revoke("p4")
    assert vault.retrieve_token(vault_ref) is None


def test_scope_compliance_check_function():
    assert _check_scope_compliance([_ALLOWED_SCOPE]) is True
    assert _check_scope_compliance([]) is False
    assert _check_scope_compliance(["https://www.googleapis.com/auth/calendar"]) is False
    assert _check_scope_compliance(["https://mail.google.com/"]) is False
    assert _check_scope_compliance([_ALLOWED_SCOPE, "https://www.googleapis.com/auth/drive.readonly"]) is False


def test_model_dump_never_exposes_token(session):
    import json
    vault = _vault(session)
    token = {"access_token": "never_expose_this", "scope": _ALLOWED_SCOPE, "token_type": "Bearer"}
    record = vault.store(
        profile_id="p5",
        connector_id="google_calendar_readonly",
        token_data=token,
        placeholder_mode=True,
    )
    dump_str = json.dumps(record.model_dump())
    assert "never_expose_this" not in dump_str
