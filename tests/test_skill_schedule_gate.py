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
from erpguard.product.skill_schedule_gate import SkillScheduleGateService

_FAKE_ERP_URL = "http://localhost:8000/fake-erp"


def _make_version(activate: bool = True):
    sess = UIRecordingSessionService()
    ev = UIEventCaptureService()
    norm = UIRecordingNormalizerService()
    builder = UISkillDraftBuilder()
    compiler = UISkillCompilerService()
    versioning = UISkillVersioningService()
    lc = UISkillLifecycleService()

    session = sess.create_session(name="Sch Gate Test", description=None, target_base_url=_FAKE_ERP_URL)
    sid = session.session_id
    ev.capture_event(sid, "navigate", url=_FAKE_ERP_URL + "/sales/orders")
    ev.capture_event(sid, "fill", selector="[data-testid='order-search']", input_value="SO-VALID")
    raw = ev.list_events(sid)
    recording = norm.normalize(sid, raw)
    draft = builder.build_draft(recording, name="Sch Gate Skill")
    skill = compiler.compile(draft.draft_id)
    family = f"sch_gate_{uuid4().hex[:12]}"
    version = versioning.create_from_compiled_skill(skill.compiled_skill_id, skill_id=family)
    if activate:
        lc.promote_to_candidate(version.version_id)
        lc.approve(version.version_id)
        lc.activate(version.version_id)
    return version


def test_gate_open_for_active_version():
    version = _make_version(activate=True)
    gate = SkillScheduleGateService()
    result = gate.check(version.version_id, _FAKE_ERP_URL, 60, 60, 30)
    assert result.can_schedule is True


def test_gate_blocks_draft_version():
    version = _make_version(activate=False)
    gate = SkillScheduleGateService()
    result = gate.check(version.version_id, _FAKE_ERP_URL, 60, 60, 30)
    assert result.can_schedule is False


def test_gate_blocks_non_fake_erp_target():
    version = _make_version(activate=True)
    gate = SkillScheduleGateService()
    result = gate.check(version.version_id, "http://prod.example.com", 60, 60, 30)
    assert result.can_schedule is False


def test_gate_blocks_interval_below_floor():
    version = _make_version(activate=True)
    gate = SkillScheduleGateService()
    result = gate.check(version.version_id, _FAKE_ERP_URL, 30, 60, 30)
    assert result.can_schedule is False
    assert any("below minimum floor" in r for r in result.blocking_reasons)


def test_gate_blocks_min_interval_below_floor():
    version = _make_version(activate=True)
    gate = SkillScheduleGateService()
    result = gate.check(version.version_id, _FAKE_ERP_URL, 120, 30, 30)
    assert result.can_schedule is False


def test_gate_blocks_interval_less_than_min_interval():
    version = _make_version(activate=True)
    gate = SkillScheduleGateService()
    result = gate.check(version.version_id, _FAKE_ERP_URL, 60, 120, 30)
    assert result.can_schedule is False


def test_gate_blocks_dedup_below_floor():
    version = _make_version(activate=True)
    gate = SkillScheduleGateService()
    result = gate.check(version.version_id, _FAKE_ERP_URL, 60, 60, 2)
    assert result.can_schedule is False


def test_gate_nonexistent_version_raises():
    gate = SkillScheduleGateService()
    with pytest.raises(ValueError, match="not found"):
        gate.check("nonexistent_version", _FAKE_ERP_URL, 60, 60, 30)
