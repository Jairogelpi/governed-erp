from __future__ import annotations

from erpguard.recording_pipeline.ui_recording_session import UIRecordingSessionService
from erpguard.recording_pipeline.ui_event_capture import UIEventCaptureService
from erpguard.recording_pipeline.ui_recording_normalizer import UIRecordingNormalizerService
from erpguard.recording_pipeline.ui_skill_draft_builder import UISkillDraftBuilder
from erpguard.recording_pipeline.ui_skill_compiler import UISkillCompilerService
from erpguard.recording_pipeline.ui_replay_runtime import UIReplayRuntime
from erpguard.recording_pipeline.ui_replay_report import UIReplayReportService

_FAKE_ERP_URL = "http://localhost:8000/fake-erp"


def _make_replay():
    sess_svc = UIRecordingSessionService()
    ev_svc = UIEventCaptureService()
    norm = UIRecordingNormalizerService()
    builder = UISkillDraftBuilder()
    compiler = UISkillCompilerService()
    runtime = UIReplayRuntime()

    session = sess_svc.create_session(name="Report Test", description=None, target_base_url=_FAKE_ERP_URL)
    sid = session.session_id
    ev_svc.capture_event(sid, "navigate", url=_FAKE_ERP_URL + "/sales/orders")
    ev_svc.capture_event(sid, "fill", selector="[data-testid='order-search']", input_value="SO-VALID")
    ev_svc.capture_event(sid, "click", selector="[data-testid='open-order-SO-VALID']")

    raw = ev_svc.list_events(sid)
    recording = norm.normalize(sid, raw)
    draft = builder.build_draft(recording, name="Report Test Skill")
    skill = compiler.compile(draft.draft_id)
    return runtime.replay(skill.compiled_skill_id, _FAKE_ERP_URL)


def test_get_report_returns_result():
    replay = _make_replay()
    svc = UIReplayReportService()
    report = svc.get_report(replay.replay_id)
    assert report is not None
    assert report.replay_id == replay.replay_id


def test_report_is_deterministic_no_llm():
    replay = _make_replay()
    svc = UIReplayReportService()
    report = svc.get_report(replay.replay_id)
    assert report.llm_used_at_replay is False
    assert report.deterministic is True


def test_report_success_rate_is_100_for_clean_replay():
    replay = _make_replay()
    svc = UIReplayReportService()
    report = svc.get_report(replay.replay_id)
    assert report.success_rate_pct == 100.0
    assert report.steps_failed == 0


def test_report_summary_mentions_passed_steps():
    replay = _make_replay()
    svc = UIReplayReportService()
    report = svc.get_report(replay.replay_id)
    assert "passed" in report.summary.lower() or "completed" in report.summary.lower()


def test_report_audit_evidence_count_matches_steps():
    replay = _make_replay()
    svc = UIReplayReportService()
    report = svc.get_report(replay.replay_id)
    assert report.audit_evidence_count == replay.step_count


def test_get_report_nonexistent_replay_returns_none():
    svc = UIReplayReportService()
    assert svc.get_report("nonexistent_replay_id") is None
