from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.db.repositories import create_skill
from erpguard.db.session import SessionLocal, init_db


client = TestClient(app)


def _make_recording_payload() -> dict:
    return {
        "name": "Review order formula from Fake ERP",
        "description": "User demonstrates how to open a sales order and review formula data.",
        "erp_type": "fake",
        "target_base_url": "http://127.0.0.1:8000",
        "actor": {"type": "user", "id": "user_1", "display_name": "Test User"},
    }


def _record_formula_flow() -> dict:
    recording = client.post("/v1/recordings", json=_make_recording_payload())
    assert recording.status_code == 200
    recording_id = recording.json()["recording_id"]

    events = [
        {
            "event_type": "navigate",
            "url": "http://127.0.0.1:8000/fake-erp/sales/orders",
            "page_title": "Fake ERP Sales Orders",
            "before_text_snapshot": "",
            "after_text_snapshot": "Sales Orders...",
        },
        {
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
        {
            "event_type": "click",
            "url": "http://127.0.0.1:8000/fake-erp/sales/orders",
            "page_title": "Fake ERP Sales Orders",
            "element_role": "link",
            "element_text": "Open SO-FORMULA-MISMATCH",
            "selector": "[data-testid='open-order-SO-FORMULA-MISMATCH']",
            "before_text_snapshot": "Sales Orders...",
            "after_text_snapshot": "Order SO-FORMULA-MISMATCH...",
        },
        {
            "event_type": "click",
            "url": "http://127.0.0.1:8000/fake-erp/sales/orders/SO-FORMULA-MISMATCH",
            "page_title": "Fake ERP Order SO-FORMULA-MISMATCH",
            "element_role": "link",
            "element_text": "Formula tab",
            "selector": "[data-testid='formula-tab']",
            "before_text_snapshot": "Order SO-FORMULA-MISMATCH...",
            "after_text_snapshot": "Order SO-FORMULA-MISMATCH...",
        },
        {
            "event_type": "click",
            "url": "http://127.0.0.1:8000/fake-erp/sales/orders/SO-FORMULA-MISMATCH/formula",
            "page_title": "Fake ERP Formula SO-FORMULA-MISMATCH",
            "element_role": "button",
            "element_text": "Review formula",
            "selector": "[data-testid='review-formula']",
            "before_text_snapshot": "Formula status...",
            "after_text_snapshot": "Formula status...",
        },
    ]

    for event in events:
        event_response = client.post(f"/v1/recordings/{recording_id}/events", json=event)
        assert event_response.status_code == 200

    finish_response = client.post(f"/v1/recordings/{recording_id}/finish")
    assert finish_response.status_code == 200

    compile_response = client.post(
        f"/v1/recordings/{recording_id}/compile-skill",
        json={
            "name": "Recorded Fake ERP Formula Review",
            "description": "Compiled from a demonstrated Fake ERP formula review flow.",
            "runtime_type": "deterministic_browser",
        },
    )
    assert compile_response.status_code == 200
    return compile_response.json()


def test_inspect_skill_returns_expected_workflow_and_safety_summary():
    compiled = _record_formula_flow()

    response = client.get(f"/v1/skills/{compiled['skill_id']}/inspect")

    assert response.status_code == 200
    body = response.json()
    assert body["skill_id"] == compiled["skill_id"]
    assert body["name"] == compiled["name"]
    assert body["version_id"] == compiled["version_id"]
    assert body["runtime_type"] == "deterministic_browser"
    assert body["llm_required_for_repeated_runs"] is False
    assert body["inputs"] == {"order_reference": "string"}
    assert body["guards"] == ["formula_guard"]
    assert [step["id"] for step in body["workflow_steps"]] == [
        "open_orders",
        "search_order",
        "open_order",
        "open_formula",
        "review_formula",
        "run_formula_guard",
    ]
    assert body["workflow_steps"][-1]["guard"] == "formula_guard"
    assert body["compiled_from_recording_id"] == compiled["recording_id"]
    assert body["safety_summary"] == {
        "has_guards": True,
        "guard_count": 1,
        "has_write_actions": False,
        "requires_llm_for_replay": False,
    }


def test_inspect_missing_skill_returns_controlled_error():
    response = client.get("/v1/skills/missing-skill/inspect")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "skill_not_found"


def test_inspect_skill_without_version_returns_controlled_error():
    init_db()
    session = SessionLocal()
    try:
        skill = create_skill(session, "Inspector Orphan Skill", "No version yet")
    finally:
        session.close()

    response = client.get(f"/v1/skills/{skill.id}/inspect")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "skill_version_not_found"