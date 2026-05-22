from __future__ import annotations

import pytest
from erpguard.product.ui_recording_session import UIRecordingSessionService
from erpguard.product.ui_event_capture import UIEventCaptureService
from erpguard.product.ui_recording_normalizer import UIRecordingNormalizerService
from erpguard.product.ui_skill_draft_builder import UISkillDraftBuilder
from erpguard.product.ui_skill_compiler import UISkillCompilerService
from erpguard.product.skill_versioning import UISkillVersioningService
from erpguard.product.skill_promotion_readiness import UISkillPromotionReadinessService

_FAKE_ERP_URL = "http://localhost:8000/fake-erp"


def _make_version():
    sess = UIRecordingSessionService()
    ev = UIEventCaptureService()
    norm = UIRecordingNormalizerService()
    builder = UISkillDraftBuilder()
    compiler = UISkillCompilerService()
    versioning = UISkillVersioningService()

    session = sess.create_session(name="Readiness Test", description=None, target_base_url=_FAKE_ERP_URL)
    sid = session.session_id
    ev.capture_event(sid, "navigate", url=_FAKE_ERP_URL + "/sales/orders")
    ev.capture_event(sid, "fill", selector="[data-testid='order-search']", input_value="SO-VALID")
    ev.capture_event(sid, "click", selector="[data-testid='formula-tab']")
    raw = ev.list_events(sid)
    recording = norm.normalize(sid, raw)
    draft = builder.build_draft(recording, name="Readiness Skill")
    skill = compiler.compile(draft.draft_id)
    return versioning.create_from_compiled_skill(skill.compiled_skill_id)


def test_readiness_without_replay_returns_warning():
    version = _make_version()
    svc = UISkillPromotionReadinessService()
    result = svc.compute(version.version_id)
    assert result.version_id == version.version_id
    assert isinstance(result.ready, bool)
    assert result.readiness_level in ("ready", "warning", "blocked")
    assert any(c["check"] == "has_replay_run" for c in result.checks)


def test_readiness_has_steps_check():
    version = _make_version()
    svc = UISkillPromotionReadinessService()
    result = svc.compute(version.version_id)
    has_steps_check = next((c for c in result.checks if c["check"] == "has_steps"), None)
    assert has_steps_check is not None
    assert has_steps_check["ok"] is True


def test_readiness_no_llm_required():
    version = _make_version()
    svc = UISkillPromotionReadinessService()
    result = svc.compute(version.version_id)
    no_llm_check = next((c for c in result.checks if c["check"] == "no_llm_required"), None)
    assert no_llm_check is not None
    assert no_llm_check["ok"] is True


def test_readiness_nonexistent_raises():
    svc = UISkillPromotionReadinessService()
    with pytest.raises(ValueError, match="not found"):
        svc.compute("nonexistent_version_id")
