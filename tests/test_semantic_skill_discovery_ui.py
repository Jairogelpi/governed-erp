"""Sprint 40 — Semantic Skill Discovery UI smoke tests."""
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


def test_sprint40_card_present(client):
    html = client.get("/demo").text
    assert "Semantic Skill Discovery" in html


def test_discovery_search_button(client):
    assert "discoverySearch" in client.get("/demo").text


def test_discovery_similar_button(client):
    assert "discoverySimilar" in client.get("/demo").text


def test_discovery_lifecycle_button(client):
    assert "discoveryLifecycle" in client.get("/demo").text


def test_discovery_gaps_button(client):
    assert "discoveryGaps" in client.get("/demo").text


def test_discovery_recs_button(client):
    assert "discoveryRecs" in client.get("/demo").text


def test_discovery_reuse_button(client):
    assert "discoveryReuse" in client.get("/demo").text


def test_discovery_output_element(client):
    assert "discoveryOutput" in client.get("/demo").text


def test_advisory_only_language(client):
    html = client.get("/demo").text
    assert "advisory" in html.lower() or "Advisory" in html
