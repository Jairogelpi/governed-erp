from __future__ import annotations

from erpguard.recording_pipeline.ui_recording_session import UIRecordingSessionService
from erpguard.recording_pipeline.ui_event_capture import UIEventCaptureService
from erpguard.recording_pipeline.ui_recording_normalizer import UIRecordingNormalizerService
from erpguard.recording_pipeline.ui_skill_draft_builder import UISkillDraftBuilder
from erpguard.recording_pipeline.ui_skill_compiler import UISkillCompilerService
from erpguard.recording_pipeline.ui_replay_runtime import UIReplayRuntime
from erpguard.recording_pipeline.ui_replay_audit import UIReplayAuditService

_FAKE_ERP_URL = "http://localhost:8000/fake-erp"


def _make_replay():
    sess_svc = UIRecordingSessionService()
    ev_svc = UIEventCaptureService()
    norm = UIRecordingNormalizerService()
    builder = UISkillDraftBuilder()
    compiler = UISkillCompilerService()
    runtime = UIReplayRuntime()

    session = sess_svc.create_session(name="Audit Test", description=None, target_base_url=_FAKE_ERP_URL)
    sid = session.session_id
    ev_svc.capture_event(sid, "navigate", url=_FAKE_ERP_URL + "/sales/orders")
    ev_svc.capture_event(sid, "fill", selector="[data-testid='order-search']", input_value="SO-VALID")
    ev_svc.capture_event(sid, "click", selector="[data-testid='open-order-SO-VALID']")

    raw = ev_svc.list_events(sid)
    recording = norm.normalize(sid, raw)
    draft = builder.build_draft(recording, name="Audit Test Skill")
    skill = compiler.compile(draft.draft_id)
    return runtime.replay(skill.compiled_skill_id, _FAKE_ERP_URL)


def test_get_audit_returns_result():
    replay = _make_replay()
    svc = UIReplayAuditService()
    audit = svc.get_audit(replay.replay_id)
    assert audit is not None
    assert audit.replay_id == replay.replay_id


def test_audit_entries_match_step_count():
    replay = _make_replay()
    svc = UIReplayAuditService()
    audit = svc.get_audit(replay.replay_id)
    assert len(audit.entries) == replay.step_count


def test_audit_entry_has_before_after_state():
    replay = _make_replay()
    svc = UIReplayAuditService()
    audit = svc.get_audit(replay.replay_id)
    for entry in audit.entries:
        assert isinstance(entry.before_state, dict)
        assert isinstance(entry.after_state, dict)
        assert isinstance(entry.evidence, dict)


def test_get_audit_nonexistent_replay_returns_none():
    svc = UIReplayAuditService()
    assert svc.get_audit("nonexistent_replay_id") is None
