from fastapi.testclient import TestClient

from apps.api.main import app


client = TestClient(app)


def make_recording_payload() -> dict:
    return {
        "name": "Review order formula from Fake ERP",
        "description": "User demonstrates how to open a sales order and review formula data.",
        "erp_type": "fake",
        "target_base_url": "http://127.0.0.1:8000",
        "actor": {
            "type": "user",
            "id": "user_1",
            "display_name": "Test User",
        },
    }


def test_create_recording_session_and_list_recordings():
    response = client.post("/v1/recordings", json=make_recording_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["recording_id"].startswith("recording_")
    assert body["status"] == "recording"

    list_response = client.get("/v1/recordings")

    assert list_response.status_code == 200
    assert any(recording["recording_id"] == body["recording_id"] for recording in list_response.json())


def test_add_event_get_recording_and_finish_session():
    recording = client.post("/v1/recordings", json=make_recording_payload()).json()

    event_response = client.post(
        f"/v1/recordings/{recording['recording_id']}/events",
        json={
            "event_type": "click",
            "url": "http://127.0.0.1:8000/fake-erp/sales/orders",
            "page_title": "Fake ERP Sales Orders",
            "element_role": "link",
            "element_text": "Open SO-FORMULA-MISMATCH",
            "selector": "[data-testid='open-order-SO-FORMULA-MISMATCH']",
            "before_text_snapshot": "Sales Orders...",
            "after_text_snapshot": "Order SO-FORMULA-MISMATCH...",
            "metadata_json": {"source": "manual"},
        },
    )

    assert event_response.status_code == 200
    event_body = event_response.json()
    assert event_body["event_index"] == 1
    assert event_body["metadata_json"]["source"] == "manual"

    second_event_response = client.post(
        f"/v1/recordings/{recording['recording_id']}/events",
        json={
            "event_type": "navigate",
            "url": "http://127.0.0.1:8000/fake-erp/sales/orders/SO-FORMULA-MISMATCH",
            "page_title": "Fake ERP Order SO-FORMULA-MISMATCH",
            "metadata_json": {"source": "manual"},
        },
    )

    assert second_event_response.status_code == 200
    assert second_event_response.json()["event_index"] == 2

    detail = client.get(f"/v1/recordings/{recording['recording_id']}")

    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["event_count"] == 2
    assert [event["event_index"] for event in detail_body["events"]] == [1, 2]

    finish_response = client.post(f"/v1/recordings/{recording['recording_id']}/finish")

    assert finish_response.status_code == 200
    assert finish_response.json()["status"] == "finished"


def test_missing_recording_returns_404():
    response = client.get("/v1/recordings/missing-recording")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "recording_not_found"


def test_health_endpoint_still_works_after_recording_routes():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}