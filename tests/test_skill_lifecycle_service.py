from __future__ import annotations

from uuid import uuid4
import pytest
from erpguard.recording_pipeline.ui_recording_session import UIRecordingSessionService
from erpguard.recording_pipeline.ui_event_capture import UIEventCaptureService
from erpguard.recording_pipeline.ui_recording_normalizer import UIRecordingNormalizerService
from erpguard.recording_pipeline.ui_skill_draft_builder import UISkillDraftBuilder
from erpguard.recording_pipeline.ui_skill_compiler import UISkillCompilerService
from erpguard.product.skill_versioning import UISkillVersioningService
from erpguard.product.skill_lifecycle import UISkillLifecycleService

_FAKE_ERP_URL = "http://localhost:8000/fake-erp"


def _make_version(skill_id: str | None = None):
    sess = UIRecordingSessionService()
    ev = UIEventCaptureService()
    norm = UIRecordingNormalizerService()
    builder = UISkillDraftBuilder()
    compiler = UISkillCompilerService()
    versioning = UISkillVersioningService()

    session = sess.create_session(name="LC Test", description=None, target_base_url=_FAKE_ERP_URL)
    sid = session.session_id
    ev.capture_event(sid, "navigate", url=_FAKE_ERP_URL + "/sales/orders")
    ev.capture_event(sid, "fill", selector="[data-testid='order-search']", input_value="SO-VALID")
    raw = ev.list_events(sid)
    recording = norm.normalize(sid, raw)
    draft = builder.build_draft(recording, name="LC Test Skill")
    skill = compiler.compile(draft.draft_id)
    final_skill_id = skill_id or f"lc_solo_{uuid4().hex[:12]}"
    return versioning.create_from_compiled_skill(skill.compiled_skill_id, skill_id=final_skill_id)


def test_promote_to_candidate():
    version = _make_version()
    svc = UISkillLifecycleService()
    result = svc.promote_to_candidate(version.version_id, actor="user1")
    assert result.from_status == "draft"
    assert result.to_status == "candidate"
    assert result.event_type == "promote_candidate"


def test_approve_from_candidate():
    version = _make_version()
    svc = UISkillLifecycleService()
    svc.promote_to_candidate(version.version_id)
    result = svc.approve(version.version_id, actor="approver1")
    assert result.to_status == "approved"


def test_activate_from_approved():
    version = _make_version()
    svc = UISkillLifecycleService()
    svc.promote_to_candidate(version.version_id)
    svc.approve(version.version_id)
    result = svc.activate(version.version_id, actor="ops")
    assert result.to_status == "active"


def test_invalid_transition_raises():
    version = _make_version()
    svc = UISkillLifecycleService()
    with pytest.raises(ValueError, match="Cannot transition"):
        svc.approve(version.version_id)


def test_deprecate_approved_version():
    version = _make_version()
    svc = UISkillLifecycleService()
    svc.promote_to_candidate(version.version_id)
    svc.approve(version.version_id)
    result = svc.deprecate(version.version_id)
    assert result.to_status == "deprecated"


def test_cannot_transition_from_deprecated():
    version = _make_version()
    svc = UISkillLifecycleService()
    svc.promote_to_candidate(version.version_id)
    svc.approve(version.version_id)
    svc.deprecate(version.version_id)
    with pytest.raises(ValueError, match="Cannot transition"):
        svc.approve(version.version_id)


def test_two_active_versions_blocked():
    family_id = f"two_active_family_{uuid4().hex[:12]}"
    v1 = _make_version(skill_id=family_id)
    v2 = _make_version(skill_id=family_id)
    svc = UISkillLifecycleService()
    for vid in (v1.version_id, v2.version_id):
        svc.promote_to_candidate(vid)
        svc.approve(vid)
    svc.activate(v1.version_id)
    with pytest.raises(ValueError, match="already has an active version"):
        svc.activate(v2.version_id)
