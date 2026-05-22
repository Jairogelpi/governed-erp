from __future__ import annotations

from erpguard.product.ui_recording_session import UIRecordingSessionService
from erpguard.product.ui_event_capture import UIEventCaptureService
from erpguard.product.ui_recording_normalizer import UIRecordingNormalizerService
from erpguard.product.ui_skill_draft_builder import UISkillDraftBuilder
from erpguard.product.ui_skill_compiler import UISkillCompilerService
from erpguard.product.skill_versioning import UISkillVersioningService
from erpguard.product.skill_lifecycle import UISkillLifecycleService
from erpguard.product.skill_activation_gate import UISkillActivationGateService

_FAKE_ERP_URL = "http://localhost:8000/fake-erp"


def _make_version():
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
    return versioning.create_from_compiled_skill(skill.compiled_skill_id)


def test_gate_blocks_draft_version():
    version = _make_version()
    gate = UISkillActivationGateService()
    result = gate.check(version.version_id)
    assert result.can_activate is False
    assert result.gate_status == "blocked"
    assert any("approved" in r for r in result.blocking_reasons)


def test_gate_open_for_approved_version():
    version = _make_version()
    lc = UISkillLifecycleService()
    lc.promote_to_candidate(version.version_id)
    lc.approve(version.version_id)
    gate = UISkillActivationGateService()
    result = gate.check(version.version_id)
    assert result.can_activate is True
    assert result.gate_status == "open"


def test_gate_status_is_approved_check():
    version = _make_version()
    gate = UISkillActivationGateService()
    result = gate.check(version.version_id)
    status_check = next((c for c in result.checks if c["check"] == "status_is_approved"), None)
    assert status_check is not None
    assert status_check["ok"] is False


def test_gate_deterministic_runtime_check():
    version = _make_version()
    gate = UISkillActivationGateService()
    result = gate.check(version.version_id)
    runtime_check = next((c for c in result.checks if c["check"] == "deterministic_runtime"), None)
    assert runtime_check is not None
    assert runtime_check["ok"] is True
