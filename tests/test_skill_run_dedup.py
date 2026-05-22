from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from erpguard.product.skill_run_dedup import SkillRunDedupService
from erpguard.product.skill_run_queue import SkillRunQueueService


def _enqueue(schedule_id: str, inputs: dict, status: str = "queued"):
    q = SkillRunQueueService()
    return q.enqueue(
        schedule_id=schedule_id,
        version_id="ver_x",
        skill_id="skill_x",
        inputs=inputs,
        target_base_url="http://localhost:8000/fake-erp",
        status=status,
    )


def test_no_recent_entries_no_duplicate():
    svc = SkillRunDedupService()
    schedule_id = f"sch_no_recent_{uuid4().hex[:8]}"
    result = svc.check(schedule_id, {"k": "v"}, 30)
    assert result.is_duplicate is False


def test_recent_identical_entry_is_duplicate():
    schedule_id = f"sch_dup_{uuid4().hex[:8]}"
    _enqueue(schedule_id, {"k": "v"}, status="queued")
    svc = SkillRunDedupService()
    result = svc.check(schedule_id, {"k": "v"}, 30)
    assert result.is_duplicate is True
    assert result.matched_entry_id is not None


def test_recent_different_inputs_not_duplicate():
    schedule_id = f"sch_diff_{uuid4().hex[:8]}"
    _enqueue(schedule_id, {"k": "a"}, status="queued")
    svc = SkillRunDedupService()
    result = svc.check(schedule_id, {"k": "b"}, 30)
    assert result.is_duplicate is False


def test_recent_skipped_entry_not_blocking():
    schedule_id = f"sch_skipped_{uuid4().hex[:8]}"
    _enqueue(schedule_id, {"k": "v"}, status="skipped_dedup")
    svc = SkillRunDedupService()
    result = svc.check(schedule_id, {"k": "v"}, 30)
    assert result.is_duplicate is False


def test_old_entry_outside_window_not_blocking():
    schedule_id = f"sch_old_{uuid4().hex[:8]}"
    svc = SkillRunDedupService()
    far_future = datetime.now(timezone.utc) + timedelta(seconds=3600)
    _enqueue(schedule_id, {"k": "v"}, status="queued")
    result = svc.check(schedule_id, {"k": "v"}, 30, now=far_future)
    assert result.is_duplicate is False
