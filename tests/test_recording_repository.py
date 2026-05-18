import json

from erpguard.db.repositories import (
    add_recording_event,
    create_recording_session,
    finish_recording_session,
    get_recording_session,
    list_recording_events,
    list_recording_sessions,
)
from erpguard.db.session import SessionLocal, init_db


def test_recording_repository_roundtrip_and_event_order():
    init_db()
    session = SessionLocal()
    try:
        recording = create_recording_session(
            session=session,
            name="Repo Recording",
            description="Repository level recording test",
            erp_type="fake",
            target_base_url="http://127.0.0.1:8000",
            created_by_actor_json=json.dumps({"type": "user", "id": "user_1"}),
        )

        assert get_recording_session(session, recording.id).name == "Repo Recording"
        assert any(row.id == recording.id for row in list_recording_sessions(session))

        first_event = add_recording_event(
            session=session,
            recording_session_id=recording.id,
            event_type="click",
            url="http://127.0.0.1:8000/fake-erp/sales/orders",
            page_title="Fake ERP Sales Orders",
            metadata_json=json.dumps({"step": 1}),
        )
        second_event = add_recording_event(
            session=session,
            recording_session_id=recording.id,
            event_type="navigate",
            url="http://127.0.0.1:8000/fake-erp/sales/orders/SO-VALID",
            page_title="Fake ERP Order SO-VALID",
            metadata_json=json.dumps({"step": 2}),
        )

        events = list_recording_events(session, recording.id)
        assert [event.event_index for event in events] == [1, 2]
        assert json.loads(events[0].metadata_json)["step"] == 1
        assert json.loads(events[1].metadata_json)["step"] == 2
        assert first_event.event_index == 1
        assert second_event.event_index == 2

        finished = finish_recording_session(session, recording.id)
        assert finished.status == "finished"
    finally:
        session.close()