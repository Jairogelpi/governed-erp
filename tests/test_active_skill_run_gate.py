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
from erpguard.product.active_skill_run_gate import ActiveSkillRunGateService

_FAKE_ERP_URL = "http://localhost:8000/fake-erp"


def _make_version(skill_id: str | None = None):
    sess = UIRecordingSessionService()
    ev = UIEventCaptureService()
    norm = UIRecordingNormalizerService()
    builder = UISkillDraftBuilder()
    compiler = UISkillCompilerService()
    versioning = UISkillVersioningService()

    session = sess.create_session(name="Gate Test", description=None, target_base_url=_FAKE_ERP_URL)
    sid = session.session_id
    ev.capture_event(sid, "navigate", url=_FAKE_ERP_URL + "/sales/orders")
    ev.capture_event(sid, "fill", selector="[data-testid='order-search']", input_value="SO-VALID")
    raw = ev.list_events(sid)
    recording = norm.normalize(sid, raw)
    draft = builder.build_draft(recording, name="Gate Test Skill")
    skill = compiler.compile(draft.draft_id)
    final_skill_id = skill_id or f"gate_solo_{uuid4().hex[:12]}"
    return versioning.create_from_compiled_skill(skill.compiled_skill_id, skill_id=final_skill_id)


def _activate(version_id: str):
    lc = UISkillLifecycleService()
    lc.promote_to_candidate(version_id)
    lc.approve(version_id)
    lc.activate(version_id)


def test_gate_blocks_draft_version():
    version = _make_version()
    gate = ActiveSkillRunGateService()
    result = gate.check(version.version_id, _FAKE_ERP_URL)
    assert result.can_run is False
    assert result.gate_status == "blocked"
    assert any("active" in r for r in result.blocking_reasons)


def test_gate_blocks_approved_version():
    version = _make_version()
    lc = UISkillLifecycleService()
    lc.promote_to_candidate(version.version_id)
    lc.approve(version.version_id)
    gate = ActiveSkillRunGateService()
    result = gate.check(version.version_id, _FAKE_ERP_URL)
    assert result.can_run is False


def test_gate_open_for_active_version():
    version = _make_version()
    _activate(version.version_id)
    gate = ActiveSkillRunGateService()
    result = gate.check(version.version_id, _FAKE_ERP_URL)
    assert result.can_run is True
    assert result.gate_status == "open"


def test_gate_blocks_non_fake_erp_target():
    version = _make_version()
    _activate(version.version_id)
    gate = ActiveSkillRunGateService()
    result = gate.check(version.version_id, "http://production-erp.example.com")
    assert result.can_run is False
    assert any("Fake ERP" in r for r in result.blocking_reasons)


def test_gate_nonexistent_version_raises():
    gate = ActiveSkillRunGateService()
    with pytest.raises(ValueError, match="not found"):
        gate.check("nonexistent_version_id", _FAKE_ERP_URL)


def test_gate_has_no_llm_required_check():
    version = _make_version()
    _activate(version.version_id)
    gate = ActiveSkillRunGateService()
    result = gate.check(version.version_id, _FAKE_ERP_URL)
    llm_check = next((c for c in result.checks if c["check"] == "no_llm_required"), None)
    assert llm_check is not None
    assert llm_check["ok"] is True
