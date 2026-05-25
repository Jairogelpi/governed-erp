"""Sprint 41 — Operator Console UI smoke tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_demo_loads(client):
    r = client.get("/demo")
    assert r.status_code == 200


def test_sprint41_card_present(client):
    assert "Conversational Operator Console" in client.get("/demo").text


def test_create_session_button(client):
    assert "consoleCreateSession" in client.get("/demo").text


def test_list_intents_button(client):
    assert "consoleListIntents" in client.get("/demo").text


def test_ask_button(client):
    assert "consoleAsk" in client.get("/demo").text


def test_history_button(client):
    assert "consoleHistory" in client.get("/demo").text


def test_console_output_element(client):
    assert "consoleOutput" in client.get("/demo").text


def test_advisory_language_in_sprint41_card(client):
    html = client.get("/demo").text
    assert "Advisory only" in html or "advisory only" in html.lower()


def test_no_execution_language(client):
    html = client.get("/demo").text
    assert "No execution" in html


def test_query_input_present(client):
    assert "consoleQuery" in client.get("/demo").text
