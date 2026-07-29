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
from erpguard.product.skill_rollback_planner import UISkillRollbackPlanner
from erpguard.product.skill_rollback_service import UISkillRollbackService

_FAKE_ERP_URL = "http://localhost:8000/fake-erp"


def _make_version(skill_id: str | None = None):
    sess = UIRecordingSessionService()
    ev = UIEventCaptureService()
    norm = UIRecordingNormalizerService()
    builder = UISkillDraftBuilder()
    compiler = UISkillCompilerService()
    versioning = UISkillVersioningService()

    session = sess.create_session(name="Rollback Test", description=None, target_base_url=_FAKE_ERP_URL)
    sid = session.session_id
    ev.capture_event(sid, "navigate", url=_FAKE_ERP_URL + "/sales/orders")
    ev.capture_event(sid, "fill", selector="[data-testid='order-search']", input_value="SO-VALID")
    raw = ev.list_events(sid)
    recording = norm.normalize(sid, raw)
    draft = builder.build_draft(recording, name="Rollback Test Skill")
    skill = compiler.compile(draft.draft_id)
    final_skill_id = skill_id or f"rb_solo_{uuid4().hex[:12]}"
    return versioning.create_from_compiled_skill(skill.compiled_skill_id, skill_id=final_skill_id)


def _promote_to_active(version_id: str):
    lc = UISkillLifecycleService()
    lc.promote_to_candidate(version_id)
    lc.approve(version_id)
    lc.activate(version_id)


def test_rollback_plan_is_executable():
    family_id = f"rollback_family_{uuid4().hex[:12]}"
    v1 = _make_version(skill_id=family_id)
    v2 = _make_version(skill_id=family_id)
    _promote_to_active(v1.version_id)
    _promote_to_active_ready_only(v2.version_id)
    planner = UISkillRollbackPlanner()
    plan = planner.plan(v1.version_id, v2.version_id)
    assert plan.is_executable is True
    assert plan.skill_id == family_id


def _promote_to_active_ready_only(version_id: str):
    lc = UISkillLifecycleService()
    lc.promote_to_candidate(version_id)
    lc.approve(version_id)


def test_rollback_plan_same_version_raises():
    v = _make_version()
    planner = UISkillRollbackPlanner()
    with pytest.raises(ValueError, match="same version"):
        planner.plan(v.version_id, v.version_id)


def test_rollback_plan_cross_family_raises():
    v1 = _make_version(skill_id=f"family_a_{uuid4().hex[:12]}")
    v2 = _make_version(skill_id=f"family_b_{uuid4().hex[:12]}")
    planner = UISkillRollbackPlanner()
    with pytest.raises(ValueError, match="different skill families"):
        planner.plan(v1.version_id, v2.version_id)


def test_rollback_execution():
    family_id = f"exec_rollback_family_{uuid4().hex[:12]}"
    v1 = _make_version(skill_id=family_id)
    v2 = _make_version(skill_id=family_id)
    _promote_to_active(v1.version_id)
    lc = UISkillLifecycleService()
    lc.promote_to_candidate(v2.version_id)
    lc.approve(v2.version_id)

    rollback = UISkillRollbackService()
    result = rollback.execute(v1.version_id, v2.version_id, actor="ops", reason="testing rollback")
    assert result.rolled_back_version_id == v1.version_id
    assert result.reactivated_version_id == v2.version_id
    assert result.rolled_back_version_number == 1
    assert result.reactivated_version_number == 2


def test_rollback_blocked_for_draft_version():
    family_id = f"blocked_rollback_family_{uuid4().hex[:12]}"
    v1 = _make_version(skill_id=family_id)
    v2 = _make_version(skill_id=family_id)
    rollback = UISkillRollbackService()
    with pytest.raises(ValueError, match="not executable"):
        rollback.execute(v1.version_id, v2.version_id)
