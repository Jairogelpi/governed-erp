from fastapi.testclient import TestClient

from apps.api.main import app
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


def test_approval_decision_simulation_approve_and_reject_paths_do_not_create_runs():
    skill_id = _compile_skill()

    init_db()
    session = SessionLocal()
    try:
        before_runs = len(list_skill_runs(session, skill_id))
    finally:
        session.close()

    approve_response = client.post(
        f"/v1/skills/{skill_id}/simulate-approval-decision",
        json={
            "inputs": {"order_reference": "SO-VALID"},
            "requested_action": "confirm_sales_order",
            "decision": "approve",
            "approver": {"type": "user", "id": "demo_approver", "display_name": "Demo Approver"},
            "reason": "Formula preview is clean.",
        },
    )
    block_response = client.post(
        f"/v1/skills/{skill_id}/simulate-approval-decision",
        json={
            "inputs": {"order_reference": "SO-FORMULA-MISMATCH"},
            "requested_action": "confirm_sales_order",
            "decision": "approve",
            "approver": {"type": "user", "id": "demo_approver", "display_name": "Demo Approver"},
            "reason": "Formula preview is clean.",
        },
    )
    reject_response = client.post(
        f"/v1/skills/{skill_id}/simulate-approval-decision",
        json={
            "inputs": {"order_reference": "SO-FORMULA-MISMATCH"},
            "requested_action": "confirm_sales_order",
            "decision": "reject",
            "approver": {"type": "user", "id": "demo_approver", "display_name": "Demo Approver"},
            "reason": "Formula Guard blocks this order.",
        },
    )

    init_db()
    session = SessionLocal()
    try:
        after_runs = len(list_skill_runs(session, skill_id))
    finally:
        session.close()

    assert before_runs == 0
    assert after_runs == 0
    assert approve_response.status_code == 200
    assert block_response.status_code == 200
    assert reject_response.status_code == 200

    approve_body = approve_response.json()
    block_body = block_response.json()
    reject_body = reject_response.json()

    assert approve_body["approval_decision"] == "approved"
    assert approve_body["status"] == "approved_but_not_executed"
    assert approve_body["simulated_execution"] == {
        "would_execute": True,
        "did_execute": False,
        "blocked_reason": "real_erp_write_blocked_by_mvp_scope",
    }
    assert approve_body["proof"] == {
        "approval_decision_recorded": True,
        "approval_required": True,
        "guard_checked_before_decision": True,
        "real_erp_write_blocked": True,
        "no_real_execution": True,
        "human_decision_simulated": True,
    }

    assert block_body["approval_decision"] == "approved"
    assert block_body["status"] == "blocked_before_execution"
    assert block_body["simulated_execution"] == {
        "would_execute": False,
        "did_execute": False,
        "blocked_reason": "guard_blocked",
    }

    assert reject_body["approval_decision"] == "rejected"
    assert reject_body["status"] == "rejected_before_execution"
    assert reject_body["simulated_execution"] == {
        "would_execute": False,
        "did_execute": False,
        "blocked_reason": "rejected_by_human",
    }


def test_approval_decision_simulation_rejects_unsupported_decision_action_and_missing_skill():
    skill_id = _compile_skill()

    unsupported_decision = client.post(
        f"/v1/skills/{skill_id}/simulate-approval-decision",
        json={
            "inputs": {"order_reference": "SO-VALID"},
            "requested_action": "confirm_sales_order",
            "decision": "maybe",
            "approver": {"type": "user", "id": "demo_approver", "display_name": "Demo Approver"},
            "reason": "Not a valid approval choice.",
        },
    )
    unsupported_action = client.post(
        f"/v1/skills/{skill_id}/simulate-approval-decision",
        json={
            "inputs": {"order_reference": "SO-VALID"},
            "requested_action": "inspect_access_rules",
            "decision": "approve",
            "approver": {"type": "user", "id": "demo_approver", "display_name": "Demo Approver"},
            "reason": "Unsupported action.",
        },
    )
    missing_skill = client.post(
        "/v1/skills/missing-skill/simulate-approval-decision",
        json={
            "inputs": {"order_reference": "SO-VALID"},
            "requested_action": "confirm_sales_order",
            "decision": "approve",
            "approver": {"type": "user", "id": "demo_approver", "display_name": "Demo Approver"},
            "reason": "Formula preview is clean.",
        },
    )

    assert unsupported_decision.status_code == 400
    assert unsupported_decision.json()["error"]["code"] == "unsupported_decision"
    assert unsupported_action.status_code == 400
    assert unsupported_action.json()["error"]["code"] == "unsupported_action"
    assert missing_skill.status_code == 404
    assert missing_skill.json()["error"]["code"] == "skill_not_found"


def test_health_endpoint_still_works_after_approval_decision_simulation_route():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}