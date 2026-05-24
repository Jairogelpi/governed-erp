from __future__ import annotations

from erpguard.product.agent_proposal_eligibility import check_eligibility

_VALID_PROPOSAL = {
    "proposal_id": "proposal_test",
    "status": "draft",
    "can_execute": False,
    "intent": {"action_type": "read", "target_entity": "sales_order"},
    "workflow": {
        "steps": [
            {"step_id": "s1", "step_type": "load_context"},
            {"step_id": "s2", "step_type": "read_record"},
        ]
    },
    "guards": {
        "mandatory_guards": [
            {"guard_id": "no_generic_writes"},
            {"guard_id": "no_r3_r4_writes"},
            {"guard_id": "no_raw_tool_execution"},
            {"guard_id": "requires_human_review"},
        ],
        "all_guard_ids": ["no_generic_writes", "no_r3_r4_writes", "no_raw_tool_execution", "requires_human_review"],
    },
}


def test_valid_proposal_is_eligible():
    result = check_eligibility(_VALID_PROPOSAL)
    assert result.eligible is True
    assert result.issues == []
    assert result.runtime_mode == "dry_run_only"
    assert result.write_actions is False
    assert result.requires_human_review is True


def test_ineligible_status_blocks():
    proposal = {**_VALID_PROPOSAL, "status": "draft_created"}
    result = check_eligibility(proposal)
    assert result.eligible is False
    codes = [i.code for i in result.issues]
    assert "ineligible_status" in codes


def test_unknown_intent_adds_issue():
    proposal = {**_VALID_PROPOSAL, "intent": {"action_type": "unknown", "target_entity": "unknown"}}
    result = check_eligibility(proposal)
    assert result.eligible is False
    assert any(i.code == "no_intent" for i in result.issues)


def test_empty_workflow_adds_issue():
    proposal = {**_VALID_PROPOSAL, "workflow": {"steps": []}}
    result = check_eligibility(proposal)
    assert result.eligible is False
    assert any(i.code == "empty_workflow" for i in result.issues)


def test_missing_mandatory_guards_adds_issue():
    proposal = {
        **_VALID_PROPOSAL,
        "guards": {"mandatory_guards": [], "all_guard_ids": []},
    }
    result = check_eligibility(proposal)
    assert result.eligible is False
    assert any(i.code == "missing_mandatory_guards" for i in result.issues)


def test_can_execute_true_blocks():
    proposal = {**_VALID_PROPOSAL, "can_execute": True}
    result = check_eligibility(proposal)
    assert result.eligible is False
    assert any(i.code == "execution_flag_set" for i in result.issues)


def test_revised_status_is_eligible():
    proposal = {**_VALID_PROPOSAL, "status": "revised"}
    result = check_eligibility(proposal)
    assert result.eligible is True
