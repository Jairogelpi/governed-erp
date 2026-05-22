from __future__ import annotations

from erpguard.product.operator_runbook_summary import OperatorRunbookSummaryService


def test_generates_runbook():
    svc = OperatorRunbookSummaryService()
    runbook = svc.generate()
    assert runbook.operation_count > 0
    assert len(runbook.operations) == runbook.operation_count
    assert runbook.generated_at


def test_all_operations_have_required_fields():
    svc = OperatorRunbookSummaryService()
    runbook = svc.generate()
    for op in runbook.operations:
        assert "id" in op
        assert "title" in op
        assert "endpoint" in op
        assert "preconditions" in op
        assert "safety_notes" in op
        assert "sprint" in op


def test_operations_cover_all_sprints():
    svc = OperatorRunbookSummaryService()
    runbook = svc.generate()
    sprint_nums = {op["sprint"] for op in runbook.operations}
    for s in range(20, 27):
        assert s in sprint_nums, f"Sprint {s} not covered in runbook"


def test_manual_tick_documented():
    svc = OperatorRunbookSummaryService()
    runbook = svc.generate()
    tick_op = next((op for op in runbook.operations if op["id"] == "tick_scheduler"), None)
    assert tick_op is not None
    notes = " ".join(tick_op["safety_notes"]).lower()
    assert "manual" in notes or "autonomous" in notes


def test_kill_switches_present():
    svc = OperatorRunbookSummaryService()
    runbook = svc.generate()
    assert len(runbook.kill_switches) >= 2
    joined = " ".join(runbook.kill_switches).lower()
    assert "kill" in joined


def test_safety_flags_present():
    svc = OperatorRunbookSummaryService()
    runbook = svc.generate()
    assert len(runbook.safety_flags) >= 3
    flags = {f["flag"] for f in runbook.safety_flags}
    assert "ALLOW_GENERIC_REAL_ODOO_WRITES" in flags


def test_evidence_pack_operation_documented():
    svc = OperatorRunbookSummaryService()
    runbook = svc.generate()
    ep_op = next((op for op in runbook.operations if op["id"] == "evidence_pack"), None)
    assert ep_op is not None
    assert "/v1/operator/evidence-packs" in ep_op["endpoint"]


def test_product_name():
    svc = OperatorRunbookSummaryService()
    runbook = svc.generate()
    assert "ERPGuard" in runbook.product


def test_sprint_chain():
    svc = OperatorRunbookSummaryService()
    runbook = svc.generate()
    assert "20" in runbook.sprint_chain
    assert "26" in runbook.sprint_chain
