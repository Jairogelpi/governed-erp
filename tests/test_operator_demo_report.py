from __future__ import annotations

from erpguard.product.operator_demo_report import OperatorDemoReportService


def test_generates_report():
    svc = OperatorDemoReportService()
    report = svc.generate()
    assert report.safety_verdict == "safe"
    assert report.invariants_violated == 0
    assert report.generated_at


def test_report_with_seed_result():
    svc = OperatorDemoReportService()
    seed = {"session_id": "rec_abc", "version_id": "ui_skv_xyz", "run_id": "run_123", "schedule_id": "sch_001"}
    report = svc.generate(seed_result=seed)
    assert report.seed_result["session_id"] == "rec_abc"
    notes_text = " ".join(report.notes)
    assert "rec_abc" in notes_text
    assert "run_123" in notes_text


def test_report_with_pack_id():
    svc = OperatorDemoReportService()
    report = svc.generate(pack_id="evpack_xyz")
    notes_text = " ".join(report.notes)
    assert "evpack_xyz" in notes_text


def test_sprint_coverage_complete():
    svc = OperatorDemoReportService()
    report = svc.generate()
    sprints = {s["sprint"] for s in report.sprint_coverage}
    for s in range(20, 27):
        assert s in sprints


def test_blocked_operations_present():
    svc = OperatorDemoReportService()
    report = svc.generate()
    assert report.blocked_operations_count >= 10
    assert len(report.blocked_operations) >= 10


def test_runbook_operations_present():
    svc = OperatorDemoReportService()
    report = svc.generate()
    assert report.operation_count > 0
    assert len(report.runbook_operations) == report.operation_count


def test_safety_invariants_present():
    svc = OperatorDemoReportService()
    report = svc.generate()
    assert report.invariants_enforced > 0
    assert len(report.safety_invariants) == report.invariants_enforced


def test_product_and_version():
    svc = OperatorDemoReportService()
    report = svc.generate()
    assert "ERPGuard" in report.product
    assert report.version


def test_kill_switches_present():
    svc = OperatorDemoReportService()
    report = svc.generate()
    assert len(report.kill_switches) >= 2


def test_safety_flags_present():
    svc = OperatorDemoReportService()
    report = svc.generate()
    assert len(report.safety_flags) >= 3
    flags = {f["flag"] for f in report.safety_flags}
    assert "ALLOW_GENERIC_REAL_ODOO_WRITES" in flags
