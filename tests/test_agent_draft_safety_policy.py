from __future__ import annotations

from erpguard.product.agent_draft_safety_policy import enforce_draft_safety
from erpguard.product.agent_proposal_to_draft import transform_proposal_to_draft

_GOOD_PROPOSAL = {
    "proposal_id": "proposal_ok",
    "can_execute": False,
    "guards": {
        "mandatory_guards": [
            {"guard_id": "no_generic_writes"},
            {"guard_id": "no_r3_r4_writes"},
            {"guard_id": "no_raw_tool_execution"},
            {"guard_id": "requires_human_review"},
        ],
        "all_guard_ids": [
            "no_generic_writes", "no_r3_r4_writes",
            "no_raw_tool_execution", "requires_human_review",
        ],
    },
    "intent": {"action_type": "read", "target_entity": "sales_order"},
    "process_category": "sales_cycle",
    "workflow": {"steps": [{"step_id": "s1", "step_type": "load_context"}]},
    "risk_summary": {},
    "entity_mappings": [],
    "request_text": "Read all sales orders",
    "session_id": "adv_1",
    "revision_number": 1,
    "status": "draft",
}


def _transform(proposal=None):
    return transform_proposal_to_draft(proposal or _GOOD_PROPOSAL)


def test_valid_transform_passes_safety():
    transform = _transform()
    result = enforce_draft_safety(transform, _GOOD_PROPOSAL)
    assert result.passed is True
    assert result.violations == []
    assert result.runtime_mode == "dry_run_only"
    assert result.write_actions is False
    assert result.can_execute is False


def test_invariants_always_populated():
    transform = _transform()
    result = enforce_draft_safety(transform, _GOOD_PROPOSAL)
    assert len(result.enforced_invariants) >= 5


def test_can_execute_true_on_proposal_fails():
    proposal = {**_GOOD_PROPOSAL, "can_execute": True}
    transform = _transform(proposal)
    result = enforce_draft_safety(transform, proposal)
    assert result.passed is False
    codes = [v.code for v in result.violations]
    assert "can_execute_true" in codes


def test_missing_mandatory_guards_fails():
    proposal = {**_GOOD_PROPOSAL, "guards": {"mandatory_guards": [], "all_guard_ids": []}}
    transform = _transform(proposal)
    result = enforce_draft_safety(transform, proposal)
    assert result.passed is False
    assert any(v.code == "missing_mandatory_guards" for v in result.violations)
