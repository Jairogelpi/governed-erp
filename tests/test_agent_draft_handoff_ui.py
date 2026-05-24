"""Sprint 32 — UI/demo dashboard smoke tests for the approval handoff card."""
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


def test_handoff_card_present():
    html = _get_html()
    assert "Approval Handoff" in html


def test_handoff_button_proof_plan():
    html = _get_html()
    assert 'id="handoffProofPlan"' in html


def test_handoff_button_evidence():
    html = _get_html()
    assert 'id="handoffEvidence"' in html


def test_handoff_button_readiness():
    html = _get_html()
    assert 'id="handoffReadiness"' in html


def test_handoff_button_packet():
    html = _get_html()
    assert 'id="handoffPacket"' in html


def test_handoff_button_audit():
    html = _get_html()
    assert 'id="handoffAudit"' in html


def test_handoff_output_element():
    html = _get_html()
    assert 'id="handoffOutput"' in html


def test_handoff_safety_note_in_card():
    html = _get_html()
    assert "No execution" in html
    assert "No activation" in html or "advisory only" in html.lower()


def test_handoff_sprint_label():
    html = _get_html()
    assert "Sprint 32" in html
