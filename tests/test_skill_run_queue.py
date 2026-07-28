from __future__ import annotations

from uuid import uuid4

from erpguard.product.skill_run_queue import SkillRunQueueService


def test_enqueue_returns_entry():
    q = SkillRunQueueService()
    schedule_id = f"sch_q_{uuid4().hex[:8]}"
    entry = q.enqueue(
        schedule_id=schedule_id,
        version_id="ver_x", skill_id="skill_x",
        inputs={"k": "v"}, target_base_url="http://localhost:8000/fake-erp",
    )
    assert entry.entry_id.startswith("q_")
    assert entry.status == "queued"


def test_get_entry():
    q = SkillRunQueueService()
    schedule_id = f"sch_q_{uuid4().hex[:8]}"
    e = q.enqueue(schedule_id=schedule_id, version_id="v", skill_id="s",
                  inputs={}, target_base_url="http://localhost:8000/fake-erp")
    got = q.get_entry(e.entry_id)
    assert got is not None
    assert got.entry_id == e.entry_id


def test_mark_dispatching():
    q = SkillRunQueueService()
    schedule_id = f"sch_q_{uuid4().hex[:8]}"
    e = q.enqueue(schedule_id=schedule_id, version_id="v", skill_id="s",
                  inputs={}, target_base_url="http://localhost:8000/fake-erp")
    updated = q.mark_dispatching(e.entry_id)
    assert updated.status == "dispatching"


def test_mark_dispatched_with_completed_status():
    q = SkillRunQueueService()
    schedule_id = f"sch_q_{uuid4().hex[:8]}"
    e = q.enqueue(schedule_id=schedule_id, version_id="v", skill_id="s",
                  inputs={}, target_base_url="http://localhost:8000/fake-erp")
    updated = q.mark_dispatched(e.entry_id, run_id="as_run_xyz", run_status="completed")
    assert updated.status == "completed"
    assert updated.run_id == "as_run_xyz"


def test_mark_dispatched_with_blocked_status_marks_failed():
    q = SkillRunQueueService()
    schedule_id = f"sch_q_{uuid4().hex[:8]}"
    e = q.enqueue(schedule_id=schedule_id, version_id="v", skill_id="s",
                  inputs={}, target_base_url="http://localhost:8000/fake-erp")
    updated = q.mark_dispatched(e.entry_id, run_id="as_run_xyz", run_status="blocked")
    assert updated.status == "failed"


def test_mark_skipped_dedup():
    q = SkillRunQueueService()
    schedule_id = f"sch_q_{uuid4().hex[:8]}"
    e = q.enqueue(schedule_id=schedule_id, version_id="v", skill_id="s",
                  inputs={}, target_base_url="http://localhost:8000/fake-erp")
    updated = q.mark_skipped(e.entry_id, reason="dedup", detail="duplicate detected")
    assert updated.status == "skipped_dedup"


def test_list_for_schedule_orders_desc():
    q = SkillRunQueueService()
    schedule_id = f"sch_q_list_{uuid4().hex[:8]}"
    q.enqueue(schedule_id=schedule_id, version_id="v", skill_id="s",
                   inputs={"i": 1}, target_base_url="http://localhost:8000/fake-erp")
    e2 = q.enqueue(schedule_id=schedule_id, version_id="v", skill_id="s",
                   inputs={"i": 2}, target_base_url="http://localhost:8000/fake-erp")
    entries = q.list_for_schedule(schedule_id)
    assert len(entries) == 2
    # newest first
    assert entries[0].entry_id == e2.entry_id


def test_get_nonexistent_entry_returns_none():
    q = SkillRunQueueService()
    assert q.get_entry("nonexistent_entry_id") is None
