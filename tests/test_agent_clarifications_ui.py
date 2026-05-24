from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def test_demo_contains_clarification_loop_section():
    r = client.get("/demo")
    assert r.status_code == 200
    assert "Clarification Loop" in r.text


def test_demo_contains_clarifications_button():
    r = client.get("/demo")
    assert "cabClarifications" in r.text


def test_demo_contains_submit_answer_button():
    r = client.get("/demo")
    assert "cabSubmitAnswer" in r.text


def test_demo_contains_confirm_mapping_button():
    r = client.get("/demo")
    assert "cabConfirmMapping" in r.text


def test_demo_contains_reject_mapping_button():
    r = client.get("/demo")
    assert "cabRejectMapping" in r.text


def test_demo_contains_clarification_status_button():
    r = client.get("/demo")
    assert "cabClarificationStatus" in r.text


def test_demo_contains_refresh_draft_button():
    r = client.get("/demo")
    assert "cabRefreshDraft" in r.text


def test_demo_contains_clarification_audit_button():
    r = client.get("/demo")
    assert "cabClarificationAudit" in r.text


def test_demo_clarification_output_element():
    r = client.get("/demo")
    assert "cabClarificationOutput" in r.text


def test_demo_advisory_only_note():
    r = client.get("/demo")
    assert "dry_run_only" in r.text or "advisory" in r.text.lower()
