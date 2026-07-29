from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from erpguard.recording_pipeline.ui_recording_session import UIRecordingSessionService
from erpguard.recording_pipeline.ui_event_capture import UIEventCaptureService
from erpguard.recording_pipeline.ui_recording_normalizer import UIRecordingNormalizerService
from erpguard.recording_pipeline.ui_skill_draft_builder import UISkillDraftBuilder
from erpguard.recording_pipeline.ui_skill_compiler import UISkillCompilerService
from erpguard.product.skill_versioning import UISkillVersioningService
from erpguard.product.skill_lifecycle import UISkillLifecycleService
from erpguard.product.skill_schedule import SkillScheduleService
from erpguard.product.skill_schedule_tick import SkillScheduleTickService
from erpguard.product.skill_run_queue import SkillRunQueueService

_FAKE_ERP_URL = "http://localhost:8000/fake-erp"


def _make_active_schedule(active: bool = True):
    sess = UIRecordingSessionService()
    ev = UIEventCaptureService()
    norm = UIRecordingNormalizerService()
    builder = UISkillDraftBuilder()
    compiler = UISkillCompilerService()
    versioning = UISkillVersioningService()
    lc = UISkillLifecycleService()
    schedules = SkillScheduleService()

    session = sess.create_session(name="Tick Test", description=None, target_base_url=_FAKE_ERP_URL)
    sid = session.session_id
    ev.capture_event(sid, "navigate", url=_FAKE_ERP_URL + "/sales/orders")
    ev.capture_event(sid, "fill", selector="[data-testid='order-search']", input_value="SO-VALID")
    raw = ev.list_events(sid)
    recording = norm.normalize(sid, raw)
    draft = builder.build_draft(recording, name="Tick Skill")
    skill = compiler.compile(draft.draft_id)
    family = f"tick_family_{uuid4().hex[:12]}"
    version = versioning.create_from_compiled_skill(skill.compiled_skill_id, skill_id=family)
    lc.promote_to_candidate(version.version_id)
    lc.approve(version.version_id)
    lc.activate(version.version_id)
    sched = schedules.create_schedule(
        version_id=version.version_id,
        name="Tick test schedule",
        interval_seconds=60,
        target_base_url=_FAKE_ERP_URL,
    )
    if active:
        schedules.activate(sched.schedule_id)
    return sched


def test_tick_with_no_due_schedules_returns_empty_report():
    tick = SkillScheduleTickService()
    past = datetime(2000, 1, 1, tzinfo=timezone.utc)
    report = tick.tick(now=past)
    assert report.due_count == 0
    assert report.dispatched == []


def test_tick_dispatches_due_active_schedule():
    sched = _make_active_schedule(active=True)
    tick = SkillScheduleTickService()
    future = datetime.now(timezone.utc) + timedelta(seconds=10)
    report = tick.tick(now=future)
    assert report.due_count >= 1
    matching = [d for d in report.dispatched if d.schedule_id == sched.schedule_id]
    assert len(matching) == 1
    assert matching[0].run_id is not None


def test_tick_does_not_dispatch_paused_schedule():
    sched = _make_active_schedule(active=True)
    schedules = SkillScheduleService()
    schedules.pause(sched.schedule_id)
    tick = SkillScheduleTickService()
    future = datetime.now(timezone.utc) + timedelta(seconds=10)
    report = tick.tick(now=future)
    matching = [d for d in report.dispatched if d.schedule_id == sched.schedule_id]
    assert len(matching) == 0


def test_tick_dedups_within_window():
    sched = _make_active_schedule(active=True)
    tick = SkillScheduleTickService()
    base = datetime.now(timezone.utc) + timedelta(seconds=10)
    first = tick.tick(now=base)
    assert any(d.schedule_id == sched.schedule_id for d in first.dispatched)

    second_base = base + timedelta(seconds=5)
    second = tick.tick(now=second_base)
    matching_skipped = [s for s in second.skipped if s.schedule_id == sched.schedule_id]
    matching_dispatched = [d for d in second.dispatched if d.schedule_id == sched.schedule_id]
    assert len(matching_dispatched) == 0
    if matching_skipped:
        assert matching_skipped[0].reason in ("dedup", "min_interval", "locked")


def test_tick_updates_next_run_at_after_dispatch():
    sched = _make_active_schedule(active=True)
    tick = SkillScheduleTickService()
    future = datetime.now(timezone.utc) + timedelta(seconds=10)
    tick.tick(now=future)

    schedules = SkillScheduleService()
    refreshed = schedules.get_schedule(sched.schedule_id)
    assert refreshed.last_run_at != ""
    assert refreshed.last_run_id is not None


def test_tick_creates_queue_entries():
    sched = _make_active_schedule(active=True)
    tick = SkillScheduleTickService()
    future = datetime.now(timezone.utc) + timedelta(seconds=10)
    tick.tick(now=future)

    q = SkillRunQueueService()
    entries = q.list_for_schedule(sched.schedule_id)
    assert len(entries) >= 1
