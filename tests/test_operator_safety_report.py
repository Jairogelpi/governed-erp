from __future__ import annotations

from erpguard.product.operator_safety_report import OperatorSafetyReportService


def test_generates_report():
    svc = OperatorSafetyReportService()
    report = svc.generate()
    assert report.invariants_enforced > 0
    assert report.invariants_violated == 0
    assert report.verdict == "safe"
    assert len(report.invariants) == report.invariants_enforced
    assert report.generated_at


def test_all_invariants_enforced():
    svc = OperatorSafetyReportService()
    report = svc.generate()
    for inv in report.invariants:
        assert inv["status"] == "enforced", f"Invariant {inv['id']} not enforced"


def test_blocked_operations_present():
    svc = OperatorSafetyReportService()
    report = svc.generate()
    assert report.blocked_operations_count >= 10
    joined = " ".join(report.blocked_operations).lower()
    assert "real odoo" in joined or "odoo" in joined
    assert "llm" in joined or "lm" in joined


def test_sprint_coverage_complete():
    svc = OperatorSafetyReportService()
    report = svc.generate()
    sprints = {s["sprint"] for s in report.sprint_coverage}
    for expected in range(20, 27):
        assert expected in sprints, f"Sprint {expected} missing from coverage"


def test_report_fields():
    svc = OperatorSafetyReportService()
    report = svc.generate()
    assert "ERPGuard" in report.product
    assert "20" in report.sprint_chain
    assert "26" in report.sprint_chain


def test_verdict_detail_populated():
    svc = OperatorSafetyReportService()
    report = svc.generate()
    assert len(report.verdict_detail) > 0


def test_fake_erp_invariant_present():
    svc = OperatorSafetyReportService()
    report = svc.generate()
    ids = {i["id"] for i in report.invariants}
    assert "fake_erp_only" in ids


def test_no_llm_invariant_present():
    svc = OperatorSafetyReportService()
    report = svc.generate()
    ids = {i["id"] for i in report.invariants}
    assert "no_llm_replay" in ids


def test_no_background_scheduler_invariant():
    svc = OperatorSafetyReportService()
    report = svc.generate()
    ids = {i["id"] for i in report.invariants}
    assert "no_background_scheduler" in ids
