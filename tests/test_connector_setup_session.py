from __future__ import annotations

from erpguard.db.session import SessionLocal, init_db
from erpguard.product.connector_setup_session import (
    ConnectorSetupEnvironmentType,
    ConnectorSetupInput,
    ConnectorSetupService,
    normalize_erp_url_host,
)


def _service():
    init_db()
    session = SessionLocal()
    return session, ConnectorSetupService(session)


def test_creates_setup_session_from_https_erp_url():
    session, service = _service()
    try:
        result = service.create_session(
            ConnectorSetupInput(
                connector_name="Odoo Production",
                erp_url="https://miempresa.odoo.com",
                environment_type=ConnectorSetupEnvironmentType.PRODUCTION,
                submitted_by="operator_1",
            )
        )

        assert result.session_id.startswith("csess_")
        assert result.status == "awaiting_credentials"
        assert result.credential_mode == "not_provided"
        assert result.erp_url_host == "miempresa.odoo.com"
        assert result.requires_credentials is True
        assert result.can_fingerprint is False
        assert result.can_activate_read_only is False
        assert result.will_connect is False
        assert result.external_http_performed is False
        assert result.credentials_stored is False
        assert result.raw_credentials_seen is False
    finally:
        session.close()


def test_normalizes_erp_url_host_from_login_path():
    host, blocking_reasons = normalize_erp_url_host("https://miempresa.odoo.com/web/login")

    assert host == "miempresa.odoo.com"
    assert blocking_reasons == []


def test_invalid_url_blocks_without_external_work():
    session, service = _service()
    try:
        result = service.create_session(
            ConnectorSetupInput(
                connector_name="Broken ERP",
                erp_url="not-a-url",
                environment_type=ConnectorSetupEnvironmentType.UNKNOWN,
                submitted_by="operator_1",
            )
        )

        assert result.status == "blocked"
        assert "invalid_erp_url" in result.blocking_reasons
        _assert_no_external_work(result)
    finally:
        session.close()


def test_external_http_url_blocks_as_unsafe():
    session, service = _service()
    try:
        result = service.create_session(
            ConnectorSetupInput(
                connector_name="Unsafe ERP",
                erp_url="http://erp.example.com",
                environment_type=ConnectorSetupEnvironmentType.PRODUCTION,
                submitted_by="operator_1",
            )
        )

        assert result.status == "blocked"
        assert result.erp_url_host == "erp.example.com"
        assert "unsafe_url_scheme" in result.blocking_reasons
        _assert_no_external_work(result)
    finally:
        session.close()


def test_localhost_http_is_allowed_for_tests_but_still_does_not_connect():
    session, service = _service()
    try:
        result = service.create_session(
            ConnectorSetupInput(
                connector_name="Local Test ERP",
                erp_url="http://localhost:8069",
                environment_type=ConnectorSetupEnvironmentType.SANDBOX,
                submitted_by="operator_1",
            )
        )

        assert result.status == "awaiting_credentials"
        assert result.erp_url_host == "localhost"
        _assert_no_external_work(result)
    finally:
        session.close()


def _assert_no_external_work(result):
    assert result.will_connect is False
    assert result.external_http_performed is False
    assert result.login_attempted is False
    assert result.fingerprint_performed is False
    assert result.schema_inspection_performed is False
    assert result.capability_generation_performed is False
    assert result.read_only_activation_performed is False
    assert result.erp_write_performed is False
