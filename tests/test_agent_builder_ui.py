from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import app


client = TestClient(app)


def test_demo_contains_safe_agent_builder_section():
    html = client.get("/demo").text

    assert "Safe Agent Builder" in html
    assert "This builder creates reviewed drafts only" in html
    assert "agentBuilderSessionOutput" in html
    assert "agentBuilderPreviewOutput" in html
    assert "Save as automation draft" in html
    assert "/v1/agent-builder/sessions" in html
    assert "/v1/agent-builder/step-library" in html


def test_demo_agent_builder_safety_copy_keeps_no_goals_visible():
    html = client.get("/demo").text

    assert "does not execute free-form agents" in html
    assert "enable new ERP writes" in html
    assert "review / compile / approval" in html
