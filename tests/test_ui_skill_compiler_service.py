from __future__ import annotations

import pytest
from erpguard.recording_pipeline.ui_recording_session import UIRecordingSessionService
from erpguard.recording_pipeline.ui_event_capture import UIEventCaptureService
from erpguard.recording_pipeline.ui_recording_normalizer import UIRecordingNormalizerService
from erpguard.recording_pipeline.ui_skill_draft_builder import UISkillDraftBuilder
from erpguard.recording_pipeline.ui_skill_compiler import UISkillCompilerService


def _make_draft():
    sess_svc = UIRecordingSessionService()
    ev_svc = UIEventCaptureService()
    norm = UIRecordingNormalizerService()
    builder = UISkillDraftBuilder()

    session = sess_svc.create_session(name="Compiler Test", description=None, target_base_url="http://localhost:8000/fake-erp")
    sid = session.session_id

    ev_svc.capture_event(sid, "navigate", url="http://localhost:8000/fake-erp/sales/orders")
    ev_svc.capture_event(sid, "fill", selector="[data-testid='order-search']", input_value="SO-VALID")
    ev_svc.capture_event(sid, "click", selector="[data-testid='open-order-SO-VALID']")

    raw = ev_svc.list_events(sid)
    recording = norm.normalize(sid, raw)
    return builder.build_draft(recording, name="Test Compiled Skill")


def test_compile_creates_compiled_skill():
    draft = _make_draft()
    compiler = UISkillCompilerService()
    result = compiler.compile(draft.draft_id)
    assert result.compiled_skill_id.startswith("ui_skill_")
    assert result.runtime_type == "deterministic_ui"
    assert result.llm_required is False
    assert result.status == "compiled"


def test_compiled_steps_are_deterministic():
    draft = _make_draft()
    compiler = UISkillCompilerService()
    result = compiler.compile(draft.draft_id)
    for step in result.steps:
        assert step["deterministic"] is True
        assert step["llm_required"] is False


def test_compile_nonexistent_draft_raises():
    compiler = UISkillCompilerService()
    with pytest.raises(ValueError, match="not found"):
        compiler.compile("nonexistent_draft_id")


def test_compile_links_to_draft():
    draft = _make_draft()
    compiler = UISkillCompilerService()
    result = compiler.compile(draft.draft_id)
    assert result.draft_id == draft.draft_id
    assert result.session_id == draft.session_id
