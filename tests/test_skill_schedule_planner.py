from __future__ import annotations

from datetime import datetime, timedelta, timezone

from erpguard.product.skill_schedule_planner import SkillSchedulePlannerService


def test_no_previous_run_schedules_now():
    svc = SkillSchedulePlannerService()
    now = datetime(2026, 5, 22, 12, 0, 0, tzinfo=timezone.utc)
    plan = svc.compute_next_run("sch_x", interval_seconds=60, last_run_at=None, now=now)
    assert plan.next_run_at == now
    assert "no_previous_run" in plan.reason


def test_interval_already_elapsed_schedules_now():
    svc = SkillSchedulePlannerService()
    now = datetime(2026, 5, 22, 12, 0, 0, tzinfo=timezone.utc)
    last = now - timedelta(seconds=120)
    plan = svc.compute_next_run("sch_x", interval_seconds=60, last_run_at=last, now=now)
    assert plan.next_run_at == now
    assert "already_elapsed" in plan.reason


def test_interval_in_future():
    svc = SkillSchedulePlannerService()
    now = datetime(2026, 5, 22, 12, 0, 0, tzinfo=timezone.utc)
    last = now - timedelta(seconds=30)
    plan = svc.compute_next_run("sch_x", interval_seconds=60, last_run_at=last, now=now)
    assert plan.next_run_at == last + timedelta(seconds=60)
    assert plan.reason == "interval_in_future"


def test_interval_seconds_recorded():
    svc = SkillSchedulePlannerService()
    now = datetime(2026, 5, 22, 12, 0, 0, tzinfo=timezone.utc)
    plan = svc.compute_next_run("sch_x", interval_seconds=300, last_run_at=None, now=now)
    assert plan.interval_seconds == 300
