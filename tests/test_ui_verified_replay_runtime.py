from __future__ import annotations

import pytest
from erpguard.recording_pipeline.ui_recording_session import UIRecordingSessionService
from erpguard.recording_pipeline.ui_event_capture import UIEventCaptureService
from erpguard.recording_pipeline.ui_recording_normalizer import UIRecordingNormalizerService
from erpguard.recording_pipeline.ui_skill_draft_builder import UISkillDraftBuilder
from erpguard.recording_pipeline.ui_skill_compiler import UISkillCompilerService
from erpguard.recording_pipeline.ui_verified_replay_runtime import UIVerifiedReplayRuntime

_FAKE_ERP_URL = "http://localhost:8000/fake-erp"


def _make_compiled_skill():
    sess = UIRecordingSessionService()
    ev = UIEventCaptureService()
    norm = UIRecordingNormalizerService()
    builder = UISkillDraftBuilder()
    compiler = UISkillCompilerService()

    session = sess.create_session(name="Verified Replay Test", description=None, target_base_url=_FAKE_ERP_URL)
    sid = session.session_id
    ev.capture_event(sid, "navigate", url=_FAKE_ERP_URL + "/sales/orders")
    ev.capture_event(sid, "fill", selector="[data-testid='order-search']", input_value="SO-VALID")
    ev.capture_event(sid, "click", selector="[data-testid='open-order-SO-VALID']")
    ev.capture_event(sid, "click", selector="[data-testid='formula-tab']")
    ev.capture_event(sid, "click", selector="[data-testid='review-formula']")
    raw = ev.list_events(sid)
    recording = norm.normalize(sid, raw)
    draft = builder.build_draft(recording, name="Verified Replay Skill")
    return compiler.compile(draft.draft_id)


def test_verified_replay_clean_pass():
    skill = _make_compiled_skill()
    runtime = UIVerifiedReplayRuntime()
    result = runtime.replay(skill.compiled_skill_id, _FAKE_ERP_URL)
    assert result.replay_id.startswith("ui_replay_")
    assert result.status in ("completed", "completed_with_failures")
    assert result.steps_verification_failed == 0
    assert result.steps_passed > 0


def test_verified_replay_step_results_have_verification_status():
    skill = _make_compiled_skill()
    runtime = UIVerifiedReplayRuntime()
    result = runtime.replay(skill.compiled_skill_id, _FAKE_ERP_URL)
    for step in result.step_results:
        assert step.verification_status in ("passed", "verification_failed")
        assert isinstance(step.checks, dict)


def test_verified_replay_rejects_non_fake_erp():
    skill = _make_compiled_skill()
    runtime = UIVerifiedReplayRuntime()
    with pytest.raises(ValueError, match="Fake ERP"):
        runtime.replay(skill.compiled_skill_id, "http://production-odoo.example.com")


def test_verified_replay_rejects_nonexistent_skill():
    runtime = UIVerifiedReplayRuntime()
    with pytest.raises(ValueError, match="not found"):
        runtime.replay("nonexistent_skill_id", _FAKE_ERP_URL)


def test_verified_replay_step_with_stable_selector_passes_verification():
    skill = _make_compiled_skill()
    runtime = UIVerifiedReplayRuntime()
    result = runtime.replay(skill.compiled_skill_id, _FAKE_ERP_URL)
    fill_steps = [s for s in result.step_results if s.step_type == "fill"]
    for step in fill_steps:
        assert step.verification_status == "passed"
        assert step.checks.get("selector_ambiguity", {}).get("ok") is True


def test_verified_replay_all_steps_have_checks():
    skill = _make_compiled_skill()
    runtime = UIVerifiedReplayRuntime()
    result = runtime.replay(skill.compiled_skill_id, _FAKE_ERP_URL)
    for step in result.step_results:
        assert "page_state" in step.checks
        assert "selector_ambiguity" in step.checks


def test_verified_replay_deterministic_no_llm():
    skill = _make_compiled_skill()
    runtime = UIVerifiedReplayRuntime()
    result = runtime.replay(skill.compiled_skill_id, _FAKE_ERP_URL)
    assert result.steps_passed + result.steps_failed == result.step_count
