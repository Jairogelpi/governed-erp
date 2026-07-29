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
from erpguard.product.active_skill_runner import ActiveSkillRunnerService

_FAKE_ERP_URL = "http://localhost:8000/fake-erp"


def _make_active_version():
    sess = UIRecordingSessionService()
    ev = UIEventCaptureService()
    norm = UIRecordingNormalizerService()
    builder = UISkillDraftBuilder()
    compiler = UISkillCompilerService()
    versioning = UISkillVersioningService()
    lc = UISkillLifecycleService()

    session = sess.create_session(name="Runner Test", description=None, target_base_url=_FAKE_ERP_URL)
    sid = session.session_id
    ev.capture_event(sid, "navigate", url=_FAKE_ERP_URL + "/sales/orders")
    ev.capture_event(sid, "fill", selector="[data-testid='order-search']", input_value="SO-VALID")
    ev.capture_event(sid, "click", selector="[data-testid='formula-tab']")
    raw = ev.list_events(sid)
    recording = norm.normalize(sid, raw)
    draft = builder.build_draft(recording, name="Runner Skill")
    skill = compiler.compile(draft.draft_id)
    skill_id = f"runner_family_{uuid4().hex[:12]}"
    version = versioning.create_from_compiled_skill(skill.compiled_skill_id, skill_id=skill_id)
    lc.promote_to_candidate(version.version_id)
    lc.approve(version.version_id)
    lc.activate(version.version_id)
    return version


def _make_draft_version():
    sess = UIRecordingSessionService()
    ev = UIEventCaptureService()
    norm = UIRecordingNormalizerService()
    builder = UISkillDraftBuilder()
    compiler = UISkillCompilerService()
    versioning = UISkillVersioningService()

    session = sess.create_session(name="Draft Runner Test", description=None, target_base_url=_FAKE_ERP_URL)
    sid = session.session_id
    ev.capture_event(sid, "navigate", url=_FAKE_ERP_URL + "/sales/orders")
    ev.capture_event(sid, "fill", selector="[data-testid='order-search']", input_value="SO-VALID")
    raw = ev.list_events(sid)
    recording = norm.normalize(sid, raw)
    draft = builder.build_draft(recording, name="Draft Runner Skill")
    skill = compiler.compile(draft.draft_id)
    skill_id = f"draft_runner_family_{uuid4().hex[:12]}"
    return versioning.create_from_compiled_skill(skill.compiled_skill_id, skill_id=skill_id)


def test_run_active_version_succeeds():
    version = _make_active_version()
    svc = ActiveSkillRunnerService()
    result = svc.run(version.version_id, _FAKE_ERP_URL)
    assert result.run_id.startswith("as_run_")
    assert result.status in ("completed", "completed_with_failures")
    assert result.replay_run_id is not None


def test_run_draft_version_blocked():
    version = _make_draft_version()
    svc = ActiveSkillRunnerService()
    result = svc.run(version.version_id, _FAKE_ERP_URL)
    assert result.status == "blocked"
    assert result.replay_run_id is None


def test_run_with_invalid_target_rejected():
    version = _make_active_version()
    svc = ActiveSkillRunnerService()
    result = svc.run(version.version_id, "http://production-erp.example.com")
    assert result.status == "rejected"


def test_run_with_invalid_inputs_rejected():
    version = _make_active_version()
    svc = ActiveSkillRunnerService()
    result = svc.run(version.version_id, _FAKE_ERP_URL, inputs={"nested": {"key": "val"}})
    assert result.status == "rejected"


def test_run_nonexistent_version_raises():
    svc = ActiveSkillRunnerService()
    with pytest.raises(ValueError, match="not found"):
        svc.run("nonexistent_version_id", _FAKE_ERP_URL)


def test_run_records_actor():
    version = _make_active_version()
    svc = ActiveSkillRunnerService()
    result = svc.run(version.version_id, _FAKE_ERP_URL, actor="test_operator")
    assert result.actor == "test_operator"


def test_run_sanitizes_inputs():
    version = _make_active_version()
    svc = ActiveSkillRunnerService()
    result = svc.run(version.version_id, _FAKE_ERP_URL, inputs={"order_reference": "SO-VALID"})
    assert "order_reference" in result.inputs
    assert result.inputs["order_reference"] == "SO-VALID"
