"""Sprint 31 — UI/demo dashboard smoke tests for the bridge card."""
from apps.api.routes.demo_dashboard import router


def _get_html() -> str:
    for route in router.routes:
        if hasattr(route, "path") and route.path == "/demo":
            break
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    r = client.get("/demo")
    assert r.status_code == 200
    return r.text


def test_bridge_card_present():
    html = _get_html()
    assert "Draft Review Bridge" in html


def test_bridge_button_eligibility():
    html = _get_html()
    assert 'id="bridgeEligibility"' in html


def test_bridge_button_clarification_gate():
    html = _get_html()
    assert 'id="bridgeClarificationGate"' in html


def test_bridge_button_review():
    html = _get_html()
    assert 'id="bridgeReview"' in html


def test_bridge_button_validate():
    html = _get_html()
    assert 'id="bridgeValidate"' in html


def test_bridge_button_compile_plan():
    html = _get_html()
    assert 'id="bridgeCompilePlan"' in html


def test_bridge_button_report():
    html = _get_html()
    assert 'id="bridgeReport"' in html


def test_bridge_button_audit():
    html = _get_html()
    assert 'id="bridgeAudit"' in html


def test_bridge_output_element():
    html = _get_html()
    assert 'id="bridgeOutput"' in html


def test_bridge_safety_note_in_card():
    html = _get_html()
    assert "dry_run_only" in html or "No execution" in html
    assert "No activation" in html or "advisory only" in html.lower()
