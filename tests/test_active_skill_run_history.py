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
from erpguard.product.active_skill_run_history import ActiveSkillRunHistoryService

_FAKE_ERP_URL = "http://localhost:8000/fake-erp"


def _run_one_skill():
    sess = UIRecordingSessionService()
    ev = UIEventCaptureService()
    norm = UIRecordingNormalizerService()
    builder = UISkillDraftBuilder()
    compiler = UISkillCompilerService()
    versioning = UISkillVersioningService()
    lc = UISkillLifecycleService()
    runner = ActiveSkillRunnerService()

    session = sess.create_session(name="History Test", description=None, target_base_url=_FAKE_ERP_URL)
    sid = session.session_id
    ev.capture_event(sid, "navigate", url=_FAKE_ERP_URL + "/sales/orders")
    ev.capture_event(sid, "fill", selector="[data-testid='order-search']", input_value="SO-VALID")
    raw = ev.list_events(sid)
    recording = norm.normalize(sid, raw)
    draft = builder.build_draft(recording, name="History Skill")
    skill = compiler.compile(draft.draft_id)
    skill_id = f"history_family_{uuid4().hex[:12]}"
    version = versioning.create_from_compiled_skill(skill.compiled_skill_id, skill_id=skill_id)
    lc.promote_to_candidate(version.version_id)
    lc.approve(version.version_id)
    lc.activate(version.version_id)
    return runner.run(version.version_id, _FAKE_ERP_URL), skill_id


def test_get_run_returns_summary():
    result, _ = _run_one_skill()
    svc = ActiveSkillRunHistoryService()
    summary = svc.get_run(result.run_id)
    assert summary is not None
    assert summary.run_id == result.run_id
    assert summary.trigger == "manual"


def test_get_run_nonexistent_returns_none():
    svc = ActiveSkillRunHistoryService()
    assert svc.get_run("nonexistent_run_id") is None


def test_list_runs_for_skill():
    result, skill_id = _run_one_skill()
    svc = ActiveSkillRunHistoryService()
    runs = svc.list_runs_for_skill(skill_id)
    assert len(runs) >= 1
    assert any(r.run_id == result.run_id for r in runs)


def test_list_run_events():
    result, _ = _run_one_skill()
    svc = ActiveSkillRunHistoryService()
    events = svc.list_run_events(result.run_id)
    assert events is not None
    assert len(events) >= 2
    event_types = [e.event_type for e in events]
    assert "requested" in event_types


def test_list_run_events_nonexistent_returns_none():
    svc = ActiveSkillRunHistoryService()
    assert svc.list_run_events("nonexistent_run_id") is None
