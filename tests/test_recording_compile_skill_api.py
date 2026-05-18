from fastapi.testclient import TestClient

from apps.api.main import app


client = TestClient(app)


def make_recording_payload() -> dict:
    return {
        "name": "Review order formula from Fake ERP",
        "description": "User demonstrates how to open a sales order and review formula data.",
        "erp_type": "fake",
        "target_base_url": "http://127.0.0.1:8000",
        "actor": {"type": "user", "id": "user_1", "display_name": "Test User"},
    }


def add_formula_flow_events(recording_id: str):
    client.post(
        f"/v1/recordings/{recording_id}/events",
        json={
            "event_type": "navigate",
            "url": "http://127.0.0.1:8000/fake-erp/sales/orders",
            "page_title": "Fake ERP Sales Orders",
            "before_text_snapshot": "",
            "after_text_snapshot": "Sales Orders...",
        },
    )
    client.post(
        f"/v1/recordings/{recording_id}/events",
        json={
            "event_type": "fill",
            "url": "http://127.0.0.1:8000/fake-erp/sales/orders",
            "page_title": "Fake ERP Sales Orders",
            "element_role": "searchbox",
            "element_text": "SO-FORMULA-MISMATCH",
            "selector": "[data-testid='order-search']",
            "input_value": "SO-FORMULA-MISMATCH",
            "before_text_snapshot": "Sales Orders...",
            "after_text_snapshot": "Sales Orders...",
        },
    )
    client.post(
        f"/v1/recordings/{recording_id}/events",
        json={
            "event_type": "click",
            "url": "http://127.0.0.1:8000/fake-erp/sales/orders",
            "page_title": "Fake ERP Sales Orders",
            "element_role": "link",
            "element_text": "Open SO-FORMULA-MISMATCH",
            "selector": "[data-testid='open-order-SO-FORMULA-MISMATCH']",
            "before_text_snapshot": "Sales Orders...",
            "after_text_snapshot": "Order SO-FORMULA-MISMATCH...",
        },
    )
    client.post(
        f"/v1/recordings/{recording_id}/events",
        json={
            "event_type": "click",
            "url": "http://127.0.0.1:8000/fake-erp/sales/orders/SO-FORMULA-MISMATCH",
            "page_title": "Fake ERP Order SO-FORMULA-MISMATCH",
            "element_role": "link",
            "element_text": "Formula tab",
            "selector": "[data-testid='formula-tab']",
            "before_text_snapshot": "Order SO-FORMULA-MISMATCH...",
            "after_text_snapshot": "Order SO-FORMULA-MISMATCH...",
        },
    )
    client.post(
        f"/v1/recordings/{recording_id}/events",
        json={
            "event_type": "click",
            "url": "http://127.0.0.1:8000/fake-erp/sales/orders/SO-FORMULA-MISMATCH/formula",
            "page_title": "Fake ERP Formula SO-FORMULA-MISMATCH",
            "element_role": "button",
            "element_text": "Review formula",
            "selector": "[data-testid='review-formula']",
            "before_text_snapshot": "Formula status...",
            "after_text_snapshot": "Formula status...",
        },
    )


def test_compile_finished_recording_into_skill_and_run_it():
    recording = client.post("/v1/recordings", json=make_recording_payload()).json()
    add_formula_flow_events(recording["recording_id"])
    finish = client.post(f"/v1/recordings/{recording['recording_id']}/finish")
    assert finish.status_code == 200

    compile_response = client.post(
        f"/v1/recordings/{recording['recording_id']}/compile-skill",
        json={
            "name": "Recorded Fake ERP Formula Review",
            "description": "Compiled from a demonstrated Fake ERP formula review flow.",
            "runtime_type": "deterministic_browser",
        },
    )

    assert compile_response.status_code == 200
    body = compile_response.json()
    assert body["recording_id"] == recording["recording_id"]
    assert body["runtime_type"] == "deterministic_browser"
    assert body["llm_required_for_repeated_runs"] is False
    assert body["skill_package"]["skill_id"] == "recorded_fake_erp_formula_review"

    get_skill_response = client.get(f"/v1/skills/{body['skill_id']}")
    assert get_skill_response.status_code == 200
    assert get_skill_response.json()["skill_package"]["compiled_from_recording_id"] == recording["recording_id"]

    allow_run = client.post(f"/v1/skills/{body['skill_id']}/run", json={"inputs": {"order_reference": "SO-VALID"}})
    assert allow_run.status_code == 200
    assert allow_run.json()["decision"] == "allow"

    block_run = client.post(
        f"/v1/skills/{body['skill_id']}/run",
        json={"inputs": {"order_reference": "SO-FORMULA-MISMATCH"}},
    )
    assert block_run.status_code == 200
    assert block_run.json()["decision"] == "block"


def test_compile_rejects_unfinished_recording_and_empty_recording():
    unfinished = client.post("/v1/recordings", json=make_recording_payload()).json()
    response = client.post(
        f"/v1/recordings/{unfinished['recording_id']}/compile-skill",
        json={
            "name": "Recorded Fake ERP Formula Review",
            "description": "Compiled from a demonstrated Fake ERP formula review flow.",
            "runtime_type": "deterministic_browser",
        },
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "recording_not_finished"

    empty = client.post("/v1/recordings", json=make_recording_payload()).json()
    client.post(f"/v1/recordings/{empty['recording_id']}/finish")
    empty_response = client.post(
        f"/v1/recordings/{empty['recording_id']}/compile-skill",
        json={
            "name": "Recorded Fake ERP Formula Review",
            "description": "Compiled from a demonstrated Fake ERP formula review flow.",
            "runtime_type": "deterministic_browser",
        },
    )
    assert empty_response.status_code == 400
    assert empty_response.json()["error"]["code"] in {"recording_has_no_events", "unsupported_recording_flow"}


def test_health_endpoint_still_works_after_compile_route():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
