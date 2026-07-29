from __future__ import annotations

from uuid import uuid4

from erpguard.recording_pipeline.ui_recording_session import UIRecordingSessionService
from erpguard.recording_pipeline.ui_event_capture import UIEventCaptureService
from erpguard.recording_pipeline.ui_recording_normalizer import UIRecordingNormalizerService
from erpguard.recording_pipeline.ui_skill_draft_builder import UISkillDraftBuilder
from erpguard.recording_pipeline.ui_skill_compiler import UISkillCompilerService
from erpguard.product.skill_versioning import UISkillVersioningService
from erpguard.product.skill_lifecycle import UISkillLifecycleService
from erpguard.product.active_skill_runner import ActiveSkillRunnerService
from erpguard.product.active_skill_run_report import ActiveSkillRunReportService

_FAKE_ERP_URL = "http://localhost:8000/fake-erp"


def _run_active_skill():
    sess = UIRecordingSessionService()
    ev = UIEventCaptureService()
    norm = UIRecordingNormalizerService()
    builder = UISkillDraftBuilder()
    compiler = UISkillCompilerService()
    versioning = UISkillVersioningService()
    lc = UISkillLifecycleService()
    runner = ActiveSkillRunnerService()

    session = sess.create_session(name="Report Test", description=None, target_base_url=_FAKE_ERP_URL)
    sid = session.session_id
    ev.capture_event(sid, "navigate", url=_FAKE_ERP_URL + "/sales/orders")
    ev.capture_event(sid, "fill", selector="[data-testid='order-search']", input_value="SO-VALID")
    raw = ev.list_events(sid)
    recording = norm.normalize(sid, raw)
    draft = builder.build_draft(recording, name="Report Skill")
    skill = compiler.compile(draft.draft_id)
    version = versioning.create_from_compiled_skill(skill.compiled_skill_id, skill_id=f"report_family_{uuid4().hex[:12]}")
    lc.promote_to_candidate(version.version_id)
    lc.approve(version.version_id)
    lc.activate(version.version_id)
    return runner.run(version.version_id, _FAKE_ERP_URL)


def test_report_returns_result():
    run = _run_active_skill()
    svc = ActiveSkillRunReportService()
    report = svc.get_report(run.run_id)
    assert report is not None
    assert report.run_id == run.run_id


def test_report_is_deterministic_no_llm():
    run = _run_active_skill()
    svc = ActiveSkillRunReportService()
    report = svc.get_report(run.run_id)
    assert report.deterministic is True
    assert report.llm_used_at_replay is False


def test_report_has_event_log():
    run = _run_active_skill()
    svc = ActiveSkillRunReportService()
    report = svc.get_report(run.run_id)
    assert len(report.event_log) >= 2


def test_report_has_verifications():
    run = _run_active_skill()
    svc = ActiveSkillRunReportService()
    report = svc.get_report(run.run_id)
    assert report.step_count > 0
    assert len(report.verifications) > 0


def test_report_nonexistent_returns_none():
    svc = ActiveSkillRunReportService()
    assert svc.get_report("nonexistent_run_id") is None
