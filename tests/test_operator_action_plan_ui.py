"""Sprint 42 — Action planner demo dashboard UI smoke tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_demo_loads(client):
    assert client.get("/demo").status_code == 200


def test_sprint42_card_present(client):
    html = client.get("/demo").text
    assert "Conversational Action Planner" in html


def test_create_plan_button(client):
    assert "plannerCreatePlan" in client.get("/demo").text


def test_audit_button(client):
    assert "plannerAudit" in client.get("/demo").text


def test_plan_types_button(client):
    assert "plannerPlanTypes" in client.get("/demo").text


def test_goal_input_present(client):
    assert "plannerGoal" in client.get("/demo").text


def test_version_id_input_present(client):
    assert "plannerVersionId" in client.get("/demo").text


def test_planner_output_element(client):
    assert "plannerOutput" in client.get("/demo").text


def test_advisory_language_present(client):
    html = client.get("/demo").text
    assert "Advisory plan only" in html or "advisory" in html.lower()


def test_no_execution_language(client):
    html = client.get("/demo").text
    assert "No execution" in html


def test_button_numbers(client):
    html = client.get("/demo").text
    assert "69." in html
    assert "70." in html
    assert "71." in html
