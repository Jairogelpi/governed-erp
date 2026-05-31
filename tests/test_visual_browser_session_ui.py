"""UI tests for Sprint 80 - visual browser session shell."""

from fastapi.testclient import TestClient

from apps.api.main import app


def test_ui_exposes_visual_browser_session_shell_section():
    client = TestClient(app)

    response = client.get("/demo")

    assert response.status_code == 200
    assert b"Visual Browser Session Shell" in response.content
    assert b"Sprint 80 creates a safe visual browser session shell only" in response.content
    assert b"visualBrowserTargetUrl" in response.content
    assert b"visualBrowserErpHint" in response.content
    assert b"visualBrowserCreate" in response.content
    assert b"visualBrowserAudit" in response.content
