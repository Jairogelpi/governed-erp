from __future__ import annotations

import json

from erpguard.product.agent_proposal_to_draft import transform_proposal_to_draft

_PROPOSAL = {
    "proposal_id": "proposal_abc",
    "session_id": "advisory_123",
    "request_text": "List all draft sales orders every morning",
    "intent": {"action_type": "read", "target_entity": "sales_order"},
    "process_category": "sales_cycle",
    "process_description": "End-to-end sales process",
    "workflow": {
        "steps": [
            {"step_id": "s1", "step_type": "load_context"},
            {"step_id": "s2", "step_type": "read_record"},
        ]
    },
    "guards": {"mandatory_guards": [], "all_guard_ids": []},
    "risk_summary": {"overall_risk_level": "low"},
    "entity_mappings": [],
}


def test_transform_sets_dry_run_only():
    result = transform_proposal_to_draft(_PROPOSAL)
    assert result.runtime_mode == "dry_run_only"
    assert result.write_actions is False
    assert result.status == "pending_review"


def test_transform_name_includes_action_and_entity():
    result = transform_proposal_to_draft(_PROPOSAL)
    assert "Read" in result.name
    assert "Sales Order" in result.name


def test_transform_uses_advisory_sentinels():
    result = transform_proposal_to_draft(_PROPOSAL)
    assert result.scan_id == "agent_advisory"
    assert result.snapshot_id == "agent_advisory"
    assert result.connection_id == "agent_advisory"
    assert "agent_proposal:" in result.opportunity_id


def test_transform_draft_json_has_safety_flags():
    result = transform_proposal_to_draft(_PROPOSAL)
    content = json.loads(result.draft_json)
    safety = content["safety"]
    assert safety["runtime_mode"] == "dry_run_only"
    assert safety["write_actions"] is False
    assert safety["can_execute"] is False
    assert safety["is_advisory_only"] is True
    assert safety["requires_human_review"] is True


def test_transform_draft_json_embeds_proposal_id():
    result = transform_proposal_to_draft(_PROPOSAL)
    content = json.loads(result.draft_json)
    assert content["proposal_id"] == "proposal_abc"
    assert content["source"] == "agent_advisory_proposal"


def test_transform_description_contains_review_note():
    result = transform_proposal_to_draft(_PROPOSAL)
    assert "review" in result.description.lower()


def test_transform_unknown_intent_uses_process_name():
    proposal = {**_PROPOSAL, "intent": {"action_type": "unknown", "target_entity": "unknown"}}
    result = transform_proposal_to_draft(proposal)
    assert "Agent" in result.name
