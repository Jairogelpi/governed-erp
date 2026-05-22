from __future__ import annotations

from uuid import uuid4
import pytest

from erpguard.product.ui_recording_session import UIRecordingSessionService
from erpguard.product.ui_event_capture import UIEventCaptureService
from erpguard.product.ui_recording_normalizer import UIRecordingNormalizerService
from erpguard.product.ui_skill_draft_builder import UISkillDraftBuilder
from erpguard.product.ui_skill_compiler import UISkillCompilerService
from erpguard.product.skill_versioning import UISkillVersioningService
from erpguard.product.skill_lifecycle import UISkillLifecycleService
from erpguard.product.skill_schedule import SkillScheduleService

_FAKE_ERP_URL = "http://localhost:8000/fake-erp"


def _make_active_version():
    sess = UIRecordingSessionService()
    ev = UIEventCaptureService()
    norm = UIRecordingNormalizerService()
    builder = UISkillDraftBuilder()
    compiler = UISkillCompilerService()
    versioning = UISkillVersioningService()
    lc = UISkillLifecycleService()

    session = sess.create_session(name="Sch Test", description=None, target_base_url=_FAKE_ERP_URL)
    sid = session.session_id
    ev.capture_event(sid, "navigate", url=_FAKE_ERP_URL + "/sales/orders")
    ev.capture_event(sid, "fill", selector="[data-testid='order-search']", input_value="SO-VALID")
    raw = ev.list_events(sid)
    recording = norm.normalize(sid, raw)
    draft = builder.build_draft(recording, name="Sch Skill")
    skill = compiler.compile(draft.draft_id)
    family = f"sch_svc_{uuid4().hex[:12]}"
    version = versioning.create_from_compiled_skill(skill.compiled_skill_id, skill_id=family)
    lc.promote_to_candidate(version.version_id)
    lc.approve(version.version_id)
    lc.activate(version.version_id)
    return version


def test_create_schedule():
    version = _make_active_version()
    svc = SkillScheduleService()
    sched = svc.create_schedule(
        version_id=version.version_id,
        name="Test schedule",
        interval_seconds=60,
        target_base_url=_FAKE_ERP_URL,
    )
    assert sched.schedule_id.startswith("sch_")
    assert sched.status == "draft"
    assert sched.interval_seconds == 60


def test_create_schedule_with_bad_interval_raises():
    version = _make_active_version()
    svc = SkillScheduleService()
    with pytest.raises(ValueError, match="gate blocked"):
        svc.create_schedule(
            version_id=version.version_id,
            name="Bad",
            interval_seconds=10,
            target_base_url=_FAKE_ERP_URL,
        )


def test_activate_schedule():
    version = _make_active_version()
    svc = SkillScheduleService()
    sched = svc.create_schedule(version.version_id, "T", 60, _FAKE_ERP_URL)
    activated = svc.activate(sched.schedule_id)
    assert activated.status == "active"
    assert activated.next_run_at != ""


def test_pause_active_schedule():
    version = _make_active_version()
    svc = SkillScheduleService()
    sched = svc.create_schedule(version.version_id, "T", 60, _FAKE_ERP_URL)
    svc.activate(sched.schedule_id)
    paused = svc.pause(sched.schedule_id)
    assert paused.status == "paused"


def test_resume_paused_schedule():
    version = _make_active_version()
    svc = SkillScheduleService()
    sched = svc.create_schedule(version.version_id, "T", 60, _FAKE_ERP_URL)
    svc.activate(sched.schedule_id)
    svc.pause(sched.schedule_id)
    resumed = svc.resume(sched.schedule_id)
    assert resumed.status == "active"


def test_disable_schedule_terminal():
    version = _make_active_version()
    svc = SkillScheduleService()
    sched = svc.create_schedule(version.version_id, "T", 60, _FAKE_ERP_URL)
    svc.activate(sched.schedule_id)
    svc.disable(sched.schedule_id)
    with pytest.raises(ValueError, match="Cannot transition"):
        svc.resume(sched.schedule_id)


def test_invalid_transition_raises():
    version = _make_active_version()
    svc = SkillScheduleService()
    sched = svc.create_schedule(version.version_id, "T", 60, _FAKE_ERP_URL)
    with pytest.raises(ValueError, match="Cannot transition"):
        svc.pause(sched.schedule_id)


def test_get_schedule():
    version = _make_active_version()
    svc = SkillScheduleService()
    sched = svc.create_schedule(version.version_id, "T", 60, _FAKE_ERP_URL)
    got = svc.get_schedule(sched.schedule_id)
    assert got is not None
    assert got.schedule_id == sched.schedule_id


def test_get_nonexistent_returns_none():
    svc = SkillScheduleService()
    assert svc.get_schedule("nonexistent_schedule_id") is None
