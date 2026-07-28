from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.adapters.fake import FakeERPAdapter
from erpguard.canonical.enums import SalesOrderState
from erpguard.db.repositories import list_skill_runs
from erpguard.db.session import SessionLocal, init_db


client = TestClient(app)


def _recording_payload() -> dict:
    return {
        "name": "Review order formula from Fake ERP",
        "description": "User demonstrates how to open a sales order and review formula data.",
        "erp_type": "fake",
        "target_base_url": "http://127.0.0.1:8000",
        "actor": {"type": "user", "id": "user_1", "display_name": "Test User"},
    }


def _events() -> list[dict]:
    return [
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


def _compile_skill() -> str:
    recording = client.post("/v1/recordings", json=_recording_payload())
    assert recording.status_code == 200
    recording_id = recording.json()["recording_id"]

    for event in _events():
        response = client.post(f"/v1/recordings/{recording_id}/events", json=event)
        assert response.status_code == 200

    finish = client.post(f"/v1/recordings/{recording_id}/finish")
    assert finish.status_code == 200

    compile_response = client.post(
        f"/v1/recordings/{recording_id}/compile-skill",
        json={
            "name": "Recorded Fake ERP Formula Review",
            "description": "Compiled from a demonstrated Fake ERP formula review flow.",
            "runtime_type": "deterministic_browser",
        },
    )
    assert compile_response.status_code == 200
    return compile_response.json()["skill_id"]


def test_plan_action_returns_safe_plan_and_guard_preview_for_allow_and_block_paths():
    skill_id = _compile_skill()

    init_db()
    session = SessionLocal()
    try:
        before_runs = len(list_skill_runs(session, skill_id))
    finally:
        session.close()

    valid_response = client.post(
        f"/v1/skills/{skill_id}/plan-action",
        json={"inputs": {"order_reference": "SO-VALID"}, "requested_action": "confirm_sales_order"},
    )
    invalid_response = client.post(
        f"/v1/skills/{skill_id}/plan-action",
        json={"inputs": {"order_reference": "SO-FORMULA-MISMATCH"}, "requested_action": "confirm_sales_order"},
    )

    init_db()
    session = SessionLocal()
    try:
        after_runs = len(list_skill_runs(session, skill_id))
    finally:
        session.close()

    assert before_runs == 0
    assert after_runs == 0
    assert valid_response.status_code == 200
    assert invalid_response.status_code == 200

    valid_body = valid_response.json()
    invalid_body = invalid_response.json()

    assert valid_body["skill_id"] == skill_id
    assert valid_body["requested_action"] == "confirm_sales_order"
    assert valid_body["approval_required"] is True
    assert valid_body["risk_level"] == "R3"
    assert valid_body["status"] == "approval_required"
    assert [step["id"] for step in valid_body["plan"]["steps"]] == [
        "load_skill",
        "load_order",
        "run_formula_guard",
        "request_human_approval",
        "blocked_before_real_execution",
    ]
    assert [step["type"] for step in valid_body["plan"]["steps"]] == [
        "load",
        "load",
        "guard",
        "approval",
        "safety_stop",
    ]
    assert valid_body["guard_preview"] == {"decision": "allow", "issues_count": 0}
    assert valid_body["proof"] == {
        "critical_action_detected": True,
        "approval_required": True,
        "guard_checked_before_approval": True,
        "real_erp_write_blocked": True,
        "no_real_execution": True,
    }

    assert invalid_body["guard_preview"] == {"decision": "block", "issues_count": 1}
    assert invalid_body["proof"]["real_erp_write_blocked"] is True
    assert invalid_body["proof"]["no_real_execution"] is True


def test_plan_action_rejects_unknown_action_and_missing_skill():
    skill_id = _compile_skill()

    unknown_action = client.post(
        f"/v1/skills/{skill_id}/plan-action",
        json={"inputs": {"order_reference": "SO-VALID"}, "requested_action": "inspect_access_rules"},
    )
    missing_skill = client.post(
        "/v1/skills/missing-skill/plan-action",
        json={"inputs": {"order_reference": "SO-VALID"}, "requested_action": "confirm_sales_order"},
    )

    assert unknown_action.status_code == 400
    assert unknown_action.json()["error"]["code"] == "unsupported_action"
    assert missing_skill.status_code == 404
    assert missing_skill.json()["error"]["code"] == "skill_not_found"


def test_plan_action_does_not_mutate_fake_erp_state():
    adapter = FakeERPAdapter()
    before = adapter.get_sales_order_by_reference("SO-VALID")

    skill_id = _compile_skill()
    response = client.post(
        f"/v1/skills/{skill_id}/plan-action",
        json={"inputs": {"order_reference": "SO-VALID"}, "requested_action": "confirm_sales_order"},
    )

    after = adapter.get_sales_order_by_reference("SO-VALID")

    assert response.status_code == 200
    assert before.state == SalesOrderState.DRAFT
    assert after.state == SalesOrderState.DRAFT


def test_health_endpoint_still_works_after_plan_action_route():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}