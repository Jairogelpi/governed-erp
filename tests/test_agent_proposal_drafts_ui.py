from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def test_demo_contains_conversational_agent_builder_section():
    r = client.get("/demo")
    assert r.status_code == 200
    assert "Conversational Agent Builder" in r.text


def test_demo_contains_draft_preview_control():
    r = client.get("/demo")
    assert "cabDraftPreview" in r.text
    assert "draft-preview" in r.text


def test_demo_contains_create_draft_control():
    r = client.get("/demo")
    assert "cabCreateDraft" in r.text
    assert "create-draft" in r.text


def test_demo_contains_draft_link_control():
    r = client.get("/demo")
    assert "cabDraftLink" in r.text
    assert "draft-link" in r.text


def test_demo_advisory_only_messaging():
    r = client.get("/demo")
    assert "Advisory only" in r.text or "advisory" in r.text.lower()


def test_demo_source_proposal_endpoint_referenced():
    r = client.get("/demo")
    assert "source-proposal" in r.text or "draft-link" in r.text
