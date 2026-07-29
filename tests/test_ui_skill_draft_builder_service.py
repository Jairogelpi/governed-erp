from __future__ import annotations

from erpguard.recording_pipeline.ui_recording_normalizer import UIRecordingNormalizerService
from erpguard.recording_pipeline.ui_skill_draft_builder import UISkillDraftBuilder
from erpguard.recording_pipeline.ui_recording_session import UIRecordingSessionService
from erpguard.recording_pipeline.ui_event_capture import UIEventCaptureService


def _make_recording_with_events():
    sess_svc = UIRecordingSessionService()
    ev_svc = UIEventCaptureService()
    norm = UIRecordingNormalizerService()

    session = sess_svc.create_session(
        name="Draft Builder Test",
        description=None,
        target_base_url="http://localhost:8000/fake-erp",
    )
    sid = session.session_id

    ev_svc.capture_event(sid, "navigate", url="http://localhost:8000/fake-erp/sales/orders")
    ev_svc.capture_event(sid, "fill", selector="[data-testid='order-search']", input_value="SO-VALID")
    ev_svc.capture_event(sid, "click", selector="[data-testid='open-order-SO-VALID']")
    ev_svc.capture_event(sid, "click", selector="[data-testid='formula-tab']")
    ev_svc.capture_event(sid, "click", selector="[data-testid='review-formula']")

    raw = ev_svc.list_events(sid)
    recording = norm.normalize(sid, raw)
    return recording


def test_build_draft_creates_steps():
    recording = _make_recording_with_events()
    builder = UISkillDraftBuilder()
    draft = builder.build_draft(recording, name="Formula Review Skill")
    assert draft.draft_id.startswith("ui_draft_")
    assert len(draft.steps) == 5
    assert draft.steps[0]["type"] == "navigate"
    assert draft.steps[1]["type"] == "fill"


def test_build_draft_extracts_selector_map():
    recording = _make_recording_with_events()
    builder = UISkillDraftBuilder()
    draft = builder.build_draft(recording, name="Formula Review Skill")
    assert "step_1" in draft.selector_map
    assert draft.selector_map["step_1"] == "[data-testid='order-search']"


def test_build_draft_infers_formula_guard():
    recording = _make_recording_with_events()
    builder = UISkillDraftBuilder()
    draft = builder.build_draft(recording, name="Formula Review Skill")
    assert "formula_guard" in draft.guard_names


def test_build_draft_status_is_draft():
    recording = _make_recording_with_events()
    builder = UISkillDraftBuilder()
    draft = builder.build_draft(recording, name="My Skill", description="Test")
    assert draft.status == "draft"
    assert draft.description == "Test"
