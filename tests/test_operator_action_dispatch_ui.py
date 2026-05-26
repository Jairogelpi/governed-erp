"""Sprint 44 — Dispatch eligibility demo dashboard UI smoke tests."""
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


def test_demo_loads(client):
    assert client.get("/demo").status_code == 200


def test_sprint44_card_present(client):
    assert "Action Dispatch Eligibility Registry" in _html(client)


def test_registry_button(client):
    assert "dispatchRegistry" in _html(client)


def test_eligibility_button(client):
    assert "dispatchEligibility" in _html(client)


def test_audit_button(client):
    assert "dispatchAudit" in _html(client)


def test_endpoint_input(client):
    assert "dispatchEndpoint" in _html(client)


def test_token_input(client):
    assert "dispatchTokenId" in _html(client)


def test_output_element(client):
    assert "dispatchOutput" in _html(client)


def test_no_execution_language(client):
    assert "no action is executed" in _html(client).lower() or "No execution" in _html(client)


def test_advisory_language(client):
    assert "Advisory only" in _html(client)


def test_button_numbers(client):
    html = _html(client)
    assert "75." in html
    assert "76." in html
    assert "77." in html
