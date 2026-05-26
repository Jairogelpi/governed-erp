"""Sprint 43 — Step token demo dashboard UI smoke tests."""
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


def test_sprint43_card_present(client):
    assert "Action Plan Step Preview" in _html(client)


def test_preview_button(client):
    assert "tokenPreview" in _html(client)


def test_status_button(client):
    assert "tokenStatus" in _html(client)


def test_confirm_button(client):
    assert "tokenConfirm" in _html(client)


def test_plan_id_input(client):
    assert "tokenPlanId" in _html(client)


def test_token_id_input(client):
    assert "tokenId" in _html(client)


def test_output_element(client):
    assert "tokenOutput" in _html(client)


def test_advisory_language(client):
    assert "Advisory only" in _html(client) or "advisory" in _html(client).lower()


def test_no_execution_language(client):
    assert "No execution" in _html(client)


def test_button_numbers(client):
    html = _html(client)
    assert "72." in html
    assert "73." in html
    assert "74." in html
