import json

from erpguard.compiler.recording_to_skill import compile_recording_to_skill_package
from erpguard.db.repositories import add_recording_event, create_recording_session, finish_recording_session, list_recording_events
from erpguard.db.session import SessionLocal, init_db


def test_compiler_generalizes_order_reference_and_builds_expected_workflow():
    init_db()
    session = SessionLocal()
    try:
        recording = create_recording_session(
            session=session,
            name="Compile recording",
            description="Finished recording for compiler test",
            erp_type="fake",
            target_base_url="http://127.0.0.1:8000",
            created_by_actor_json=json.dumps({"type": "user", "id": "user_1", "display_name": "Test User"}),
        )
        add_recording_event(
            session=session,
            recording_session_id=recording.id,
            event_type="navigate",
            url="http://127.0.0.1:8000/fake-erp/sales/orders",
            page_title="Fake ERP Sales Orders",
            before_text_snapshot="",
            after_text_snapshot="Sales Orders...",
        )
        add_recording_event(
            session=session,
            recording_session_id=recording.id,
            event_type="fill",
            url="http://127.0.0.1:8000/fake-erp/sales/orders",
            page_title="Fake ERP Sales Orders",
            element_role="searchbox",
            element_text="SO-FORMULA-MISMATCH",
            selector="[data-testid='order-search']",
            input_value="SO-FORMULA-MISMATCH",
            before_text_snapshot="Sales Orders...",
            after_text_snapshot="Sales Orders...",
        )
        add_recording_event(
            session=session,
            recording_session_id=recording.id,
            event_type="click",
            url="http://127.0.0.1:8000/fake-erp/sales/orders",
            page_title="Fake ERP Sales Orders",
            element_role="link",
            element_text="Open SO-FORMULA-MISMATCH",
            selector="[data-testid='open-order-SO-FORMULA-MISMATCH']",
            before_text_snapshot="Sales Orders...",
            after_text_snapshot="Order SO-FORMULA-MISMATCH...",
        )
        add_recording_event(
            session=session,
            recording_session_id=recording.id,
            event_type="click",
            url="http://127.0.0.1:8000/fake-erp/sales/orders/SO-FORMULA-MISMATCH",
            page_title="Fake ERP Order SO-FORMULA-MISMATCH",
            element_role="link",
            element_text="Formula tab",
            selector="[data-testid='formula-tab']",
            before_text_snapshot="Order SO-FORMULA-MISMATCH...",
            after_text_snapshot="Order SO-FORMULA-MISMATCH...",
        )
        add_recording_event(
            session=session,
            recording_session_id=recording.id,
            event_type="click",
            url="http://127.0.0.1:8000/fake-erp/sales/orders/SO-FORMULA-MISMATCH/formula",
            page_title="Fake ERP Formula SO-FORMULA-MISMATCH",
            element_role="button",
            element_text="Review formula",
            selector="[data-testid='review-formula']",
            before_text_snapshot="Formula status...",
            after_text_snapshot="Formula status...",
        )
        finish_recording_session(session, recording.id)

        events = list_recording_events(session, recording.id)
        package = compile_recording_to_skill_package(recording, events)

        assert package["skill_id"] == "recorded_fake_erp_formula_review"
        assert package["inputs"] == {"order_reference": "string"}
        assert package["llm_required_for_repeated_runs"] is False
        assert package["compiled_from_recording_id"] == recording.id
        assert package["workflow"][1]["value"] == "{{order_reference}}"
        assert package["workflow"][2]["selector_template"] == "[data-testid='open-order-{{order_reference}}']"
        assert [step["id"] for step in package["workflow"]] == [
            "open_orders",
            "search_order",
            "open_order",
            "open_formula",
            "review_formula",
            "run_formula_guard",
        ]
    finally:
        session.close()
