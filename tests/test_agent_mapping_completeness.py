from __future__ import annotations

from erpguard.product.agent_mapping_completeness import check_mapping_completeness


def test_complete_mappings_pass():
    proposal = {
        "proposal_id": "p1",
        "entity_mappings": [
            {"field": "name", "odoo_field": "name", "required": True},
            {"field": "partner_id", "odoo_field": "partner_id", "required": True},
        ],
    }
    result = check_mapping_completeness(proposal)
    assert result.complete is True
    assert result.missing_required_fields == []
    assert result.coverage_pct == 100


def test_empty_mappings_still_complete():
    proposal = {"proposal_id": "p2", "entity_mappings": []}
    result = check_mapping_completeness(proposal)
    assert result.complete is True
    assert any(i.code == "no_mappings" for i in result.issues)


def test_missing_entity_mappings_key():
    proposal = {"proposal_id": "p3"}
    result = check_mapping_completeness(proposal)
    assert result.complete is True


def test_proposal_id_propagated():
    proposal = {"proposal_id": "prop_xyz", "entity_mappings": []}
    result = check_mapping_completeness(proposal)
    assert result.proposal_id == "prop_xyz"
