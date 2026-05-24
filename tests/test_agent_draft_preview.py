from __future__ import annotations

from erpguard.product.agent_draft_preview import preview_draft

_ELIGIBLE_PROPOSAL = {
    "proposal_id": "proposal_preview_test",
    "status": "draft",
    "can_execute": False,
    "intent": {"action_type": "read", "target_entity": "sales_order"},
    "process_category": "sales_cycle",
    "process_description": "",
    "workflow": {
        "steps": [
            {"step_id": "s1", "step_type": "load_context", "label": "Load Context"},
            {"step_id": "s2", "step_type": "read_record", "label": "Read Record"},
        ]
    },
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
    "risk_summary": {"overall_risk_level": "low"},
    "entity_mappings": [],
    "request_text": "List all draft sales orders",
    "session_id": "adv_1",
    "revision_number": 1,
    "clarification_questions": [],
}


def test_eligible_proposal_preview_is_ready():
    result = preview_draft(_ELIGIBLE_PROPOSAL)
    assert result.eligible is True
    assert result.ready_to_create is True
    assert result.blocking_issues == []
    assert result.draft_runtime_mode == "dry_run_only"
    assert result.draft_write_actions is False
    assert result.draft_status == "pending_review"


def test_preview_populates_workflow_steps():
    result = preview_draft(_ELIGIBLE_PROPOSAL)
    assert len(result.workflow_steps) == 2


def test_preview_populates_guard_ids():
    result = preview_draft(_ELIGIBLE_PROPOSAL)
    assert "no_generic_writes" in result.guard_ids


def test_preview_risk_level():
    result = preview_draft(_ELIGIBLE_PROPOSAL)
    assert result.risk_level == "low"


def test_preview_includes_draft_name():
    result = preview_draft(_ELIGIBLE_PROPOSAL)
    assert "[Agent]" in result.draft_name


def test_ineligible_proposal_not_ready():
    proposal = {**_ELIGIBLE_PROPOSAL, "workflow": {"steps": []}}
    result = preview_draft(proposal)
    assert result.ready_to_create is False
    assert len(result.blocking_issues) > 0


def test_advisory_note_present():
    result = preview_draft(_ELIGIBLE_PROPOSAL)
    assert "non-persisted" in result.advisory_note
