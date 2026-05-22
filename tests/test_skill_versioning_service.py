from __future__ import annotations

from uuid import uuid4
import pytest
from erpguard.product.ui_recording_session import UIRecordingSessionService
from erpguard.product.ui_event_capture import UIEventCaptureService
from erpguard.product.ui_recording_normalizer import UIRecordingNormalizerService
from erpguard.product.ui_skill_draft_builder import UISkillDraftBuilder
from erpguard.product.ui_skill_compiler import UISkillCompilerService
from erpguard.product.skill_versioning import UISkillVersioningService

_FAKE_ERP_URL = "http://localhost:8000/fake-erp"


def _make_compiled_skill():
    sess = UIRecordingSessionService()
    ev = UIEventCaptureService()
    norm = UIRecordingNormalizerService()
    builder = UISkillDraftBuilder()
    compiler = UISkillCompilerService()

    session = sess.create_session(name="Versioning Test", description=None, target_base_url=_FAKE_ERP_URL)
    sid = session.session_id
    ev.capture_event(sid, "navigate", url=_FAKE_ERP_URL + "/sales/orders")
    ev.capture_event(sid, "fill", selector="[data-testid='order-search']", input_value="SO-VALID")
    ev.capture_event(sid, "click", selector="[data-testid='formula-tab']")
    raw = ev.list_events(sid)
    recording = norm.normalize(sid, raw)
    draft = builder.build_draft(recording, name="Versioning Test Skill")
    return compiler.compile(draft.draft_id)


def test_create_version_from_compiled_skill():
    skill = _make_compiled_skill()
    svc = UISkillVersioningService()
    unique_skill_id = f"vfam_{uuid4().hex[:12]}"
    version = svc.create_from_compiled_skill(skill.compiled_skill_id, skill_id=unique_skill_id)
    assert version.version_id.startswith("ui_skv_")
    assert version.status == "draft"
    assert version.version_number == 1
    assert version.llm_required is False
    assert version.runtime_type == "deterministic_ui"


def test_create_version_with_explicit_skill_id():
    skill = _make_compiled_skill()
    svc = UISkillVersioningService()
    skill_id = f"my_skill_family_{uuid4().hex[:12]}"
    version = svc.create_from_compiled_skill(skill.compiled_skill_id, skill_id=skill_id)
    assert version.skill_id == skill_id


def test_create_second_version_increments_number():
    skill_a = _make_compiled_skill()
    skill_b = _make_compiled_skill()
    svc = UISkillVersioningService()
    family_id = f"multi_family_{uuid4().hex[:12]}"
    v1 = svc.create_from_compiled_skill(skill_a.compiled_skill_id, skill_id=family_id)
    v2 = svc.create_from_compiled_skill(skill_b.compiled_skill_id, skill_id=family_id)
    assert v1.version_number == 1
    assert v2.version_number == 2


def test_get_version_returns_detail():
    skill = _make_compiled_skill()
    svc = UISkillVersioningService()
    version = svc.create_from_compiled_skill(skill.compiled_skill_id)
    fetched = svc.get_version(version.version_id)
    assert fetched is not None
    assert fetched.version_id == version.version_id


def test_get_nonexistent_version_returns_none():
    svc = UISkillVersioningService()
    assert svc.get_version("nonexistent_version_id") is None


def test_list_versions_for_skill_id():
    skill_a = _make_compiled_skill()
    skill_b = _make_compiled_skill()
    svc = UISkillVersioningService()
    family_id = f"list_family_{uuid4().hex[:12]}"
    svc.create_from_compiled_skill(skill_a.compiled_skill_id, skill_id=family_id)
    svc.create_from_compiled_skill(skill_b.compiled_skill_id, skill_id=family_id)
    versions = svc.list_versions(family_id)
    assert len(versions) == 2


def test_create_version_nonexistent_compiled_skill_raises():
    svc = UISkillVersioningService()
    with pytest.raises(ValueError, match="not found"):
        svc.create_from_compiled_skill("nonexistent_compiled_skill_id")


def test_version_steps_match_compiled_skill():
    skill = _make_compiled_skill()
    svc = UISkillVersioningService()
    version = svc.create_from_compiled_skill(skill.compiled_skill_id)
    assert len(version.steps) == len(skill.steps)
