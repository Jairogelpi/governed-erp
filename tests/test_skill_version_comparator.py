from __future__ import annotations

from uuid import uuid4
import pytest
from erpguard.recording_pipeline.ui_recording_session import UIRecordingSessionService
from erpguard.recording_pipeline.ui_event_capture import UIEventCaptureService
from erpguard.recording_pipeline.ui_recording_normalizer import UIRecordingNormalizerService
from erpguard.recording_pipeline.ui_skill_draft_builder import UISkillDraftBuilder
from erpguard.recording_pipeline.ui_skill_compiler import UISkillCompilerService
from erpguard.product.skill_versioning import UISkillVersioningService
from erpguard.product.skill_version_comparator import UISkillVersionComparator

_FAKE_ERP_URL = "http://localhost:8000/fake-erp"


def _make_version(events_spec: list[dict], skill_id: str | None = None):
    sess = UIRecordingSessionService()
    ev = UIEventCaptureService()
    norm = UIRecordingNormalizerService()
    builder = UISkillDraftBuilder()
    compiler = UISkillCompilerService()
    versioning = UISkillVersioningService()

    session = sess.create_session(name="Comparator Test", description=None, target_base_url=_FAKE_ERP_URL)
    sid = session.session_id
    for spec in events_spec:
        ev.capture_event(sid, **spec)
    raw = ev.list_events(sid)
    recording = norm.normalize(sid, raw)
    draft = builder.build_draft(recording, name="Comparator Skill")
    skill = compiler.compile(draft.draft_id)
    return versioning.create_from_compiled_skill(skill.compiled_skill_id, skill_id=skill_id)


def test_identical_versions_shows_no_diff():
    events = [
        {"event_type": "navigate", "url": _FAKE_ERP_URL + "/sales/orders"},
        {"event_type": "fill", "selector": "[data-testid='order-search']", "input_value": "SO-VALID"},
    ]
    family_id = f"compare_family_same_{uuid4().hex[:12]}"
    v1 = _make_version(events, skill_id=family_id)
    v2 = _make_version(events, skill_id=family_id)
    comparator = UISkillVersionComparator()
    result = comparator.compare(v1.version_id, v2.version_id)
    assert result.is_identical is True
    assert "identical" in result.summary.lower()


def test_versions_with_different_steps():
    family_id = f"compare_family_diff_{uuid4().hex[:12]}"
    v1 = _make_version([
        {"event_type": "navigate", "url": _FAKE_ERP_URL + "/sales/orders"},
        {"event_type": "fill", "selector": "[data-testid='order-search']", "input_value": "SO-VALID"},
    ], skill_id=family_id)
    v2 = _make_version([
        {"event_type": "navigate", "url": _FAKE_ERP_URL + "/sales/orders"},
        {"event_type": "fill", "selector": "[data-testid='order-search']", "input_value": "SO-VALID"},
        {"event_type": "click", "selector": "[data-testid='formula-tab']"},
    ], skill_id=family_id)
    comparator = UISkillVersionComparator()
    result = comparator.compare(v1.version_id, v2.version_id)
    assert result.is_identical is False


def test_compare_same_version_raises():
    v = _make_version([{"event_type": "navigate", "url": _FAKE_ERP_URL + "/sales/orders"}])
    comparator = UISkillVersionComparator()
    with pytest.raises(ValueError, match="itself"):
        comparator.compare(v.version_id, v.version_id)


def test_compare_nonexistent_version_raises():
    v = _make_version([{"event_type": "navigate", "url": _FAKE_ERP_URL + "/sales/orders"}])
    comparator = UISkillVersionComparator()
    with pytest.raises(ValueError, match="not found"):
        comparator.compare(v.version_id, "nonexistent_version_id")
