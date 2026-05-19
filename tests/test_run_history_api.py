from fastapi.testclient import TestClient

from apps.api.main import app


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


def _build_compiled_skill() -> str:
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


def _run_skill(skill_id: str, order_reference: str):
    response = client.post(f"/v1/skills/{skill_id}/run", json={"inputs": {"order_reference": order_reference}})
    assert response.status_code == 200
    return response.json()


def test_skill_run_history_lists_executions_and_decisions():
    skill_id = _build_compiled_skill()

    allow_run = _run_skill(skill_id, "SO-VALID")
    block_run = _run_skill(skill_id, "SO-FORMULA-MISMATCH")

    response = client.get(f"/v1/skills/{skill_id}/runs")

    assert response.status_code == 200
    body = response.json()
    assert body["skill_id"] == skill_id
    assert len(body["runs"]) == 2
    decisions = {run["decision"] for run in body["runs"]}
    assert decisions == {"allow", "block"}
    assert body["runs"][0]["output_summary"]["policy_id"] == "formula_guard"
    assert body["runs"][0]["output_summary"]["issues_count"] in {0, 1}
    assert body["runs"][0]["estimated_tokens_saved"] == 2000
    assert allow_run["decision"] == "allow"
    assert block_run["decision"] == "block"


def test_skill_run_timeline_returns_ordered_audit_steps_and_proof():
    skill_id = _build_compiled_skill()
    run = _run_skill(skill_id, "SO-FORMULA-MISMATCH")

    response = client.get(f"/v1/skills/{skill_id}/runs/{run['skill_run_id']}/timeline")

    assert response.status_code == 200
    body = response.json()
    assert body["skill_id"] == skill_id
    assert body["skill_run_id"] == run["skill_run_id"]
    assert [step["step_id"] for step in body["timeline"]] == [
        "load_skill",
        "load_order",
        "formula_guard",
        "produce_result",
    ]
    assert body["timeline"][2]["step_type"] == "guard"
    assert body["timeline"][2]["status"] in {"passed", "blocked", "failed"}
    assert body["proof"] == {
        "has_guard_step": True,
        "has_result_step": True,
        "decision_is_auditable": True,
        "llm_replay_not_required": True,
    }


def test_skill_run_history_rejects_unknown_skill_and_run():
    missing_skill = client.get("/v1/skills/missing-skill/runs")
    assert missing_skill.status_code == 404
    assert missing_skill.json()["error"]["code"] == "skill_not_found"

    skill_id = _build_compiled_skill()
    missing_run = client.get(f"/v1/skills/{skill_id}/runs/missing-run/timeline")
    assert missing_run.status_code == 404
    assert missing_run.json()["error"]["code"] == "skill_run_not_found"


def test_health_endpoint_still_works_after_run_history_routes():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}