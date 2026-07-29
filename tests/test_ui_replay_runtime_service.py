from __future__ import annotations

import pytest
from erpguard.recording_pipeline.ui_recording_session import UIRecordingSessionService
from erpguard.recording_pipeline.ui_event_capture import UIEventCaptureService
from erpguard.recording_pipeline.ui_recording_normalizer import UIRecordingNormalizerService
from erpguard.recording_pipeline.ui_skill_draft_builder import UISkillDraftBuilder
from erpguard.recording_pipeline.ui_skill_compiler import UISkillCompilerService
from erpguard.recording_pipeline.ui_replay_runtime import UIReplayRuntime

_FAKE_ERP_URL = "http://localhost:8000/fake-erp"


def _make_compiled_skill():
    sess_svc = UIRecordingSessionService()
    ev_svc = UIEventCaptureService()
    norm = UIRecordingNormalizerService()
    builder = UISkillDraftBuilder()
    compiler = UISkillCompilerService()

    session = sess_svc.create_session(name="Replay Test", description=None, target_base_url=_FAKE_ERP_URL)
    sid = session.session_id

    ev_svc.capture_event(sid, "navigate", url=_FAKE_ERP_URL + "/sales/orders")
    ev_svc.capture_event(sid, "fill", selector="[data-testid='order-search']", input_value="SO-VALID")
    ev_svc.capture_event(sid, "click", selector="[data-testid='open-order-SO-VALID']")

    raw = ev_svc.list_events(sid)
    recording = norm.normalize(sid, raw)
    draft = builder.build_draft(recording, name="Replay Test Skill")
    return compiler.compile(draft.draft_id)


def test_replay_completes_successfully():
    skill = _make_compiled_skill()
    runtime = UIReplayRuntime()
    result = runtime.replay(skill.compiled_skill_id, _FAKE_ERP_URL)
    assert result.replay_id.startswith("ui_replay_")
    assert result.status in ("completed", "completed_with_failures")
    assert result.step_count == 3
    assert result.steps_passed == 3
    assert result.steps_failed == 0


def test_replay_step_results_count_matches_steps():
    skill = _make_compiled_skill()
    runtime = UIReplayRuntime()
    result = runtime.replay(skill.compiled_skill_id, _FAKE_ERP_URL)
    assert len(result.step_results) == result.step_count


def test_replay_all_steps_have_before_and_after_state():
    skill = _make_compiled_skill()
    runtime = UIReplayRuntime()
    result = runtime.replay(skill.compiled_skill_id, _FAKE_ERP_URL)
    for step in result.step_results:
        assert isinstance(step.before_state, dict)
        assert isinstance(step.after_state, dict)


def test_replay_rejects_non_fake_erp_url():
    skill = _make_compiled_skill()
    runtime = UIReplayRuntime()
    with pytest.raises(ValueError, match="Fake ERP"):
        runtime.replay(skill.compiled_skill_id, "http://production-odoo.example.com")


def test_replay_rejects_nonexistent_skill():
    runtime = UIReplayRuntime()
    with pytest.raises(ValueError, match="not found"):
        runtime.replay("nonexistent_skill_id", _FAKE_ERP_URL)


def test_replay_navigate_step_updates_url():
    skill = _make_compiled_skill()
    runtime = UIReplayRuntime()
    result = runtime.replay(skill.compiled_skill_id, _FAKE_ERP_URL)
    nav_step = next(s for s in result.step_results if s.step_type == "navigate")
    assert nav_step.status == "passed"
    assert "navigated_to" in nav_step.evidence
