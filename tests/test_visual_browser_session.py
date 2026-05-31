"""Sprint 80 - visual browser session shell service tests."""

from __future__ import annotations

from erpguard.db.session import SessionLocal, init_db
from erpguard.product.visual_browser_session import (
    VisualBrowserSessionInput,
    VisualBrowserSessionService,
)


UNSAFE_FLAGS = [
    "credential_capture_allowed",
    "llm_can_see_credentials",
    "automatic_clicks_allowed",
    "automatic_form_submit_allowed",
    "dom_observation_allowed",
    "screen_capture_allowed",
    "workflow_recording_allowed",
    "browser_launched",
    "action_execution_allowed",
    "external_http_performed",
    "browser_control_performed",
    "mcp_execution_performed",
    "scheduler_used",
]


def _service():
    init_db()
    session = SessionLocal()
    return session, VisualBrowserSessionService(session)


def test_creates_visual_session_shell_with_all_unsafe_flags_false():
    session, service = _service()
    try:
        result = service.create_session(
            VisualBrowserSessionInput(
                created_by="operator_1",
                target_url="https://my-erp.example.com",
                intended_erp_hint="odoo",
                workspace_mode="observe_only",
            )
        )

        assert result.visual_session_id.startswith("vbs_")
        assert result.status in {"created", "waiting_for_user_login"}
        assert result.target_host == "my-erp.example.com"
        for flag in UNSAFE_FLAGS:
            assert getattr(result, flag) is False
    finally:
        session.close()


def test_allows_empty_target_url_for_later_user_navigation():
    session, service = _service()
    try:
        result = service.create_session(
            VisualBrowserSessionInput(created_by="operator_1", target_url="")
        )

        assert result.status == "created"
        assert result.target_host == ""
        assert result.blocking_reasons == []
    finally:
        session.close()


def test_allows_localhost_http_for_tests_without_external_work():
    session, service = _service()
    try:
        result = service.create_session(
            VisualBrowserSessionInput(
                created_by="operator_1",
                target_url="http://localhost:8069",
            )
        )

        assert result.status == "created"
        assert result.target_host == "localhost"
        assert result.external_http_performed is False
        assert result.browser_launched is False
    finally:
        session.close()


def test_blocks_missing_actor():
    session, service = _service()
    try:
        result = service.create_session(VisualBrowserSessionInput(created_by=""))

        assert result.status == "blocked"
        assert result.blocking_reasons == ["actor_required"]
    finally:
        session.close()


def test_blocks_invalid_workspace_mode():
    session, service = _service()
    try:
        result = service.create_session(
            VisualBrowserSessionInput(created_by="operator_1", workspace_mode="execute")
        )

        assert result.status == "blocked"
        assert result.blocking_reasons == ["workspace_mode_not_allowed"]
    finally:
        session.close()


def test_blocks_unsafe_url_scheme_and_external_http():
    session, service = _service()
    try:
        ftp_result = service.create_session(
            VisualBrowserSessionInput(
                created_by="operator_1",
                target_url="ftp://erp.example.com",
            )
        )
        http_result = service.create_session(
            VisualBrowserSessionInput(
                created_by="operator_1",
                target_url="http://erp.example.com",
            )
        )

        assert ftp_result.blocking_reasons == ["unsafe_url_scheme"]
        assert http_result.blocking_reasons == ["unsafe_url_scheme"]
        assert ftp_result.external_http_performed is False
        assert http_result.browser_control_performed is False
    finally:
        session.close()


def test_blocks_attempts_to_enable_forbidden_capabilities():
    session, service = _service()
    try:
        credential = service.create_session(
            VisualBrowserSessionInput(
                created_by="operator_1",
                credential_capture_allowed=True,
            )
        )
        clicks = service.create_session(
            VisualBrowserSessionInput(
                created_by="operator_1",
                automatic_clicks_allowed=True,
            )
        )
        actions = service.create_session(
            VisualBrowserSessionInput(
                created_by="operator_1",
                action_execution_allowed=True,
            )
        )

        assert credential.blocking_reasons == ["credential_capture_forbidden"]
        assert clicks.blocking_reasons == ["automatic_clicks_forbidden"]
        assert actions.blocking_reasons == ["action_execution_forbidden"]
        for result in (credential, clicks, actions):
            for flag in UNSAFE_FLAGS:
                assert getattr(result, flag) is False
    finally:
        session.close()


def test_revoke_marks_session_revoked_and_keeps_unsafe_flags_false():
    session, service = _service()
    try:
        created = service.create_session(VisualBrowserSessionInput(created_by="operator_1"))
        revoked = service.revoke_session(created.visual_session_id, actor="operator_1")

        assert revoked is not None
        assert revoked.status == "revoked"
        for flag in UNSAFE_FLAGS:
            assert getattr(revoked, flag) is False
    finally:
        session.close()
