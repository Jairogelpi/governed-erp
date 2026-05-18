from fastapi.testclient import TestClient

from apps.api.main import app


client = TestClient(app)


def _human_recording_payload() -> dict:
    return {
        "name": "Human Recorded Fake ERP Formula Review",
        "description": "Controlled human recording from the demo surface.",
        "erp_type": "fake",
        "target_base_url": "http://127.0.0.1:8000",
        "actor": {"type": "user", "id": "demo_user", "display_name": "Demo User"},
    }


def _recording_events_payload() -> list[dict]:
    return [
        {
            "event_type": "navigate",
            "url": "http://127.0.0.1:8000/fake-erp/sales/orders?recording_id=recording_test",
            "page_title": "Fake ERP Sales Orders",
            "before_text_snapshot": "",
            "after_text_snapshot": "Fake ERP Sales Orders",
            "metadata_json": {"source": "human_recording_v0.2"},
        },
        {
            "event_type": "fill",
            "url": "http://127.0.0.1:8000/fake-erp/sales/orders?recording_id=recording_test",
            "page_title": "Fake ERP Sales Orders",
            "element_role": "searchbox",
            "selector": "[data-testid='order-search']",
            "element_text": "SO-FORMULA-MISMATCH",
            "input_value": "SO-FORMULA-MISMATCH",
            "before_text_snapshot": "Fake ERP Sales Orders",
            "after_text_snapshot": "Fake ERP Sales Orders",
            "metadata_json": {"source": "human_recording_v0.2"},
        },
        {
            "event_type": "click",
            "url": "http://127.0.0.1:8000/fake-erp/sales/orders/SO-FORMULA-MISMATCH?recording_id=recording_test",
            "page_title": "Fake ERP Order SO-FORMULA-MISMATCH",
            "element_role": "link",
            "selector": "[data-testid='open-order-SO-FORMULA-MISMATCH']",
            "element_text": "Open SO-FORMULA-MISMATCH",
            "before_text_snapshot": "Fake ERP Sales Orders",
            "after_text_snapshot": "Fake ERP Sales Orders",
            "metadata_json": {"source": "human_recording_v0.2"},
        },
        {
            "event_type": "click",
            "url": "http://127.0.0.1:8000/fake-erp/sales/orders/SO-FORMULA-MISMATCH/formula?recording_id=recording_test",
            "page_title": "Fake ERP Formula SO-FORMULA-MISMATCH",
            "element_role": "link",
            "selector": "[data-testid='formula-tab']",
            "element_text": "Formula tab",
            "before_text_snapshot": "Fake ERP Order SO-FORMULA-MISMATCH",
            "after_text_snapshot": "Fake ERP Order SO-FORMULA-MISMATCH",
            "metadata_json": {"source": "human_recording_v0.2"},
        },
        {
            "event_type": "click",
            "url": "http://127.0.0.1:8000/fake-erp/sales/orders/SO-FORMULA-MISMATCH/formula?recording_id=recording_test",
            "page_title": "Fake ERP Formula SO-FORMULA-MISMATCH",
            "element_role": "button",
            "selector": "[data-testid='review-formula']",
            "element_text": "Review formula",
            "before_text_snapshot": "Formula Tab - SO-FORMULA-MISMATCH",
            "after_text_snapshot": "Formula Tab - SO-FORMULA-MISMATCH",
            "metadata_json": {"source": "human_recording_v0.2"},
        },
    ]


def _create_finished_recording_with_events(events: list[dict]) -> str:
    create_response = client.post("/v1/recordings", json=_human_recording_payload())
    assert create_response.status_code == 200
    recording_id = create_response.json()["recording_id"]

    for event in events:
      response = client.post(f"/v1/recordings/{recording_id}/events", json=event)
      assert response.status_code == 200

    finish_response = client.post(f"/v1/recordings/{recording_id}/finish")
    assert finish_response.status_code == 200
    assert finish_response.json()["status"] == "finished"
    return recording_id


def _compile_recording(recording_id: str):
    return client.post(
        f"/v1/recordings/{recording_id}/compile-skill",
        json={
            "name": "Human Recorded Fake ERP Formula Review",
            "description": "Compiled from controlled human recording.",
            "runtime_type": "deterministic_browser",
        },
    )


def test_demo_dashboard_exposes_human_recording_controls():
    response = client.get("/demo")

    assert response.status_code == 200
    html = response.text
    assert "Human Recording v0.2" in html
    assert "Start human recording" in html
    assert "Open Fake ERP sales orders" in html
    assert "Finish recording" in html
    assert "Compile recording" in html
    assert "Run compiled skill" in html


def test_demo_dashboard_exposes_human_recording_preview_and_readiness():
    response = client.get("/demo")

    assert response.status_code == 200
    html = response.text
    assert "Recording Preview" in html
    assert "compiler readiness" in html
    assert "humanPreview" in html
    assert "ordered events" in html
    assert "selectors captured" in html


def test_human_recording_pipeline_compiles_and_runs_allow_block():
    recording_id = _create_finished_recording_with_events(_recording_events_payload())

    detail_response = client.get(f"/v1/recordings/{recording_id}")
    assert detail_response.status_code == 200
    detail_body = detail_response.json()
    assert [event["event_index"] for event in detail_body["events"]] == [1, 2, 3, 4, 5]

    compile_response = _compile_recording(recording_id)
    assert compile_response.status_code == 200
    compile_body = compile_response.json()
    skill_id = compile_body["skill_id"]

    valid_run = client.post(f"/v1/skills/{skill_id}/run", json={"inputs": {"order_reference": "SO-VALID"}})
    assert valid_run.status_code == 200
    assert valid_run.json()["decision"] == "allow"
    assert valid_run.json()["token_economics"]["repeated_execution_token_cost"] == 0

    invalid_run = client.post(
        f"/v1/skills/{skill_id}/run",
        json={"inputs": {"order_reference": "SO-FORMULA-MISMATCH"}},
    )
    assert invalid_run.status_code == 200
    assert invalid_run.json()["decision"] == "block"
    assert invalid_run.json()["output"]["issues"]


def test_human_recording_compile_without_search_event_reports_diagnostic():
    events = [event for event in _recording_events_payload() if event.get("selector") != "[data-testid='order-search']"]
    recording_id = _create_finished_recording_with_events(events)

    response = _compile_recording(recording_id)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsupported_recording_flow"
    assert response.json()["error"]["message"] == "missing_order_search_event"


def test_human_recording_compile_without_formula_tab_reports_diagnostic():
    events = [event for event in _recording_events_payload() if event.get("selector") != "[data-testid='formula-tab']"]
    recording_id = _create_finished_recording_with_events(events)

    response = _compile_recording(recording_id)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsupported_recording_flow"
    assert response.json()["error"]["message"] == "missing_formula_tab_event"


def test_human_recording_compile_without_review_formula_reports_diagnostic():
    events = [event for event in _recording_events_payload() if event.get("selector") != "[data-testid='review-formula']"]
    recording_id = _create_finished_recording_with_events(events)

    response = _compile_recording(recording_id)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsupported_recording_flow"
    assert response.json()["error"]["message"] == "missing_review_formula_event"


def test_health_endpoint_still_works_after_human_recording_routes():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
