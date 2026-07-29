from __future__ import annotations

from erpguard.recording_pipeline.ui_recording_session import UIRecordingSessionService
from erpguard.recording_pipeline.ui_event_capture import UIEventCaptureService
from erpguard.recording_pipeline.ui_recording_normalizer import UIRecordingNormalizerService
from erpguard.recording_pipeline.ui_skill_draft_builder import UISkillDraftBuilder
from erpguard.recording_pipeline.ui_skill_compiler import UISkillCompilerService
from erpguard.recording_pipeline.ui_verified_replay_runtime import UIVerifiedReplayRuntime
from erpguard.recording_pipeline.ui_robust_replay_report import UIRobustReplayReportService

_FAKE_ERP_URL = "http://localhost:8000/fake-erp"


def _make_verified_replay():
    sess = UIRecordingSessionService()
    ev = UIEventCaptureService()
    norm = UIRecordingNormalizerService()
    builder = UISkillDraftBuilder()
    compiler = UISkillCompilerService()
    runtime = UIVerifiedReplayRuntime()

    session = sess.create_session(name="Robust Report Test", description=None, target_base_url=_FAKE_ERP_URL)
    sid = session.session_id
    ev.capture_event(sid, "navigate", url=_FAKE_ERP_URL + "/sales/orders")
    ev.capture_event(sid, "fill", selector="[data-testid='order-search']", input_value="SO-VALID")
    ev.capture_event(sid, "click", selector="[data-testid='open-order-SO-VALID']")
    raw = ev.list_events(sid)
    recording = norm.normalize(sid, raw)
    draft = builder.build_draft(recording, name="Robust Report Skill")
    skill = compiler.compile(draft.draft_id)
    return runtime.replay(skill.compiled_skill_id, _FAKE_ERP_URL)


def test_robust_report_returns_result():
    replay = _make_verified_replay()
    svc = UIRobustReplayReportService()
    report = svc.get_report(replay.replay_id)
    assert report is not None
    assert report.replay_id == replay.replay_id


def test_robust_report_is_deterministic_no_llm():
    replay = _make_verified_replay()
    svc = UIRobustReplayReportService()
    report = svc.get_report(replay.replay_id)
    assert report.llm_used_at_replay is False
    assert report.deterministic is True


def test_robust_report_has_verifications():
    replay = _make_verified_replay()
    svc = UIRobustReplayReportService()
    report = svc.get_report(replay.replay_id)
    assert report.verification_count > 0
    assert len(report.verifications) > 0


def test_robust_report_clean_replay_has_no_failures():
    replay = _make_verified_replay()
    svc = UIRobustReplayReportService()
    report = svc.get_report(replay.replay_id)
    assert report.failure_count == 0
    assert report.recovery_actions_required is False


def test_robust_report_nonexistent_returns_none():
    svc = UIRobustReplayReportService()
    assert svc.get_report("nonexistent_replay_id") is None


def test_get_verifications_returns_list():
    replay = _make_verified_replay()
    svc = UIRobustReplayReportService()
    verifs = svc.get_verifications(replay.replay_id)
    assert verifs is not None
    assert len(verifs) == replay.step_count


def test_get_failures_returns_empty_for_clean_replay():
    replay = _make_verified_replay()
    svc = UIRobustReplayReportService()
    failures = svc.get_failures(replay.replay_id)
    assert failures is not None
    assert failures == []


def test_get_verifications_nonexistent_returns_none():
    svc = UIRobustReplayReportService()
    assert svc.get_verifications("nonexistent_replay_id") is None
