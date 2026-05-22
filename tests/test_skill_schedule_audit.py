from __future__ import annotations

from uuid import uuid4

from erpguard.product.ui_recording_session import UIRecordingSessionService
from erpguard.product.ui_event_capture import UIEventCaptureService
from erpguard.product.ui_recording_normalizer import UIRecordingNormalizerService
from erpguard.product.ui_skill_draft_builder import UISkillDraftBuilder
from erpguard.product.ui_skill_compiler import UISkillCompilerService
from erpguard.product.skill_versioning import UISkillVersioningService
from erpguard.product.skill_lifecycle import UISkillLifecycleService
from erpguard.product.skill_schedule import SkillScheduleService
from erpguard.product.skill_schedule_audit import SkillScheduleAuditService

_FAKE_ERP_URL = "http://localhost:8000/fake-erp"


def _make_schedule():
    sess = UIRecordingSessionService()
    ev = UIEventCaptureService()
    norm = UIRecordingNormalizerService()
    builder = UISkillDraftBuilder()
    compiler = UISkillCompilerService()
    versioning = UISkillVersioningService()
    lc = UISkillLifecycleService()
    schedules = SkillScheduleService()

    session = sess.create_session(name="Audit Test", description=None, target_base_url=_FAKE_ERP_URL)
    sid = session.session_id
    ev.capture_event(sid, "navigate", url=_FAKE_ERP_URL + "/sales/orders")
    ev.capture_event(sid, "fill", selector="[data-testid='order-search']", input_value="SO-VALID")
    raw = ev.list_events(sid)
    recording = norm.normalize(sid, raw)
    draft = builder.build_draft(recording, name="Audit Skill")
    skill = compiler.compile(draft.draft_id)
    family = f"sch_audit_{uuid4().hex[:12]}"
    version = versioning.create_from_compiled_skill(skill.compiled_skill_id, skill_id=family)
    lc.promote_to_candidate(version.version_id)
    lc.approve(version.version_id)
    lc.activate(version.version_id)
    return schedules.create_schedule(version.version_id, "Audit sched", 60, _FAKE_ERP_URL)


def test_audit_has_creation_event():
    sched = _make_schedule()
    svc = SkillScheduleAuditService()
    events = svc.list_events(sched.schedule_id)
    assert events is not None
    types = [e.event_type for e in events]
    assert "created" in types


def test_audit_records_activation_event():
    sched = _make_schedule()
    schedules = SkillScheduleService()
    schedules.activate(sched.schedule_id, actor="ops", reason="going live")
    svc = SkillScheduleAuditService()
    events = svc.list_events(sched.schedule_id)
    types = [e.event_type for e in events]
    assert "active" in types


def test_audit_records_actor_and_reason():
    sched = _make_schedule()
    schedules = SkillScheduleService()
    schedules.activate(sched.schedule_id, actor="ops_alice", reason="approved by ops review")
    svc = SkillScheduleAuditService()
    events = svc.list_events(sched.schedule_id)
    activate_event = next(e for e in events if e.event_type == "active")
    assert "ops_alice" in activate_event.detail


def test_audit_nonexistent_returns_none():
    svc = SkillScheduleAuditService()
    assert svc.list_events("nonexistent_schedule_id") is None


def test_audit_record_creates_event():
    sched = _make_schedule()
    svc = SkillScheduleAuditService()
    entry = svc.record(sched.schedule_id, "custom_event", status="ok", detail="test")
    assert entry.event_type == "custom_event"
    events = svc.list_events(sched.schedule_id)
    assert any(e.event_id == entry.event_id for e in events)
