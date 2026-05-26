"""Sprint 45 — Confirmed read-only action dispatcher demo dashboard UI smoke tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _html(client):
    return client.get("/demo").text


def test_sprint45_card_present(client):
    assert "Confirmed Read-Only Action Dispatcher" in _html(client)


def test_sprint45_banner_present(client):
    assert "Sprint 45 dispatches only internal read-only handlers." in _html(client)


def test_sprint45_fields_present(client):
    html = _html(client)
    for marker in (
        "dispatchExecutePlanId",
        "dispatchExecuteStepNumber",
        "dispatchExecuteActionKey",
        "dispatchExecuteEndpointHint",
        "dispatchExecuteMethodHint",
        "dispatchExecuteTokenId",
        "dispatchExecuteVersionId",
        "dispatchExecuteParameters",
        "dispatchExecuteOutput",
    ):
        assert marker in html


def test_sprint45_buttons_present(client):
    html = _html(client)
    assert "Dispatch read-only action" in html
    assert "Get dispatch result" in html
    assert "Dispatch execution audit" in html
