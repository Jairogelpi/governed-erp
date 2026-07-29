from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from erpguard.product.skill_run_lock import SkillRunLockService
from erpguard.recording_pipeline.ui_recording_session import UIRecordingSessionService
from erpguard.recording_pipeline.ui_event_capture import UIEventCaptureService
from erpguard.recording_pipeline.ui_recording_normalizer import UIRecordingNormalizerService
from erpguard.recording_pipeline.ui_skill_draft_builder import UISkillDraftBuilder
from erpguard.recording_pipeline.ui_skill_compiler import UISkillCompilerService
from erpguard.product.skill_versioning import UISkillVersioningService
from erpguard.product.skill_lifecycle import UISkillLifecycleService
from erpguard.product.skill_schedule import SkillScheduleService

_FAKE_ERP_URL = "http://localhost:8000/fake-erp"


def _make_schedule() -> str:
    sess = UIRecordingSessionService()
    ev = UIEventCaptureService()
    norm = UIRecordingNormalizerService()
    builder = UISkillDraftBuilder()
    compiler = UISkillCompilerService()
    versioning = UISkillVersioningService()
    lc = UISkillLifecycleService()
    schedules = SkillScheduleService()

    session = sess.create_session(name="Lock Test", description=None, target_base_url=_FAKE_ERP_URL)
    sid = session.session_id
    ev.capture_event(sid, "navigate", url=_FAKE_ERP_URL + "/sales/orders")
    ev.capture_event(sid, "fill", selector="[data-testid='order-search']", input_value="SO-VALID")
    raw = ev.list_events(sid)
    recording = norm.normalize(sid, raw)
    draft = builder.build_draft(recording, name="Lock Skill")
    skill = compiler.compile(draft.draft_id)
    family = f"lock_family_{uuid4().hex[:12]}"
    version = versioning.create_from_compiled_skill(skill.compiled_skill_id, skill_id=family)
    lc.promote_to_candidate(version.version_id)
    lc.approve(version.version_id)
    lc.activate(version.version_id)
    sched = schedules.create_schedule(
        version_id=version.version_id,
        name="Lock test schedule",
        interval_seconds=60,
        target_base_url=_FAKE_ERP_URL,
    )
    return sched.schedule_id


def test_acquire_lock_succeeds_first_time():
    sid = _make_schedule()
    lock = SkillRunLockService()
    result = lock.acquire(sid)
    assert result.acquired is True
    assert result.token is not None


def test_acquire_lock_blocked_when_already_held():
    sid = _make_schedule()
    lock = SkillRunLockService()
    first = lock.acquire(sid)
    assert first.acquired is True
    second = lock.acquire(sid)
    assert second.acquired is False
    assert second.reason == "already_locked"


def test_release_lock_with_correct_token():
    sid = _make_schedule()
    lock = SkillRunLockService()
    result = lock.acquire(sid)
    released = lock.release(sid, result.token)
    assert released is True


def test_release_lock_with_wrong_token_returns_false():
    sid = _make_schedule()
    lock = SkillRunLockService()
    lock.acquire(sid)
    released = lock.release(sid, "wrong_token")
    assert released is False


def test_acquire_after_release_succeeds():
    sid = _make_schedule()
    lock = SkillRunLockService()
    first = lock.acquire(sid)
    lock.release(sid, first.token)
    second = lock.acquire(sid)
    assert second.acquired is True


def test_acquire_after_ttl_expired():
    sid = _make_schedule()
    lock = SkillRunLockService()
    far_future = datetime.now(timezone.utc) + timedelta(seconds=3600)
    first = lock.acquire(sid)
    assert first.acquired is True
    expired_attempt = lock.acquire(sid, now=far_future)
    assert expired_attempt.acquired is True


def test_acquire_nonexistent_schedule_returns_not_found():
    lock = SkillRunLockService()
    result = lock.acquire("nonexistent_schedule_id")
    assert result.acquired is False
    assert result.reason == "schedule_not_found"
