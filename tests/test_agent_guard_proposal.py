from __future__ import annotations

from erpguard.product.agent_guard_proposal import propose_guards


def test_mandatory_guards_always_present():
    result = propose_guards("read")
    mandatory_ids = [g.guard_id for g in result.mandatory_guards]
    assert "no_generic_writes" in mandatory_ids
    assert "no_r3_r4_writes" in mandatory_ids
    assert "no_raw_tool_execution" in mandatory_ids
    assert "requires_human_review" in mandatory_ids


def test_validate_action_recommends_formula_guard():
    result = propose_guards("validate")
    rec_ids = [g.guard_id for g in result.recommended_guards]
    assert "formula_guard" in rec_ids
    assert "odoo_readonly_guard" in rec_ids


def test_confirm_action_recommends_write_pilot():
    result = propose_guards("confirm")
    rec_ids = [g.guard_id for g in result.recommended_guards]
    assert "write_readiness_required" in rec_ids
    assert "approval_required" in rec_ids
    assert "rollback_required" in rec_ids


def test_delete_action_requires_snapshot():
    result = propose_guards("delete")
    rec_ids = [g.guard_id for g in result.recommended_guards]
    assert "snapshot_required" in rec_ids


def test_all_guard_ids_includes_mandatory_and_recommended():
    result = propose_guards("update")
    assert all(g in result.all_guard_ids for g in ["no_generic_writes", "write_readiness_required"])


def test_advisory_note_present():
    result = propose_guards("read")
    assert "advisory" in result.advisory_note.lower()
