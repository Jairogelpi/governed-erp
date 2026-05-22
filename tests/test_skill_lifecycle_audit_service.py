from __future__ import annotations

from erpguard.product.ui_recording_session import UIRecordingSessionService
from erpguard.product.ui_event_capture import UIEventCaptureService
from erpguard.product.ui_recording_normalizer import UIRecordingNormalizerService
from erpguard.product.ui_skill_draft_builder import UISkillDraftBuilder
from erpguard.product.ui_skill_compiler import UISkillCompilerService
from erpguard.product.skill_versioning import UISkillVersioningService
from erpguard.product.skill_lifecycle import UISkillLifecycleService
from erpguard.product.skill_lifecycle_audit import UISkillLifecycleAuditService

_FAKE_ERP_URL = "http://localhost:8000/fake-erp"


def _make_version():
    sess = UIRecordingSessionService()
    ev = UIEventCaptureService()
    norm = UIRecordingNormalizerService()
    builder = UISkillDraftBuilder()
    compiler = UISkillCompilerService()
    versioning = UISkillVersioningService()

    session = sess.create_session(name="Audit Test", description=None, target_base_url=_FAKE_ERP_URL)
    sid = session.session_id
    ev.capture_event(sid, "navigate", url=_FAKE_ERP_URL + "/sales/orders")
    ev.capture_event(sid, "fill", selector="[data-testid='order-search']", input_value="SO-VALID")
    raw = ev.list_events(sid)
    recording = norm.normalize(sid, raw)
    draft = builder.build_draft(recording, name="Audit Test Skill")
    skill = compiler.compile(draft.draft_id)
    return versioning.create_from_compiled_skill(skill.compiled_skill_id)


def test_audit_has_creation_event():
    version = _make_version()
    svc = UISkillLifecycleAuditService()
    result = svc.get_events(version.version_id)
    assert result is not None
    assert len(result.events) >= 1
    assert result.events[0].event_type == "created"


def test_audit_records_lifecycle_events():
    version = _make_version()
    lc = UISkillLifecycleService()
    lc.promote_to_candidate(version.version_id, actor="user1", reason="ready")
    lc.approve(version.version_id, actor="approver1", reason="approved")

    svc = UISkillLifecycleAuditService()
    result = svc.get_events(version.version_id)
    event_types = [e.event_type for e in result.events]
    assert "promote_candidate" in event_types
    assert "approve" in event_types


def test_audit_nonexistent_returns_none():
    svc = UISkillLifecycleAuditService()
    assert svc.get_events("nonexistent_version_id") is None


def test_audit_events_have_actor_and_reason():
    version = _make_version()
    lc = UISkillLifecycleService()
    lc.promote_to_candidate(version.version_id, actor="test_actor", reason="test_reason")
    svc = UISkillLifecycleAuditService()
    result = svc.get_events(version.version_id)
    promote_event = next(e for e in result.events if e.event_type == "promote_candidate")
    assert promote_event.actor == "test_actor"
    assert promote_event.reason == "test_reason"
