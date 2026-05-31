"""API tests for Sprint 81 - visual observation snapshots."""

from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.visual_browser_session import VisualBrowserSessionInput, VisualBrowserSessionService
from test_visual_observation_snapshot import _payload


def test_api_create_get_list_and_audit_observation_snapshot():
    init_db()
    db = SessionLocal()
    session = VisualBrowserSessionService(db).create_session(
        VisualBrowserSessionInput(created_by="operator_1", target_url="https://my-erp.example.com")
    )
    db.close()
    client = TestClient(app)

    created = client.post(
        f"/v1/operator-console/visual-browser/session/{session.visual_session_id}/observation-snapshot",
        json=_payload(),
    )
    payload = created.json()
    retrieved = client.get(
        f"/v1/operator-console/visual-browser/observation-snapshot/{payload['observation_id']}"
    )
    listed = client.get("/v1/operator-console/visual-browser/observation-snapshots")
    audit = client.get("/v1/operator-console/visual-browser/observation-audit")

    assert created.status_code == 200
    assert payload["status"] == "created"
    assert retrieved.status_code == 200
    assert retrieved.json()["observation_id"] == payload["observation_id"]
    assert listed.status_code == 200
    assert any(item["observation_id"] == payload["observation_id"] for item in listed.json()["snapshots"])
    assert audit.status_code == 200
    assert any(event["event_type"] == "visual_observation_snapshot_created" for event in audit.json()["events"])
